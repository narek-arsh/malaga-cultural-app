# scrapers/institutions/picasso.py
import re
from bs4 import BeautifulSoup
from ..utils import parse_spanish_date_text, fetch_html
from ..base import make_id, now_iso

SOURCE_ID = "picasso"
BASE = "https://www.museopicassomalaga.org"

def _abs(url): 
    return url if url.startswith("http") else (BASE + url)

def _parse_dates_from_detail(detail_url):
    """Abre la ficha y extrae fechas desde cualquier bloque legible."""
    try:
        html = fetch_html(detail_url)
        s = BeautifulSoup(html, "html.parser")

        # 1) candidatos explícitos
        cand = []
        for sel in [
            "time", "span", ".colorCard-date", ".hero-date", ".dates", ".meta",
            "p", "h3", "h4", ".event-date", ".carddate", ".event__date"
        ]:
            for el in s.select(sel):
                t = el.get_text(" ", strip=True)
                if any(x in t.lower() for x in [
                    "enero","febrero","marzo","abril","mayo","junio","julio",
                    "agosto","septiembre","octubre","noviembre","diciembre","/","-","—","–"
                ]):
                    cand.append(t)

        # 2) si no, usa todo el texto de la página
        text = "  ".join(cand) if cand else s.get_text(" ", strip=True)
        return parse_spanish_date_text(text)
    except Exception:
        return None, None, [], True

def fetch_expos(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # Exposiciones: tarjetas claras con fechas en 2 spans
    for card in soup.select("div.exhibitionCurrentFuture"):
        spans = card.select("span.exhibitionCurrentFuture-date")
        date_text = " ".join([s.get_text(" ", strip=True) for s in spans]) or card.get_text(" ", strip=True)
        start, end, occ, allday = parse_spanish_date_text(date_text)

        title = (card.select_one("p.mb-1.h1") or card.select_one("h2") or card).get_text(" ", strip=True)
        subtitle_el = card.select_one("p.h2")
        if subtitle_el:
            title = f"{title} — {subtitle_el.get_text(' ', strip=True)}"

        a = card.select_one("a[href]")
        link = _abs(a["href"]) if a else url
        img_el = card.select_one("div.exhibitionCurrentFuture-background img[src]")
        img = img_el["src"] if img_el else None

        item = {
            "id":"", "source_id": SOURCE_ID, "source_url": link,
            "categoria":"exposicion","titulo":title,"descripcion":"",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [], "all_day": True,
            "lugar":"Museo Picasso Málaga","imagen_url": img,
            "timezone":"Europe/Madrid","first_seen": now_iso(),"last_seen": now_iso(),
            "status":"activo","parse_confidence": 0.9 if start and end else 0.7
        }
        item["id"] = make_id(item)
        items.append(item)
    return items

def _discover_activity_links_from_scripts(html):
    """
    Si el listado no trae tarjetas (CSR), rastrea scripts en busca de rutas /actividades/slug
    Devuelve lista de URLs absolutas sin duplicados.
    """
    links = set()
    # 1) hrefs directos en el HTML (aunque no haya tarjetas)
    for m in re.finditer(r'href=["\'](/actividades/[^"\']+)["\']', html):
        links.add(m.group(1))

    # 2) rutas en JSON embebido (Next.js __NEXT_DATA__, Strapi, etc.)
    for m in re.finditer(r'(/actividades/[a-z0-9\-_/]+)', html, flags=re.I):
        links.add(m.group(1))

    # normaliza y filtra mínimos
    urls = []
    for u in links:
        if "/actividades/" in u:
            urls.append(_abs(u))
    return sorted(set(urls))

def fetch_activities(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # 1) camino normal: tarjetas del listado
    cards = soup.select("a.colorCard[href*='/actividades/']")
    if cards:
        for a in cards:
            dt_el = a.select_one("span.colorCard-date")
            date_text = dt_el.get_text(" ", strip=True) if dt_el else a.get_text(" ", strip=True)
            start, end, occ, allday = parse_spanish_date_text(date_text)

            link = _abs(a.get("href"))
            if not start or not end:
                s2, e2, occ2, allday2 = _parse_dates_from_detail(link)
                if s2 and e2:
                    start, end, occ, allday = s2, e2, occ2, allday2

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
                "id":"", "source_id": SOURCE_ID, "source_url": link,
                "categoria": categoria, "titulo": title, "descripcion":"",
                "fecha_inicio": start.isoformat() if start else None,
                "fecha_fin": end.isoformat() if end else None,
                "ocurrencias": [d.isoformat() for d in occ] if occ else [],
                "all_day": True, "lugar":"Museo Picasso Málaga", "imagen_url": img,
                "timezone":"Europe/Madrid","first_seen": now_iso(),"last_seen": now_iso(),
                "status":"activo","parse_confidence": 0.9 if start else 0.7
            }
            item["id"] = make_id(item)
            items.append(item)
        return items

    # 2) fallback CSR: no hay tarjetas → busca rutas en <script> y abre cada ficha
    links = _discover_activity_links_from_scripts(html)
    for link in links:
        html2 = fetch_html(link)
        s = BeautifulSoup(html2, "html.parser")

        # Título: intenta h1/h2 primero
        title = None
        for sel in ["h1", "h2", ".colorCard-title", ".hero-title", "title"]:
            el = s.select_one(sel)
            if el and el.get_text(strip=True):
                title = el.get_text(" ", strip=True)
                break
        if not title:
            title = link.rsplit("/", 1)[-1].replace("-", " ").title()

        # Categoría textual (si aparece)
        categoria = "actividad"
        cat_el = s.find(string=re.compile("Músicas|Música|Conferenc", re.I))
        if cat_el and "músic" in cat_el.lower():
            categoria = "concierto"
        elif cat_el and "conferenc" in cat_el.lower():
            categoria = "charla"

        # Fechas desde la ficha
        start, end, occ, allday = _parse_dates_from_detail(link)

        # Imagen (mejor esfuerzo)
        img = None
        for sel in ["img[src]", "meta[property='og:image']"]:
            el = s.select_one(sel)
            if el:
                img = el.get("src") or el.get("content")
                if img: break

        item = {
            "id":"", "source_id": SOURCE_ID, "source_url": link,
            "categoria": categoria, "titulo": title, "descripcion":"",
            "fecha_inicio": start.isoformat() if start else None,
            "fecha_fin": end.isoformat() if end else None,
            "ocurrencias": [d.isoformat() for d in occ] if occ else [],
            "all_day": True, "lugar":"Museo Picasso Málaga", "imagen_url": img,
            "timezone":"Europe/Madrid","first_seen": now_iso(),"last_seen": now_iso(),
            "status":"activo","parse_confidence": 0.85 if start else 0.6
        }
        item["id"] = make_id(item)
        items.append(item)

    return items
