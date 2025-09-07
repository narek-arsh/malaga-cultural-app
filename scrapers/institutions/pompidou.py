# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List
from bs4 import BeautifulSoup

from ..utils import fetch_html, clean_text

SOURCE_ID = "pompidou"
BASE = "https://centrepompidou-malaga.eu"
TZ = "Europe/Madrid"
PLACE = "Centre Pompidou Málaga"

def _item_proto() -> Dict[str, Any]:
    return {
        "id": None,
        "source_id": SOURCE_ID,
        "source_url": None,
        "categoria": None,
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
        "parse_confidence": 0.7,
    }

def _mk_id(url: str) -> str:
    import hashlib
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:16]

def _collect_list(list_url: str, cat: str) -> List[Dict[str, Any]]:
    html = fetch_html(list_url)
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if cat == "exposicion" and "/exposicion/" in href:
            links.append(href)
        if cat == "actividad" and "/event/" in href:
            links.append(href)
    # absolutiza y dedupe
    full = []
    for href in links:
        if href.startswith("http"):
            full.append(href)
        else:
            full.append(BASE + ("" if href.startswith("/") else "/") + href)
    full = sorted(set(full))

    items: List[Dict[str, Any]] = []
    for url in full:
        dh = fetch_html(url)
        dsoup = BeautifulSoup(dh, "lxml")
        title = clean_text(dsoup.find("h1").get_text()) if dsoup.find("h1") else ""
        img = None
        og = dsoup.find("meta", attrs={"property": "og:image"})
        if og:
            img = og.get("content")

        it = _item_proto()
        it.update({
            "id": _mk_id(url),
            "source_url": url,
            "categoria": "exposicion" if "/exposicion/" in url else "actividad",
            "titulo": title,
            "imagen_url": img,
        })
        items.append(it)
    return items

def collect(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    sections = (cfg.get("sections") or {})
    urls = (cfg.get("urls") or {})
    out: List[Dict[str, Any]] = []
    if sections.get("expos"):
        out.extend(_collect_list(urls.get("expos_list"), "exposicion"))
    if sections.get("activities"):
        out.extend(_collect_list(urls.get("activities_list"), "actividad"))
    return out
