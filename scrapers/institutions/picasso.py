from ..utils import (
    fetch_html,
    extract_next_data,
    coerce_date,
    make_item,          # asumiendo existe en tu utils
    clean_text,         # asumiendo existe en tu utils
)

BASE = "https://www.museopicassomalaga.org"

def scrape_activities(session):
    """
    Lee https://www.museopicassomalaga.org/actividades
    y extrae actividades de __NEXT_DATA__ (featuredActivities + related_activities).
    """
    url = f"{BASE}/actividades"
    html = fetch_html(session, url)
    data = extract_next_data(html)
    items = []

    if not data:
        return items  # no hay JSON embebido

    # Navegación segura
    props = (data.get("props") or {}).get("pageProps") or {}
    featured = props.get("featuredActivities") or []
    rels = props.get("related_activities") or []

    def normalize_activity(a, container="featured"):
        """
        a: puede ser un dict de 'featuredActivities' (todo plano)
           o un dict {'activity': {...}} de 'related_activities'
        Devuelve dict normalizado o None
        """
        node = a
        if container == "related":
            node = a.get("activity") or {}

        title = clean_text(node.get("title") or "")
        slug  = node.get("slug") or ""
        if not title or not slug:
            return None

        start = coerce_date(node.get("start_date"))
        end   = coerce_date(node.get("end_date"))
        dates_literal = (node.get("dates_literal") or "").strip()

        thumb = None
        # featured: node['thumbnail'] -> {'url': ...}
        # related:  node['thumbnail'] -> objeto similar (en el HTML visto)
        thumb_node = node.get("thumbnail") or {}
        thumb = thumb_node.get("url") or None

        main_type = (node.get("main_type") or {}).get("title") or ""
        categoria = "actividad"  # mantenemos categorización global
        lugar = "Museo Picasso Málaga"

        item = make_item(
            source_id="picasso",
            source_url=f"{BASE}/actividades/{slug}",
            categoria=categoria,
            titulo=title,
            descripcion="",    # si quieres, podrías usar node.get('lead') o recortar 'content'
            fecha_inicio=start,
            fecha_fin=end,
            ocurrencias=[],    # si necesitas desglosar dates_literal en múltiples, lo hacemos luego
            all_day=True,
            lugar=lugar,
            imagen_url=thumb,
            timezone="Europe/Madrid",
            extra={
                "dates_literal": dates_literal,
                "main_type": main_type,
                "container": container,
            }
        )
        return item

    # featuredActivities (estructura plana con start_date en ms)
    for fa in featured:
        it = normalize_activity(fa, container="featured")
        if it:
            items.append(it)

    # related_activities (nodos con {"activity": {...}} y start_date en ISO)
    for ra in rels:
        it = normalize_activity(ra, container="related")
        if it:
            items.append(it)

    return items
