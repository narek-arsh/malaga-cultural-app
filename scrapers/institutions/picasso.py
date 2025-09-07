# scrapers/institutions/picasso.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup  # asegúrate de tener bs4 en requirements.txt
from ..utils import fetch_html  # ya existe y lo usas en otros scrapers

SOURCE_ID = "picasso"
BASE = "https://www.museopicassomalaga.org"
TZ = "Europe/Madrid"
PLACE = "Museo Picasso Málaga"


# ------------------------------
# Utilidades internas
# ------------------------------
def _clean_text(x: Optional[str]) -> str:
    if not x:
        return ""
    return re.sub(r"\s+", " ", x).strip()

def _to_date_yyyy_mm_dd(s: Optional[str]) -> Optional[str]:
    """Convierte 'dd/mm/aaaa' -> 'aaaa-mm-dd' o devuelve s si ya está normalizada o None si no hay dato."""
    if not s:
        return None
    s = s.strip()
    # Si ya viene 'aaaa-mm-dd'
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    # Si viene 'dd/mm/aaaa'
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        d, mth, y = m.groups()
        return f"{y}-{mth}-{d}"
    # Otras variantes (no romper): intenta parseo laxo con dayfirst
    try:
        dt = datetime.strptime(s, "%d %B %Y")  # p.ej. "16 septiembre 2025"
        return dt.strftime("%Y-%m-%d")
    except Exception:
        try:
            dt = datetime.strptime(s, "%d %b %Y")  # abreviado
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None

def _from_epoch_ms(ms: Optional[int]) -> Optional[str]:
    if not isinstance(ms, int):
        return None
    try:
        return datetime.utcfromtimestamp(ms / 1000.0).strftime("%Y-%m-%d")
    except Exception:
        return None

def _make_item(**kw) -> Dict[str, Any]:
    """Estructura homogénea como la que está guardando el collector al escribir catalog.jsonl."""
    return {
        "source_id": SOURCE_ID,
        "source_url": kw.get("source_url") or "",
        "categoria": kw.get("categoria") or "",
        "titulo": _clean_text(kw.get("titulo")),
        "descripcion": _clean_text(kw.get("descripcion")),
        "fecha_inicio": kw.get("fecha_inicio"),
        "fecha_fin": kw.get("fecha_fin"),
        "ocurrencias": kw.get("ocurrencias") or [],
        "all_day": True,
        "lugar": PLACE,
        "imagen_url": kw.get("imagen_url"),
        "timezone": TZ,
    }

# ------------------------------
# Exposiciones
# ------------------------------
def _collect_expos() -> List[Dict[str, Any]]:
    url = f"{BASE}/exposiciones"
    html, meta = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    items: List[Dict[str, Any]] = []

    # Tarjetas de exposiciones (página publica)
    # Buscamos enlaces dentro de /exposiciones/<slug>
    for a in soup.select('a[href^="/exposiciones/"]'):
        href = a.get("href") or ""
        # Filtra index propio (/exposiciones) y anchors
        if href.rstrip("/") == "/exposiciones" or "#" in href:
            continue
        expo_url = BASE + href

        # Título (intenta dentro del enlace o adyacente)
        title = ""
        # hay estructura con dos líneas: artista — subtítulo; si no, usa texto plano
        title = _clean_text(a.get_text(" ") or "")
        if not title:
            # fallback: encabezado cercano
            h = a.find(["h2", "h3"])
            if h:
                title = _clean_text(h.get_text(" ") or "")

        # Fechas: la web muestra dos fechas visibles; las obtuvimos bien antes, pero aquí
        # no forzamos. Si no las podemos ver en el listado, las dejamos en None (collector ya te estaba guardando por expos).
        start = None
        end = None

        # Imagen (si hay)
        img = a.find("img")
        img_url = img.get("src") if img and img.has_attr("src") else None
        if img_url and img_url.startswith("/"):
            img_url = BASE + img_url

        items.append(
            _make_item(
                source_url=expo_url,
                categoria="exposicion",
                titulo=title,
                fecha_inicio=start,
                fecha_fin=end,
                imagen_url=img_url,
            )
        )

    # Dedup por URL
    seen = set()
    deduped = []
    for it in items:
        if it["source_url"] in seen:
            continue
        seen.add(it["source_url"])
        deduped.append(it)

    return deduped

# ------------------------------
# Actividades (lee __NEXT_DATA__)
# ------------------------------
def _collect_activities() -> List[Dict[str, Any]]:
    url = f"{BASE}/actividades"
    html, meta = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # 1) Extrae el JSON de Next.js
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        # Si no hay JSON embebido, no hay actividades renderizadas del lado servidor
        return []

    try:
        data = json.loads(script.string)
    except Exception:
        return []

    # En Next el JSON útil está en props.pageProps
    page_props = (data or {}).get("props", {}).get("pageProps", {}) or {}

    # Las actividades aparecen en varios campos según el estado:
    # - "featuredActivities": lista de destacadas (con start_date/end_date en epoch ms)
    # - "related_activities": a veces estructura con {"activity": {...}}
    # Tomamos ambos si existen.
    activities: List[Dict[str, Any]] = []

    # 2) featuredActivities (más estable)
    for act in page_props.get("featuredActivities", []) or []:
        # Formato típico:
        # { id, title, slug, start_date: epoch_ms, end_date: epoch_ms,
        #   dates_literal, tickets_url, ... , thumbnail: {url}, main_type: {title} }
        title = _clean_text(act.get("title"))
        slug = act.get("slug") or ""
        source_url = f"{BASE}/actividades/{slug}" if slug else url
        img_url = None
        thumb = act.get("thumbnail") or {}
        if isinstance(thumb, dict):
            img_url = thumb.get("url")

        start = _from_epoch_ms(act.get("start_date"))
        end = _from_epoch_ms(act.get("end_date"))

        # Si el JSON trae sólo dates_literal (p.ej. “18 – 19 septiembre 2025”), lo usamos como fallback.
        if not start and not end:
            dates_literal = _clean_text(act.get("dates_literal"))
            # No hacemos parsing fino de rangos con guiones en español aquí; guardamos None y ya está visible en “descripcion”
            # o podrías mapearlo a ocurrencias puntuales si quisieras.
        categoria = "actividad"
        if isinstance(act.get("main_type"), dict) and act["main_type"].get("title"):
            # puedes mapear a “Conferencias, Talleres, …” si algún upstream lo usa
            pass

        activities.append(
            _make_item(
                source_url=source_url,
                categoria=categoria,
                titulo=title,
                fecha_inicio=start,
                fecha_fin=end,
                imagen_url=img_url,
                descripcion=_clean_text(act.get("lead") or ""),
            )
        )

    # 3) related_activities (cuando la pestaña “Ahora y próximamente” está vacía,
    #    suelen quedar aquí igualmente serializadas)
    for rel in page_props.get("related_activities", []) or []:
        # a veces es {"id": X, "activity": {...}}
        node = rel.get("activity") if isinstance(rel, dict) and "activity" in rel else rel
        if not isinstance(node, dict):
            continue

        title = _clean_text(node.get("title"))
        slug = node.get("slug") or ""
        source_url = f"{BASE}/actividades/{slug}" if slug else url

        # Fechas pueden venir como ISO (start_date/end_date en texto) o epoch en featured.
        # En este bloque, suelen venir como ISO yyyy-mm-dd (según lo que viste en el HTML).
        start = node.get("start_date")
        end = node.get("end_date")
        start = _to_date_yyyy_mm_dd(start) if start else None
        end = _to_date_yyyy_mm_dd(end) if end else None

        img_url = None
        thumb = node.get("thumbnail") or {}
        if isinstance(thumb, dict):
            # Strapi suele dar “url” absoluto
            img_url = thumb.get("url")

        activities.append(
            _make_item(
                source_url=source_url,
                categoria="actividad",
                titulo=title,
                fecha_inicio=start,
                fecha_fin=end,
                imagen_url=img_url,
                descripcion=_clean_text(node.get("lead") or ""),
            )
        )

    # Dedup por URL
    seen = set()
    deduped = []
    for it in activities:
        if it["source_url"] in seen:
            continue
        seen.add(it["source_url"])
        deduped.append(it)

    return deduped

# ------------------------------
# Punto de entrada del scraper
# ------------------------------
def collect() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    try:
        expos = _collect_expos()
        items.extend(expos)
    except Exception:
        # no rompemos todo si falla una pata
        pass
    try:
        acts = _collect_activities()
        items.extend(acts)
    except Exception:
        pass
    return items
