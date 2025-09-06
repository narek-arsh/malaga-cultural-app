
import requests, json, re
from bs4 import BeautifulSoup
from datetime import date
from ..utils import parse_spanish_date_text
from ..base import make_id, now_iso

SOURCE_ID = "thyssen"

def fetch_expos(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for card in soup.select("article, div.card, li, div.exhibition, div.item"):
        # heuristic: title header
        title = None
        for sel in ["h2","h3",".title",".h3",".card-title"]:
            el = card.select_one(sel)
            if el and el.get_text(strip=True):
                title = el.get_text(strip=True)
                break
        if not title:
            continue
        # date text
        date_text = ""
        for sel in [".date",".fecha",".card-date","time",".meta",".exhibition-date","p"]:
            el = card.select_one(sel)
            if el and re.search(r"\d{1,2}|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre", el.get_text(strip=True, separator=" " ), re.I):
                date_text = el.get_text(" ", strip=True)
                break
        if not date_text:
            # try within card text
            txt = card.get_text(" ", strip=True)
            m = re.search(r"del|[0-9]{1,2}\s*de\s*[A-Za-z]|[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}", txt, re.I)
            if m:
                date_text = txt[m.start():]
        start, end, occ, allday = parse_spanish_date_text(date_text)
        link = None
        a = card.select_one("a[href]")
        if a:
            link = a["href"]
            if link.startswith("/"):
                link = "https://www.carmenthyssenmalaga.org" + link
        img = None
        img_el = card.select_one("img[src]")
        if img_el:
            img = img_el["src"]
        item = {
            "id": "",
            "source_id": SOURCE_ID,
            "source_url": link or url,
            "categoria": "exposicion",
            "titulo": title,
            "descripcion": "",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [d.isoformat() for d in occ] if occ else [],
            "all_day": allday,
            "lugar": "Museo Carmen Thyssen Málaga",
            "imagen_url": img,
            "timezone": "Europe/Madrid",
            "first_seen": now_iso(),
            "last_seen": now_iso(),
            "status": "activo",
            "parse_confidence": 0.7
        }
        item["id"] = make_id(item)
        items.append(item)
    return items

def fetch_activities(url):
    # Similar strategy to expos; the page structure is close
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for card in soup.select("article, div.card, li, a"):
        title = None
        for sel in ["h2","h3",".title",".h3",".card-title"]:
            el = card.select_one(sel)
            if el and el.get_text(strip=True):
                title = el.get_text(strip=True)
                break
        if not title:
            continue
        # category text hint
        cat = "actividad"
        # date text
        txt = card.get_text(" ", strip=True)
        # pick a span that likely has date
        date_text = ""
        for el in card.select("time, .date, .fecha, .card-date, span, p"):
            t = el.get_text(" ", strip=True)
            if re.search(r"\d", t) and re.search(r"enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|/", t, re.I):
                date_text = t; break
        if not date_text:
            # fallback scan
            m = re.search(r"(\d{1,2}.*\d{4})", txt)
            date_text = m.group(1) if m else ""
        start, end, occ, allday = parse_spanish_date_text(date_text)
        link = None
        a = card.select_one("a[href]")
        if a:
            link = a["href"]
            if link.startswith("/"):
                link = "https://www.carmenthyssenmalaga.org" + link
        img = None
        img_el = card.select_one("img[src]")
        if img_el:
            img = img_el["src"]
        item = {
            "id": "",
            "source_id": SOURCE_ID,
            "source_url": link or url,
            "categoria": cat,
            "titulo": title,
            "descripcion": "",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [d.isoformat() for d in occ] if occ else [],
            "all_day": allday,
            "lugar": "Museo Carmen Thyssen Málaga",
            "imagen_url": img,
            "timezone": "Europe/Madrid",
            "first_seen": now_iso(),
            "last_seen": now_iso(),
            "status": "activo",
            "parse_confidence": 0.6
        }
        item["id"] = make_id(item)
        items.append(item)
    return items
