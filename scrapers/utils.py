# scrapers/utils.py
import re
import calendar
import requests
from datetime import datetime, date
from dateutil import parser as duparser

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

def fetch_html(url: str, timeout: int = 30) -> str:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": UA})
    r.raise_for_status()
    return r.text

MONTHS_ES = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,"agosto":8,"septiembre":9,"setiembre":9,
    "octubre":10,"noviembre":11,"diciembre":12,
    "ene":1,"feb":2,"mar":3,"abr":4,"may":5,"jun":6,"jul":7,"ago":8,"sep":9,"oct":10,"nov":11,"dic":12
}

def last_day_of_month(year:int, month:int)->int:
    return calendar.monthrange(year, month)[1]

def _norm_day(s:str)->int:
    return int(s.strip().zfill(2))

def parse_spanish_date_text(text:str, default_year=None):
    """
    Devuelve: (inicio: date, fin: date, ocurrencias: list[date], all_day: bool)
    Cubierto: 
      - 'Del 01 de abril al 14 de septiembre de 2025'
      - 'Del 04 al 11 de septiembre de 2025'
      - '22 de septiembre de 2025'
      - '03/07/2025 – 31/01/2027'
      - '21/02/2025 — 02/2026'
      - '1, 8, 15, 22 y 29 octubre 2025'
      - 'Junio —— diciembre 2025'
      - '1 enero —— 21 diciembre 2025'
      - '18 – 19 septiembre 2025'
    """
    if not text:
        return None, None, [], True

    t = " ".join(text.lower().replace("—","-").replace("–","-").split())

    # DD/MM/YYYY - DD/MM/YYYY
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        d1,m1,y1,d2,m2,y2 = map(int, m.groups())
        return date(y1,m1,d1), date(y2,m2,d2), [], True

    # DD/MM/YYYY - MM/YYYY
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d{1,2})/(\d{4})", t)
    if m:
        d1,m1,y1,m2,y2 = map(int, m.groups())
        return date(y1,m1,d1), date(y2,m2,last_day_of_month(y2,m2)), [], True

    # Del DD (de mes)? al DD de mes de YYYY
    rx = re.compile(r"del\s+(\d{1,2})(?:\s+de\s+([a-záéíóú]+))?\s+al\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})")
    m = rx.search(t)
    if m:
        d1, month1, d2, month2, y = m.groups()
        y = int(y)
        m1 = MONTHS_ES[month2] if not month1 else MONTHS_ES[month1]
        return date(y,m1,_norm_day(d1)), date(y,MONTHS_ES[month2],_norm_day(d2)), [], True

    # single day: DD de mes de YYYY
    m = re.match(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})$", t)
    if m:
        d, mon, y = m.groups()
        return date(int(y), MONTHS_ES[mon], _norm_day(d)), date(int(y), MONTHS_ES[mon], _norm_day(d)), [], True

    # DD - DD mes YYYY
    m = re.match(r"(\d{1,2})\s*-\s*(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})", t)
    if m:
        d1,d2,mon,y = m.groups()
        y=int(y)
        mnum = MONTHS_ES[mon]
        return date(y,mnum,_norm_day(d1)), date(y,mnum,_norm_day(d2)), [], True

    # mes - mes YYYY
    m = re.match(r"([a-záéíóú]+)\s*-\s*([a-záéíóú]+)\s+(\d{4})", t)
    if m:
        mon1, mon2, y = m.groups()
        y = int(y)
        m1 = MONTHS_ES[mon1]; m2 = MONTHS_ES[mon2]
        return date(y,m1,1), date(y,m2,last_day_of_month(y,m2)), [], True

    # lista de días: '1, 8, 15, 22 y 29 octubre 2025'
    m = re.match(r"([\d,\sy]+)\s+([a-záéíóú]+)\s+(\d{4})", t)
    if m and "," in m.group(1):
        days = re.findall(r"\d{1,2}", m.group(1))
        mon = MONTHS_ES[m.group(2)]
        y = int(m.group(3))
        occ = [date(y,mon,int(d)) for d in days]
        return min(occ), max(occ), occ, True

    # 'DD mes YYYY - DD mes YYYY'
    m = re.match(r"(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})\s*-\s*(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})", t)
    if m:
        d1, mon1, y1, d2, mon2, y2 = m.groups()
        return date(int(y1), MONTHS_ES[mon1], _norm_day(d1)), date(int(y2), MONTHS_ES[mon2], _norm_day(d2)), [], True

    # fallback: intenta parsear algo razonable (día primero)
    try:
        dt = duparser.parse(text, dayfirst=True, default=duparser.parse(f"1/1/{default_year or datetime.now().year}"))
        d = dt.date()
        return d, d, [], True
    except Exception:
        return None, None, [], True
