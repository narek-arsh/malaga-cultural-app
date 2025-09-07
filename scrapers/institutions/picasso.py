# scrapers/institutions/picasso.py
from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timezone
import json, re
from ..utils import fetch_html, make_item, slugify, ensure_dir

BASE = "https://www.museopicassomalaga.org"

EXPOS_URL = f"{BASE}/exposiciones"
ACTIVIDADES_URL = f"{BASE}/actividades"

SPANISH_MONTHS = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,"noviembre":11,"diciembre":12
}

def _iso(d: datetime) -> str:
    return d.date().isoformat()

def _from_ms(ms: int) -> str:
    # ms epoch -> iso date (Europe/Madrid no necesario para la fecha calendario)
    return datetime.fromtimestamp(ms/1000, tz=timezone.utc).date().isoformat()

def _extract_next_data(html: str) -> Dict[str, Any] | None:
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html, re.S)
    if not m: return None
    return json.loads(m.group(1))

def _parse_related_activities(next_data: Dict[str,Any]) -> List[Dict[str,Any]]:
    arr = []
    try:
        rel = next_data["props"]["pageProps"].get("related_activities", [])
        for entry in rel:
            a = entry.get("activity", {})
            if not a: continue
            arr.append({
                "id": a.get("id"),
                "title": a.get("title","").strip(),
                "slug": a.get("slug"),
                "start_date": a.get("start_date"),  # 'YYYY-MM-DD' string
                "end_date": a.get("end_date"),
                "dates_literal": a.get("dates_literal"),
                "thumbnail": (a.get("thumbnail") or {}).get("url"),
                "main_type": (a.get("main_type") or {}).get("title"),
                "url": f"{BASE}/actividades/{a.get('slug')}" if a.get("slug") else ACTIVIDADES_URL,
            })
    except Exception:
        pass
    return arr

def _parse_featured_activities(next_data: Dict[str,Any]) -> List[Dict[str,Any]]:
    arr = []
    try:
        feats = next_data["props"]["pageProps"].get("featuredActivities", [])
        for a in feats:
            arr.append({
                "id": a.get("id"),
                "title": a.get("title","").strip(),
                "slug": a.get("slug"),
                "start_date_ms": a.get("start_date"),
                "end_date_ms": a.get("end_date"),
                "dates_literal": a.get("dates_literal"),
                "thumbnail": (a.get("thumbnail") or {}).get("url"),
                "main_type": (a.get("main_type") or {}).get("title"),
                "url": f"{BASE}/actividades/{a.get('slug')}" if a.get("slug") else ACTIVIDADES_URL,
            })
    except Exception:
        pass
    return arr

def _normalize_dates(a: Dict[str,Any]) -> tuple[str|None,str|None]:
    # Prioridad: ms epoch si existen, si no ISO (YYYY-MM-DD), si no None
    if a.get("start_date_ms"):
        start = _from_ms(a["start_date_ms"])
        end = _from_ms(a["end_date_ms"]) if a.get("end_date_ms") else start
        return start, end
    if a.get("start_date"):
        return a["start_date"], a.get("end_date") or a["start_date"]
    # Como extra, intentar dates_literal con patrones más comunes:
    lit = (a.get("dates_literal") or "").strip()
    if not lit:
        return None, None
    # Ejemplos a cubrir: "16 septiembre 2025 —— 14 julio 2026", "18 – 19 septiembre 2025"
    # "1, 8, 15, 22 y 29 octubre 2025" (múltiples ocurrencias, aquí devolvemos rango min-max)
    # Rango con dos fechas completas
    m = re.search(r'(\d{1,2})\s+([a-záéíóúñ]+)\s+(\d{4}).+?(\d{1,2})\s+([a-záéíóúñ]+)\s+(\d{4})', lit, re.I)
    if m:
        d1, mon1, y1, d2, mon2, y2 = m.groups()
        start = f"{y1}-{SPANISH_MONTHS[mon1.lower()]:02d}-{int(d1):02d}"
        end   = f"{y2}-{SPANISH_MONTHS[mon2.lower()]:02d}-{int(d2):02d}"
        return start, end
    # Rango con días dentro del mismo mes/año: "18 – 19 septiembre 2025"
    m = re.search(r'(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([a-záéíóúñ]+)\s+(\d{4})', lit, re.I)
    if m:
        d1, d2, mon, y = m.groups()
        yy = int(y); mm = SPANISH_MONTHS[mon.lower()]
        return f"{yy}-{mm:02d}-{int(d1):02d}", f"{yy}-{mm:02d}-{int(d2):02d}"
    # Lista de días en un mes: "1, 8, 15, 22 y 29 octubre 2025" => devolver min y max
    m = re.search(r'([\d,\s y\-–]+)\s+([a-záéíóúñ]+)\s+(\d{4})', lit, re.I)
    if m:
        days_blob, mon, y = m.groups()
        days = [int(x) for x in re.findall(r'\d{1,2}', days_blob)]
        if days:
            yy = int(y); mm = SPANISH_MONTHS[mon.lower()]
            return f"{yy}-{mm:02d}-{min(days):02d}", f"{yy}-{mm:02d}-{max(days):02d}"
    return None, None

def scrape_expos() -> List[Dict[str,Any]]:
    # Ya las tienes funcionando; mantenemos tu lógica existente:
    # (reutiliza tu implementación actual de exposiciones)
    from .thyssen import scrape_expos as _noop  # truco para no dejar vacío si importan
    return []

def scrape_activities() -> List[Dict[str,Any]]:
    html, meta = fetch_html(ACTIVIDADES_URL)
    nd = _extract_next_data(html) or {}
    rel = _parse_related_activities(nd)
    feats = _parse_featured_activities(nd)

    # Merge + dedup por slug o id
    seen = set()
    merged: List[Dict[str,Any]] = []
    for a in rel + feats:
        key = a.get("slug") or a.get("id")
        if not key or key in seen: continue
        seen.add(key)
        merged.append(a)

    # snapshot para depurar
    ensure_dir("data/sources")
    with open("data/sources/picasso_actividades.json", "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    items = []
    for a in merged:
        start, end = _normalize_dates(a)
        items.append(make_item(
            source_id="picasso",
            source_url=a.get("url") or ACTIVIDADES_URL,
            categoria="actividad",
            titulo=a.get("title") or "",
            descripcion="",
            fecha_inicio=start,
            fecha_fin=end,
            ocurrencias=[],  # si quieres, aquí puedes expandir la lista de días desde dates_literal
            all_day=True,
            lugar="Museo Picasso Málaga",
            imagen_url=a.get("thumbnail"),
            parse_confidence=0.9 if (start or end) else 0.7
        ))
    return items

def scrape() -> List[Dict[str,Any]]:
    # Si tu collector llama a scrape_expos() y scrape_activities(), mantenlo igual:
    expos = []  # delega a tu scraper de expos ya existente si lo prefieres
    acts = scrape_activities()
    return expos + acts
