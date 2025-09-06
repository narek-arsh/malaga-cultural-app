
import requests, re
from bs4 import BeautifulSoup
from ..utils import parse_spanish_date_text
from ..base import make_id, now_iso

SOURCE_ID = "picasso"

BASE = "https://www.museopicassomalaga.org"

def fetch_expos(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for card in soup.select("div.exhibitionCurrentFuture"):
        # dates
        spans = card.select("span.exhibitionCurrentFuture-date")
        date_text = " ".join([s.get_text(" ", strip=True) for s in spans if s.get_text(strip=True)])
        start, end, occ, allday = parse_spanish_date_text(date_text)
        title = (card.select_one("p.mb-1.h1") or card.select_one("h2") or card).get_text(" ", strip=True)
        subtitle_el = card.select_one("p.h2")
        if subtitle_el:
            title = f"{title} — {subtitle_el.get_text(' ', strip=True)}"
        link = None
        a = card.select_one("a[href]")
        if a:
            link = a["href"]
            if link.startswith("/"):
                link = BASE + link
        img_el = card.select_one("div.exhibitionCurrentFuture-background img")
        img = img_el["src"] if img_el and img_el.has_attr("src") else None
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
            "lugar":"Museo Picasso Málaga",
            "imagen_url": img,
            "timezone":"Europe/Madrid",
            "first_seen": now_iso(),
            "last_seen": now_iso(),
            "status":"activo",
            "parse_confidence": 0.9 if start and end else 0.6
        }
        item["id"] = make_id(item)
        items.append(item)
    return items

def fetch_activities(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for card in soup.select("a.colorCard"):
        date_text = ""
        dt = card.select_one("span.colorCard-date")
        if dt:
            date_text = dt.get_text(" ", strip=True)
        start, end, occ, allday = parse_spanish_date_text(date_text)
        title = card.select_one("h2.colorCard-title")
        title = title.get_text(" ", strip=True) if title else card.get_text(" ", strip=True)
        cat_el = card.select_one("p.p3")
        categoria = "actividad"
        if cat_el:
            cat_txt = cat_el.get_text(" ", strip=True).lower()
            if "música" in cat_txt or "músicas" in cat_txt:
                categoria = "concierto"
            elif "conferencia" in cat_txt:
                categoria = "charla"
        link = card.get("href")
        if link and link.startswith("/"):
            link = BASE + link
        img_el = card.select_one(".colorCard-image img")
        img = img_el["src"] if img_el and img_el.has_attr("src") else None
        item = {
            "id":"",
            "source_id": SOURCE_ID,
            "source_url": link or url,
            "categoria": categoria,
            "titulo": title,
            "descripcion":"",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [d.isoformat() for d in occ] if occ else [],
            "all_day": True,
            "lugar":"Museo Picasso Málaga",
            "imagen_url": img,
            "timezone":"Europe/Madrid",
            "first_seen": now_iso(),
            "last_seen": now_iso(),
            "status":"activo",
            "parse_confidence": 0.85 if start else 0.6
        }
        item["id"] = make_id(item)
        items.append(item)
    return items
