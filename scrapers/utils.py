# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import re
from datetime import datetime, date
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

# Meses EN/ES abreviados más varias variantes
MONTHS_MAP = {
    # Español
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "SET": 9, "OCT": 10, "NOV": 11, "DIC": 12,
    # Inglés
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}

DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": DEFAULT_UA,
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    })
    s.timeout = 30
    return s

def fetch_html(url: str) -> str:
    s = _session()
    r = s.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def fetch_json(url: str) -> Dict[str, Any]:
    s = _session()
    r = s.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def absolutize(base: str, href: str) -> str:
    return urljoin(base, href)

def clean_text(x: Optional[str]) -> str:
    if not x:
        return ""
    return re.sub(r"\s+", " ", x).strip()

def parse_iso(d: Optional[str]) -> Optional[str]:
    if not d:
        return None
    d = d.strip()
    try:
        return datetime.fromisoformat(d).date().isoformat()
    except Exception:
        return None

def parse_dd_mm_yyyy_range(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Soporta "19/03/2024 — 30/01/2028" (distintos guiones).
    """
    t = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"(\d{2}/\d{2}/\d{4})\s*[–—-]\s*(\d{2}/\d{2}/\d{4})", t)
    if not m:
        return None, None
    def to_iso(ddmmyyyy: str) -> str:
        d, mth, y = ddmmyyyy.split("/")
        return f"{y}-{int(mth):02d}-{int(d):02d}"
    return to_iso(m.group(1)), to_iso(m.group(2))

def parse_spanish_date_text_short(txt: str) -> Optional[str]:
    """
    Convierte '26 SEP' a 'YYYY-09-26' (con año actual).
    """
    if not txt:
        return None
    txt = clean_text(txt).upper()
    parts = txt.split()
    if len(parts) == 2 and parts[0].isdigit():
        day = int(parts[0])
        mon = MONTHS_MAP.get(parts[1][:3])
        if mon:
            y = date.today().year
            return f"{y}-{mon:02d}-{day:02d}"
    return None

def epoch_ms_to_iso(ms: Optional[int]) -> Optional[str]:
    if not ms and ms != 0:
        return None
    try:
        return datetime.utcfromtimestamp(ms/1000).date().isoformat()
    except Exception:
        return None

def pick(obj: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    return {k: obj.get(k) for k in keys}
