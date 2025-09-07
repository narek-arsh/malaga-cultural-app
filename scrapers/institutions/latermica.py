import re
from datetime import datetime
from bs4 import BeautifulSoup
from scrapers.utils import fetch_html, parse_spanish_date_text

BASE_URL = "https://www.latermicamalaga.com/agenda/"

def collect():
    html = fetch_html(BASE_URL)
    soup = BeautifulSoup(html, "html.parser")

    events = []

    cards = soup.select("div.event-card")  # Ajustar según HTML real
    for card in cards:
        title_el = card.select_one(".event-title")
        date_el = card.select_one(".event-date")
        time_el = card.select_one(".event-time")
        link_el = card.select_one("a")

        if not title_el or not date_el:
            continue

        title = title_el.get_text(strip=True)
        raw_date = date_el.get_text(strip=True)
        raw_time = time_el.get_text(strip=True) if time_el else None
        url = link_el["href"] if link_el else BASE_URL

        # Parse fechas
        start_date, end_date = parse_date_range(raw_date)

        events.append({
            "id": f"latermica::{slugify(title)}::{start_date}",
            "title": title,
            "place": "La Térmica",
            "url": url,
            "date_start": start_date,
            "date_end": end_date,
            "time": raw_time,
            "source": "latermica",
        })

    return events


def parse_date_range(text: str):
    """
    Convierte '26 SEP' o '02 OCT – 04 OCT' en (fecha_inicio, fecha_fin).
    """
    text = text.upper().strip()

    # Rango de fechas
    if "–" in text or "-" in text:
        parts = re.split(r"[–-]", text)
        start_txt, end_txt = parts[0].strip(), parts[1].strip()
        start_date = parse_spanish_date_text(start_txt)
        end_date = parse_spanish_date_text(end_txt)
        return start_date, end_date

    # Fecha simple
    return parse_spanish_date_text(text), parse_spanish_date_text(text)


def slugify(txt: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", txt.lower()).strip("-")
