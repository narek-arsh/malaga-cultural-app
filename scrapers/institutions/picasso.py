# scrapers/institutions/picasso.py
from bs4 import BeautifulSoup
from ..utils import parse_spanish_date_text, fetch_html
from ..base import make_id, now_iso

SOURCE_ID = "picasso"
BASE = "https://www.museopicassomalaga.org"

def _abs(url):
    return url if url.startswith("http") else (BASE + url)

def fetch_expos(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select("div.exhibitionCurrentFuture"):
        spans = card.select("span.exhibitionCurrentFuture-date")
        date_text = " ".join([s.get_text(" ", strip=True) for s in spans if s.get_text(strip=True)])
        start, end, occ, allday = parse_spanish_date_text(date_text)
        title = (card.select_one("p.mb-1.h1") or card.select_one("h2") or card).get_text(" ", strip=True)
        subtitle_el = card.select_one("p.h2")
        if subtitle_el:
            title = f"{title} — {subtitle_el.get_text(' ', strip=True)}"
        a = card.select_one("a[href]")
        link = _abs(a["href"]) if a else url
        img_el = card.select_one("div.exhibitionCurrentFuture-background img")
        img = img_el["src"] if img_el and img_el.has_attr("src") else None
        item = {
            "id":"", "source_id": SOURCE_ID, "source_url": link,
            "categoria":"exposicion","titulo":title,"descripcion":"",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [], "all_day": True,
            "lugar":"Museo Picasso Málaga","imagen_url": img,
            "timezone":"Europe/Madrid","first_seen": now_iso(),"last_seen": now_iso(),
            "status":"activo","parse_confidence": 0.9 if start and end else 0.6
        }
        item["id"] = make_id(item)
        items.append(item)
    return items

def fetch_activities(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # las tarjetas de actividades enlazan con <a class="colorCard ...">
    for a in soup.select("a.colorCard[href*='/actividades/']"):
        dt_el = a.select_one("span.colorCard-date")
        date_text = dt_el.get_text(" ", strip=True) if dt_el else a.get_text(" ", strip=True)
        start, end, occ, allday = parse_spanish_date_text(date_text)
        title_el = a.select_one("h2.colorCard-title")
        title = title_el.get_text(" ", strip=True) if title_el else a.get_text(" ", strip=True)
        cat_el = a.select_one("p.p3")
        categoria = "actividad"
        if cat_el:
            cat_txt = cat_el.get_text(" ", strip=True).lower()
            if "música" in cat_txt or "músicas" in cat_txt:
                categoria = "concierto"
            elif "conferencia" in cat_txt or "conferencias" in cat_txt:
                categoria = "charla"
        img_el = a.select_one(".colorCard-image img[src]")
        img = img_el["src"] if img_el else None
        item = {
            "id":"", "source_id": SOURCE_ID, "source_url": _abs(a["href"]),
            "categoria": categoria, "titulo": title, "descripcion":"",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [d.isoformat() for d in occ] if occ else [],
            "all_day": True, "lugar":"Museo Picasso Málaga", "imagen_url": img,
            "timezone":"Europe/Madrid","first_seen": now_iso(),"last_seen": now_iso(),
            "status":"activo","parse_confidence": 0.9 if start else 0.6
        }
        item["id"] = make_id(item)
        items.append(item)
    return items
