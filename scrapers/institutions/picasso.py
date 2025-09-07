# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from ..utils import (
    fetch_html, clean_text, parse_dd_mm_yyyy_range, epoch_ms_to_iso
)

SOURCE_ID = "picasso"
BASE = "https://www.museopicassomalaga.org"
TZ = "Europe/Madrid"
PLACE = "Museo Picasso Málaga"

def _parse_next_data(html: str) -> Optional[dict]:
    """Extrae el objeto JSON de <script id="__NEXT_DATA__">...</script>."""
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    try:
        return json.loads(tag.string)
    except Exception:
        return None

def _item_proto() -> Dict[str, Any]:
    return {
        "id": None,
        "source_id": SOURCE_ID,
        "source_url": None,
        "categoria": None,   # "exposicion" | "actividad"
        "titulo": None,
        "descripcion": "",
        "fecha_inicio": None,
        "fecha_fin": None,
        "ocurrencias": [],
        "all_day": True,
        "lugar": PLACE,
        "imagen_url": None,
        "timezone": TZ,
        "status": "activo",
        "parse_confidence": 0.9,
    }

def _mk_id(url: str) -> str:
    # id estable a partir de URL
    import hashlib
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:16]

def _collect_expos(list_url: str) -> List[Dict[str, Any]]:
    html = fetch_html(list_url)
    soup = BeautifulSoup(html, "lxml")
    # recoge enlaces a /exposiciones/...
    links = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if href.startswith("/exposiciones/"):
            links.append(BASE + href)
        elif href.startswith(BASE + "/exposiciones/"):
            links.append(href)
    links = sorted(set(links))

    items: List[Dict[str, Any]] = []
    for url in links:
        dh = fetch_html(url)
        dsoup = BeautifulSoup(dh, "lxml")
        title = clean_text(dsoup.find("h1").get_text()) if dsoup.find("h1") else None

        # 1) Intenta rango por patrón "dd/mm/yyyy — dd/mm/yyyy" en la página
        text = dsoup.get_text(" ", strip=True)
        fi, ff = parse_dd_mm_yyyy_range(text)
        # 2) Si falla, intenta __NEXT_DATA__ (cuando esté)
        if not (fi and ff):
            nd = _parse_next_data(dh)
            if nd:
                # Algunos detalles podrían ir aquí en el futuro si los exponen en Next
                pass

        item = _item_proto()
        item.update({
            "id": _mk_id(url),
            "source_url": url,
            "categoria": "exposicion",
            "titulo": title or "",
            "fecha_inicio": fi,
            "fecha_fin": ff,
            "imagen_url": None,
        })
        items.append(item)

    return items

def _collect_activities(list_url: str) -> List[Dict[str, Any]]:
    """
    La página /actividades es Next.js y expone todo en __NEXT_DATA__:
    - pageProps.featuredActivities -> lista de dicts
    - pageProps.related_activities -> lista de objetos {"id":..., "activity": {...}}
    Campos que nos interesan: title, slug (para URL), start_date/end_date (epoch ms), dates_literal,
    main_type.title (categoría humana), thumbnail.url (imagen).
    """
    html = fetch_html(list_url)
    nd = _parse_next_data(html)
    items: List[Dict[str, Any]] = []
    if not nd:
        return items

    try:
        pageProps = nd.get("props", {}).get("pageProps", {})
        fa = pageProps.get("featuredActivities", []) or []
        ra = pageProps.get("related_activities", []) or []
    except Exception:
        fa, ra = [], []

    seen_urls = set()

    def push_from_obj(obj: Dict[str, Any]):
        t = clean_text(obj.get("title"))
        slug = obj.get("slug")
        if not slug:
            return
        url = f"{BASE}/actividades/{slug}"
        if url in seen_urls:
            return
        seen_urls.add(url)

        fi = epoch_ms_to_iso(obj.get("start_date"))
        ff = epoch_ms_to_iso(obj.get("end_date"))
        img = (obj.get("thumbnail", {}) or {}).get("url") or None

        item = _item_proto()
        item.update({
            "id": _mk_id(url),
            "source_url": url,
            "categoria": "actividad",
            "titulo": t or "",
            "fecha_inicio": fi,
            "fecha_fin": ff,
            "imagen_url": img,
        })
        items.append(item)

    # featuredActivities: ya viene plano
    for x in fa:
        push_from_obj(x)

    # related_activities: viene como {"id":..., "activity": {...}}
    for x in ra:
        act = x.get("activity")
        if not isinstance(act, dict):
            continue
        push_from_obj(act)

    return items

def collect(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    sections = (cfg.get("sections") or {})
    urls = (cfg.get("urls") or {})

    out: List[Dict[str, Any]] = []
    if sections.get("expos"):
        out.extend(_collect_expos(urls.get("expos_list")))
    if sections.get("activities"):
        out.extend(_collect_activities(urls.get("activities_list")))
    return out
