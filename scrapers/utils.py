# --- NEXT.js helpers & date coercion ---

import json as _json, re as _re
from datetime import datetime as _dt, date as _date

def extract_next_data(html: str):
    """
    Devuelve el dict del <script id="__NEXT_DATA__">...</script> o None.
    """
    m = _re.search(r'<script id="__NEXT_DATA__"\s+type="application/json">(.+?)</script>', html, flags=_re.S|_re.I)
    if not m:
        return None
    return _json.loads(m.group(1))

def coerce_date(val):
    """
    Soporta:
    - int (ms epoch) -> date
    - str (YYYY-MM-DD) -> date
    - None -> None
    """
    if val is None:
        return None
    if isinstance(val, int):
        # milisegundos epoch (UTC)
        return _dt.utcfromtimestamp(val/1000).date()
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        try:
            return _dt.fromisoformat(val).date()
        except Exception:
            # último recurso: dd/mm/yyyy o dd-mm-yyyy
            for sep in ("/","-"):
                parts = val.split(sep)
                if len(parts)==3 and len(parts[2])==4:
                    d,m,y = parts
                    try:
                        return _date(int(y), int(m), int(d))
                    except Exception:
                        pass
    return None
