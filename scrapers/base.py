
import hashlib, json, time
from datetime import datetime
from typing import Dict, Any

def make_id(fields: Dict[str, Any])->str:
    s = "|".join([str(fields.get(k,"")) for k in ["source_id","titulo","lugar","fecha_inicio","fecha_fin","source_url"]])
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

def now_iso():
    return datetime.utcnow().isoformat()+"Z"
