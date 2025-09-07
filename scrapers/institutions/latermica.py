import re
from bs4 import BeautifulSoup
from scrapers.utils import fetch_html, parse_spanish_date_text

def collect(cfg) -> list[dict]:
    """
    Scraper para la agenda de La Térmica (https://www.latermicamalaga.com/agenda/)
    """
    url = cfg["urls"]["activities_list"]
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    items = []
    for card in soup.select("article.ajde_events"):  # estructura típica de su agenda
        title_el = card.select_one(".event_title a")
        date_el = card.select_one(".dates")
        link_el = title_el["href"] if title_el else None

        title = title_el.get_text(strip=True) if title_el else "Sin título"
        raw_date = date_el.get_text(strip=True) if date_el else ""
        start_date = parse_spanish_date_text(raw_date.split()[0]) if raw_date else None

        items.append({
            "id": f"latermica-{link_el or title}",
            "title": title,
            "url": link_el,
            "date": raw_date,
            "start_date": start_date,
            "source": "latermica",
        })

    return items
