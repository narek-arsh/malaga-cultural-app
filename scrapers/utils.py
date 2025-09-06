# --- REEMPLAZA SOLO ESTA FUNCIÓN EN scrapers/utils.py ---
def parse_spanish_date_text(text:str, default_year=None):
    """
    Devuelve: (inicio: date, fin: date, ocurrencias: list[date], all_day: bool)
    Cobertura:
      - Del 01 de abril al 14 de septiembre de 2025
      - Del 04 al 11 de septiembre de 2025
      - 22 de septiembre de 2025
      - 03/07/2025 – 31/01/2027
      - 21/02/2025 — 02/2026
      - 1, 8, 15, 22 y 29 octubre 2025
      - Junio —— diciembre 2025
      - 1 enero —— 21 diciembre 2025
      - 18 – 19 septiembre 2025
      - Cualquier texto que contenga dos DD/MM/YYYY en cualquier posición
    """
    if not text:
        return None, None, [], True

    t = " ".join(
        text.lower()
        .replace("\u2014","-")  # em dash
        .replace("\u2013","-")  # en dash
        .replace("—","-").replace("–","-")
        .split()
    )

    # 1) caso general robusto: si encontramos dos fechas DD/MM/YYYY en cualquier sitio, usamos la 1ª y la última
    m_all = re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if len(m_all) >= 2:
        d1, m1, y1 = map(int, m_all[0])
        d2, m2, y2 = map(int, m_all[-1])
        return date(y1, m1, d1), date(y2, m2, d2), [], True

    # 2) DD/MM/YYYY - MM/YYYY
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d{1,2})/(\d{4})", t)
    if m:
        d1,m1,y1,m2,y2 = map(int, m.groups())
        return date(y1,m1,d1), date(y2,m2,last_day_of_month(y2,m2)), [], True

    # 3) Del DD (de mes)? al DD de mes de YYYY
    rx = re.compile(r"del\s+(\d{1,2})(?:\s+de\s+([a-záéíóú]+))?\s+al\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})")
    m = rx.search(t)
    if m:
        d1, month1, d2, month2, y = m.groups()
        y = int(y)
        m1 = MONTHS_ES[month2] if not month1 else MONTHS_ES[month1]
        return date(y,m1,int(d1)), date(y,MONTHS_ES[month2],int(d2)), [], True

    # 4) día único: DD de mes de YYYY
    m = re.match(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})$", t)
    if m:
        d, mon, y = m.groups()
        return date(int(y), MONTHS_ES[mon], int(d)), date(int(y), MONTHS_ES[mon], int(d)), [], True

    # 5) DD - DD mes YYYY
    m = re.match(r"(\d{1,2})\s*-\s*(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})", t)
    if m:
        d1,d2,mon,y = m.groups()
        y=int(y); mnum = MONTHS_ES[mon]
        return date(y,mnum,int(d1)), date(y,mnum,int(d2)), [], True

    # 6) mes - mes YYYY
    m = re.match(r"([a-záéíóú]+)\s*-\s*([a-záéíóú]+)\s+(\d{4})", t)
    if m:
        mon1, mon2, y = m.groups()
        y = int(y); m1 = MONTHS_ES[mon1]; m2 = MONTHS_ES[mon2]
        return date(y,m1,1), date(y,m2,last_day_of_month(y,m2)), [], True

    # 7) lista de días: '1, 8, 15, 22 y 29 octubre 2025'
    m = re.match(r"([\d,\sy]+)\s+([a-záéíóú]+)\s+(\d{4})", t)
    if m and "," in m.group(1):
        days = re.findall(r"\d{1,2}", m.group(1))
        mon = MONTHS_ES[m.group(2)]
        y = int(m.group(3))
        occ = [date(y,mon,int(d)) for d in days]
        return min(occ), max(occ), occ, True

    # 8) 'DD mes YYYY - DD mes YYYY'
    m = re.match(r"(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})\s*-\s*(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})", t)
    if m:
        d1, mon1, y1, d2, mon2, y2 = m.groups()
        return date(int(y1), MONTHS_ES[mon1], int(d1)), date(int(y2), MONTHS_ES[mon2], int(d2)), [], True

    # 9) fallback
    try:
        dt = duparser.parse(text, dayfirst=True, default=duparser.parse(f"1/1/{default_year or datetime.now().year}"))
        d = dt.date()
        return d, d, [], True
    except Exception:
        return None, None, [], True
