# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..utils import fetch_html, fetch_json, clean_text, epoch_ms_to_iso

SOURCE_ID = "latermica"
DEFAULT_BASE = "https://www.latermicamalaga.com/"
TZ = "Europe/Madrid"
PLACE = "La Térmica (Málaga)"

# === util de trazas a data/sources ===
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
SRC_DIR = os.path.join(DATA_DIR, "sources")
os.makedirs(SRC_DIR, exist_ok=True)

def _dump(name: str, content: str | dict):
    path = os.path.join(SRC_DIR, name)
    try:
        if isinstance(content, (dict, list)):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
    except Exception:
        pass

def _item_proto() -> Dict[str, Any]:
    return {
        "id": None,
        "source_id": SOURCE_ID,
        "source_url": None,
        "categoria": "actividad",
        "titulo": "",
        "descripcion": "",
        "fecha_inicio": None,
        "fecha_fin": None,
        "ocurrencias": [],
        "all_day": True,
        "lugar": PLACE,
        "imagen_url": None,
        "timezone": TZ,
        "status": "activo",
        "parse_confidence": 0.8,
    }

def _mk_id(url: str) -> str:
    import hashlib
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:16]

# --------------------------
# 1) The Events Calendar API
# --------------------------

def _collect_tribe_v1(base: str) -> List[Dict[str, Any]]:
    api = base.rstrip("/") + "/wp-json/tribe/events/v1/events?per_page=100"
    data = fetch_json(api)
    _dump("latermica_tribe_v1.json", data)
    events = data.get("events", []) or []
    out: List[Dict[str, Any]] = []
    for ev in events:
        title = clean_text(ev.get("title"))
        url = ev.get("url")
        if not url:
            continue
        img = (ev.get("image") or {}).get("url")
        sd = ev.get("start_date_details", {}).get("timestamp")
        ed = ev.get("end_date_details", {}).get("timestamp")
        fi = epoch_ms_to_iso(sd * 1000) if isinstance(sd, (int, float)) else None
        ff = epoch_ms_to_iso(ed * 1000) if isinstance(ed, (int, float)) else None

        it = _item_proto()
        it.update({
            "id": _mk_id(url),
            "source_url": url,
            "titulo": title or "",
            "fecha_inicio": fi,
            "fecha_fin": ff,
            "imagen_url": img,
            "parse_confidence": 0.9,
        })
        out.append(it)
    return out

def _collect_tribe_v1_alt(base: str) -> List[Dict[str, Any]]:
    """
    Algunas instalaciones requieren /events/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    o usan paginación/page. Probamos dos variantes simples.
    """
    out: List[Dict[str, Any]] = []
    urls = [
        base.rstrip("/") + "/wp-json/tribe/events/v1/events/",
        base.rstrip("/") + "/wp-json/tribe/events/v1/events?page=1&per_page=50",
    ]
    for api in urls:
        try:
            data = fetch_json(api)
            _dump("latermica_tribe_v1_alt.json", data)
            evs = data.get("events", []) or []
            for ev in evs:
                title = clean_text(ev.get("title"))
                url = ev.get("url")
                if not url:
                    continue
                img = (ev.get("image") or {}).get("url")
                sd = ev.get("start_date_details", {}).get("timestamp")
                ed = ev.get("end_date_details", {}).get("timestamp")
                fi = epoch_ms_to_iso(sd * 1000) if isinstance(sd, (int, float)) else None
                ff = epoch_ms_to_iso(ed * 1000) if isinstance(ed, (int, float)) else None

                it = _item_proto()
                it.update({
                    "id": _mk_id(url),
                    "source_url": url,
                    "titulo": title or "",
                    "fecha_inicio": fi,
                    "fecha_fin": ff,
                    "imagen_url": img,
                    "parse_confidence": 0.9,
                })
                out.append(it)
            if out:
                break
        except Exception:
            continue
    return out

# --------------------------
# 2) Modern Events Calendar
# --------------------------

def _collect_mec(base: str) -> List[Dict[str, Any]]:
    """
    MEC suele exponer algo como /wp-json/mec/v1/events
    """
    api = base.rstrip("/") + "/wp-json/mec/v1/events"
    data = fetch_json(api)
    _dump("latermica_mec.json", data)
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for ev in data:
        title = clean_text(ev.get("title"))
        url = ev.get("permalink") or ev.get("url")
        if not url:
            continue
        img = ev.get("thumbnail") or None
        fi = epoch_ms_to_iso(ev.get("start") if isinstance(ev.get("start"), int) else None)
        ff = epoch_ms_to_iso(ev.get("end") if isinstance(ev.get("end"), int) else None)
        it = _item_proto()
        it.update({
            "id": _mk_id(url),
            "source_url": url,
            "titulo": title or "",
            "fecha_inicio": fi,
            "fecha_fin": ff,
            "imagen_url": img,
            "parse_confidence": 0.8,
        })
        out.append(it)
    return out

# --------------------------
# 3) WP REST genérico (CPT)
# --------------------------

def _collect_wp_v2(base: str) -> List[Dict[str, Any]]:
    """
    Fallback genérico al CPT típico de Events Calendar
    """
    api = base.rstrip("/") + "/wp-json/wp/v2/tribe_events?per_page=100"
    try:
        arr = fetch_json(api)
        _dump("latermica_wp_v2.json", arr)
    except Exception:
        return []
    if not isinstance(arr, list):
        return []
    out: List[Dict[str, Any]] = []
    for ev in arr:
        title = clean_text(ev.get("title", {}).get("rendered"))
        url = ev.get("link")
        it = _item_proto()
        it.update({
            "id": _mk_id(url or ""),
            "source_url": url,
            "titulo": title or "",
            "parse_confidence": 0.6,
        })
        out.append(it)
    return out

# --------------------------
# 4) Fallback HTML (agenda)
# --------------------------

DATE_PAT = re.compile(
    r"(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|"
    r"setiembre|octubre|noviembre|diciembre)\s+(\d{4})",
    re.IGNORECASE
)

MONTH_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12
}

def _to_iso(day: int, mon_name: str, year: int) -> Optional[str]:
    m = MONTH_ES.get(mon_name.lower())
    if not m:
        return None
    return f"{year:04d}-{m:02d}-{day:02d}"

def _html_cards(html: str, base: str) -> List[Dict[str, Any]]:
    _dump("latermica_agenda.html", html)
    soup = BeautifulSoup(html, "lxml")
    # heurística: tarjetas con título/enlace
    cards = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        text = clean_text(a.get_text())
        # En La Térmica suelen ser /actividad/... o /evento/... o posts normales con categoría Agenda
        if not text:
            continue
        if href.startswith("/"):
            url = urljoin(base, href)
        elif href.startswith("http"):
            url = href
        else:
            continue
        # filtra navegación, rrss, etc.
        if any(s in url for s in ("/categoria/", "facebook.com", "instagram.com", "twitter.com", "tienda", "/wp-json/")):
            continue
        # Guardamos posibles tarjetas (dedupe por URL luego)
        cards.append((text, url))

    # dedupe por url
    seen = set()
    out: List[Dict[str, Any]] = []
    for title, url in cards:
        if url in seen:
            continue
        seen.add(url)
        it = _item_proto()
        it.update({
            "id": _mk_id(url),
            "source_url": url,
            "titulo": title,
            "parse_confidence": 0.5,
        })
        out.append(it)

    # intenta sacar una fecha aproximada del HTML global (muy aproximado)
    txt = soup.get_text(" ", strip=True)
    m = DATE_PAT.search(txt)
    if m:
        d = int(m.group(1))
        mon = m.group(2)
        y = int(m.group(3))
        iso = _to_iso(d, mon, y)
        for it in out:
            if not it["fecha_inicio"]:
                it["fecha_inicio"] = iso
                it["fecha_fin"] = iso
    return out

def _collect_html(base: str) -> List[Dict[str, Any]]:
    urls = [
        urljoin(base, "/agenda/"),
        base,
    ]
    bag: List[Dict[str, Any]] = []
    for u in urls:
        try:
            html = fetch_html(u)
            bag.extend(_html_cards(html, base))
            if bag:
                break
        except Exception:
            continue
    return bag

# --------------------------
# entrypoint
# --------------------------

def collect(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    urls = (cfg.get("urls") or {})
    base = urls.get("base") or DEFAULT_BASE

    # 1) Tribe v1
    try:
        items = _collect_tribe_v1(base)
        if items:
            return items
    except Exception:
        pass

    # 1b) Tribe variantes
    try:
        items = _collect_tribe_v1_alt(base)
        if items:
            return items
    except Exception:
        pass

    # 2) MEC
    try:
        items = _collect_mec(base)
        if items:
            return items
    except Exception:
        pass

    # 3) WP v2 CPT
    try:
        items = _collect_wp_v2(base)
        if items:
            return items
    except Exception:
        pass

    # 4) HTML fallback (agenda / home)
    try:
        items = _collect_html(base)
        return items
    except Exception:
        return []
