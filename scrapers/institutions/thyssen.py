# scrapers/institutions/thyssen.py
import re
from bs4 import BeautifulSoup
from ..utils import parse_spanish_date_text, fetch_html
from ..base import make_id, now_iso

SOURCE_ID = "thyssen"
BASE = "https://www.carmenthyssenmalaga.org"

def _abs(url):
    if not url:
        return url
    return url if url.startswith("http") else (BASE + url)

def _parse_dates_from_detail(detail_url):
    try:
        html = fetch_html(detail_url)
        s = BeautifulSoup(html, "html.parser")
        # buscar patrones “Del … al …” o fechas sueltas en el cuerpo
        txt = s.get_text(" ", strip=True)
        start, end, occ, allday = parse_spanish_date_text(txt)
        return start, end, occ, allday
    except Exception:
        return None, None, [], True

def fetch_expos(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.select("a[href]"):
        href = a.get("href","")
        # EXPO real: enlaces que contienen '/exposicion/' (evita prensa, vídeo, visitas virtuales)
        if "/exposicion/" not in href:
            continue
        card = a
        # Título
        title_el = None
        for sel in ["h2","h3",".title",".h3",".card-title",".exhibition-title","p.mb-1.h1"]:
            e = card.select_one(sel)
            if e and e.get_text(strip=True):
                title_el = e; break
        title = title_el.get_text(" ", strip=True) if title_el else a.get_text(" ", strip=True)
        # Fecha en listado (si aparece cerca del link)
        date_text = ""
        parent_txt = a.find_parent().get_text(" ", strip=True) if a.find_parent() else ""
        # heurística: coge la primera cadena con meses o dd/mm/yyyy
        m = re.search(r"(del\s+.*?\d{4}|[0-3]?\d/[01]?\d/\d{4}\s*[-—]\s*(?:[0-3]?\d/[01]?\d/\d{4}|[01]?\d/\d{4}))", parent_txt, re.I)
        if m:
            date_text = m.group(1)
        start, end, occ, allday = parse_spanish_date_text(date_text)
        link = _abs(href)

        # Fallback: si no obtuvimos fechas del listado, abrir la ficha y buscarlas allí
        if not start or not end:
            start, end, occ, allday = _parse_dates_from_detail(link)

        item = {
            "id": "",
            "source_id": SOURCE_ID,
            "source_url": link,
            "categoria": "exposicion",
            "titulo": title,
            "descripcion": "",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [d.isoformat() for d in occ] if occ else [],
            "all_day": True,
            "lugar": "Museo Carmen Thyssen Málaga",
            "imagen_url": None,
            "timezone": "Europe/Madrid",
            "first_seen": now_iso(),
            "last_seen": now_iso(),
            "status": "activo",
            "parse_confidence": 0.9 if start and end else 0.6
        }
        item["id"] = make_id(item)
        items.append(item)
    return items

def fetch_activities(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # coge solo tarjetas con link a '/actividad/'
    for a in soup.select("a[href*='/actividad/']"):
        title_el = a.select_one("h2, h3, .h3, .card-title, .title")
        title = title_el.get_text(" ", strip=True) if title_el else a.get_text(" ", strip=True)
        # fecha en span/time cercano
        date_text = ""
        for el in a.select("time, .date, .fecha, .card-date, span, p"):
            t = el.get_text(" ", strip=True)
            if re.search(r"\d|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|/", t, re.I):
                date_text = t; break
        if not date_text:
            # última oportunidad: texto de la tarjeta
            date_text = a.get_text(" ", strip=True)
        start, end, occ, allday = parse_spanish_date_text(date_text)
        item = {
            "id": "",
            "source_id": SOURCE_ID,
            "source_url": _abs(a["href"]),
            "categoria": "actividad",
            "titulo": title,
            "descripcion": "",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [d.isoformat() for d in occ] if occ else [],
            "all_day": True,
            "lugar": "Museo Carmen Thyssen Málaga",
            "imagen_url": None,
            "timezone": "Europe/Madrid",
            "first_seen": now_iso(),
            "last_seen": now_iso(),
            "status": "activo",
            "parse_confidence": 0.85 if start else 0.6
        }
        item["id"] = make_id(item)
        items.append(item)
    return items
