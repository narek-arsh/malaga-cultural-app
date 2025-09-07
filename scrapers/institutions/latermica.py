# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..utils import fetch_json, clean_text, epoch_ms_to_iso

SOURCE_ID = "latermica"
BASE = "https://www.latermicamalaga.com/"
TZ = "Europe/Madrid"
PLACE = "La Térmica (Málaga)"

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

def _collect_via_tribe_events_v1(base: str) -> List[Dict[str, Any]]:
    """
    The Events Calendar REST oficial:
    GET /wp-json/tribe/events/v1/events?per_page=100
    Campos: events[*].title, url, image.url, start_date_details.timestamp, end_date_details.timestamp
    """
    api = base.rstrip("/") + "/wp-json/tribe/events/v1/events?per_page=100"
    data = fetch_json(api)
    events = data.get("events", []) or []
    out: List[Dict[str, Any]] = []
    for ev in events:
        title = clean_text(ev.get("title"))
        url = ev.get("url")
        if not url:
            continue
        img = (ev.get("image") or {}).get("url")
        # timestamps en segundos a ms
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
        })
        out.append(it)
    return out

def _collect_via_wp_v2(base: str) -> List[Dict[str, Any]]:
    """
    Fallback: muchos sitios exponen el CPT como /wp-json/wp/v2/tribe_events?per_page=100
    Campos: title.rendered, link, featured_media -> habría que expandir, pero lo dejamos opcional
    start_date/end_date a veces vienen en meta → si no, caen sin fechas.
    """
    api = base.rstrip("/") + "/wp-json/wp/v2/tribe_events?per_page=100"
    try:
        arr = fetch_json(api)
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
        })
        out.append(it)
    return out

def collect(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    base = (cfg.get("urls") or {}).get("base") or BASE
    # 1) Intenta API oficial del plugin The Events Calendar
    try:
        v1 = _collect_via_tribe_events_v1(base)
        if v1:
            return v1
    except Exception:
        pass
    # 2) Fallback genérico al CPT via wp/v2
    try:
        v2 = _collect_via_wp_v2(base)
        return v2
    except Exception:
        pass
    return []
