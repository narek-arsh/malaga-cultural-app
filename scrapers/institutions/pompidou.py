# scrapers/institutions/pompidou.py
import re
from bs4 import BeautifulSoup
from ..utils import parse_spanish_date_text, fetch_html
from ..base import make_id, now_iso

SOURCE_ID = "pompidou"
BASE = "https://centrepompidou-malaga.eu"

def _abs(url): return url if url.startswith("http") else (BASE + url)

def fetch_expos(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select("article, .elementor-post"):
        title_el = card.select_one(".elementor-post__title, h2, h3")
        if not title_el:
            continue
        title = title_el.get_text(" ", strip=True)
        txt = card.get_text(" ", strip=True)
        # busca 'dd/mm/yyyy – dd/mm/yyyy' o 'dd/mm/yyyy — mm/yyyy'
        m = re.search(r"\d{1,2}/\d{1,2}/\d{4}\s*[-—]\s*(\d{1,2}/\d{1,2}/\d{4}|[01]?\d/\d{4})", txt)
        date_text = m.group(0) if m else txt
        start, end, occ, allday = parse_spanish_date_text(date_text)
        a = card.select_one("a[href]")
        link = _abs(a["href"]) if a else url
        img_el = card.select_one("img[src], img[data-src]")
        img = (img_el.get("src") or img_el.get("data-src")) if img_el else None
        item = {
            "id":"", "source_id": SOURCE_ID, "source_url": link,
            "categoria":"exposicion","titulo":title,"descripcion":"",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [], "all_day": True,
            "lugar":"Centre Pompidou Málaga","imagen_url": img,
            "timezone":"Europe/Madrid","first_seen": now_iso(),"last_seen": now_iso(),
            "status":"activo","parse_confidence": 0.8 if start and end else 0.6
        }
        item["id"] = make_id(item)
        items.append(item)
    return items

def fetch_activities(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select(".tribe-events-calendar-list__event, article.type-tribe_events, article"):
        title_el = card.select_one(".tribe-events-calendar-list__event-title, h2, h3")
        if not title_el:
            continue
        title = title_el.get_text(" ", strip=True)
        # los bloques datetime suelen estar en estas clases
        date_text = ""
        for sel in [
            ".tribe-events-calendar-list__event-datetime",
            ".tribe-event-date-start", ".tribe-event-date-end",
            ".tribe-events-content", "time"
        ]:
            el = card.select_one(sel)
            if el:
                t = el.get_text(" ", strip=True)
                if re.search(r"\d|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|/|am|pm|-", t, re.I):
                    date_text = t; break
        if not date_text:
            date_text = card.get_text(" ", strip=True)
        start, end, occ, allday = parse_spanish_date_text(date_text)
        a = card.select_one("a[href]")
        link = _abs(a["href"]) if a else url
        img_el = card.select_one("img[src], img[data-src]")
        img = (img_el.get("src") or img_el.get("data-src")) if img_el else None
        item = {
            "id":"", "source_id": SOURCE_ID, "source_url": link,
            "categoria":"actividad","titulo":title,"descripcion":"",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [d.isoformat() for d in occ] if occ else [],
            "all_day": True, "lugar":"Centre Pompidou Málaga","imagen_url": img,
            "timezone":"Europe/Madrid","first_seen": now_iso(),"last_seen": now_iso(),
            "status":"activo","parse_confidence": 0.75 if start else 0.6
        }
        item["id"] = make_id(item)
        items.append(item)
    return items
