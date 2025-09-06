
import requests, re
from bs4 import BeautifulSoup
from ..utils import parse_spanish_date_text
from ..base import make_id, now_iso

SOURCE_ID = "pompidou"

BASE = "https://centrepompidou-malaga.eu"

def fetch_expos(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for card in soup.select("article, .grid-item, .exhibition, .elementor-post"):
        title = None
        for sel in ["h2","h3",".elementor-post__title"]:
            el = card.select_one(sel)
            if el and el.get_text(strip=True):
                title = el.get_text(strip=True)
                break
        if not title:
            continue
        # date string appears often near the title or as meta
        date_text = ""
        txt = card.get_text(" ", strip=True)
        # look for dd/mm/yyyy - dd/mm/yyyy OR dd/mm/yyyy - mm/yyyy
        m = re.search(r"\d{1,2}/\d{1,2}/\d{4}\s*[–—-]\s*(\d{1,2}/\d{1,2}/\d{4}|\d{1,2}/\d{4})", txt)
        if m:
            date_text = m.group(0)
        else:
            # also handle month/year only ranges
            m2 = re.search(r"\d{1,2}/\d{1,2}/\d{4}.*", txt)
            if m2:
                date_text = m2.group(0)
        start, end, occ, allday = parse_spanish_date_text(date_text)
        link = None
        a = card.select_one("a[href]")
        if a:
            link = a["href"]
            if link.startswith("/"):
                link = BASE + link
        img = None
        img_el = card.select_one("img[src]")
        if img_el:
            img = img_el.get("src") or img_el.get("data-src")
        item = {
            "id":"",
            "source_id": SOURCE_ID,
            "source_url": link or url,
            "categoria": "exposicion",
            "titulo": title,
            "descripcion":"",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [],
            "all_day": True,
            "lugar":"Centre Pompidou Málaga",
            "imagen_url": img,
            "timezone":"Europe/Madrid",
            "first_seen": now_iso(),
            "last_seen": now_iso(),
            "status":"activo",
            "parse_confidence": 0.7
        }
        item["id"] = make_id(item)
        items.append(item)
    return items

def fetch_activities(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for card in soup.select("article, .tribe-events-calendar-list__event, .type-tribe_events"):
        title = None
        for sel in ["h2","h3",".tribe-events-calendar-list__event-title"]:
            el = card.select_one(sel)
            if el and el.get_text(strip=True):
                title = el.get_text(strip=True)
                break
        if not title:
            continue
        txt = card.get_text(" ", strip=True)
        # examples: 'agosto 6 - agosto 29' or 'julio 30 / 6:00 PM - 7:30 PM'
        # pick the first line that includes month names or time
        date_text = ""
        for el in card.select("time, .tribe-events-calendar-list__event-datetime, .tribe-event-date-start, .tribe-event-date-end, .tribe-event-time"):
            t = el.get_text(" ", strip=True).lower()
            if any(m in t for m in ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre","am","pm","/","-"]):
                date_text = t; break
        if not date_text:
            date_text = txt
        start, end, occ, allday = parse_spanish_date_text(date_text)
        link = None
        a = card.select_one("a[href]")
        if a:
            link = a["href"]
            if link.startswith("/"):
                link = BASE + link
        img = None
        img_el = card.select_one("img[src]")
        if img_el:
            img = img_el.get("src") or img_el.get("data-src")
        item = {
            "id":"",
            "source_id": SOURCE_ID,
            "source_url": link or url,
            "categoria": "actividad",
            "titulo": title,
            "descripcion":"",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [d.isoformat() for d in occ] if occ else [],
            "all_day": True,
            "lugar":"Centre Pompidou Málaga",
            "imagen_url": img,
            "timezone":"Europe/Madrid",
            "first_seen": now_iso(),
            "last_seen": now_iso(),
            "status":"activo",
            "parse_confidence": 0.6
        }
        item["id"] = make_id(item)
        items.append(item)
    return items
