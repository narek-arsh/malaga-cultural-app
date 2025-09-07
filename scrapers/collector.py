import json, os, sys, logging, hashlib
from datetime import datetime
from importlib import import_module

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CATALOG = os.path.join(DATA_DIR, "catalog.jsonl")
CATALOG_LAST_OK = os.path.join(DATA_DIR, "catalog.jsonl.last_ok")
RUNLOG = os.path.join(DATA_DIR, "run.log")

logging.basicConfig(stream=sys.stdout, level=os.getenv("LOG_LEVEL","INFO"))
log = logging.getLogger("collector")

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def write_jsonl(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

def read_jsonl(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out

def dedup(items):
    seen=set()
    out=[]
    for it in items:
        key = it.get("id") or hashlib.sha1((it.get("source_id","")+it.get("source_url","")+it.get("titulo","")).encode("utf-8")).hexdigest()[:16]
        if key in seen: 
            continue
        it["id"]=key
        seen.add(key)
        out.append(it)
    return out

FEEDS = [
    # Ajusta aquí según quieras activar/pausar
    {"id":"picasso", "active": True, "sections":{"expos": True, "activities": True}},
    {"id":"latermica", "active": True, "sections":{"activities": True}},
    # {"id":"thyssen", "active": True, "sections":{"expos": True, "activities": True}},
    # {"id":"pompidou", "active": True, "sections":{"expos": True, "activities": True}},
]

def collect():
    os.makedirs(DATA_DIR, exist_ok=True)
    log.info("=== Collector start ===")
    all_items=[]

    for feed in FEEDS:
        iid = feed["id"]
        if not feed.get("active", True):
            continue
        try:
            log.info("[%s] import module", iid)
            mod = import_module(f"scrapers.institutions.{iid}")
        except Exception as e:
            log.error("[%s] import failed: %s", iid, e, exc_info=True)
            continue
        try:
            items = mod.collect(feed.get("sections", {}))
            log.info("[%s] total -> %d (written)", iid, len(items))
            all_items.extend(items)
        except Exception as e:
            log.error("[%s] collect failed: %s", iid, e, exc_info=True)

    ded = dedup(all_items)
    log.info("Collected items (dedup): %d", len(ded))
    if not ded:
        log.warning("No items collected. Keeping previous catalog.jsonl (if any).")
        return

    # mark timestamps/status
    now = now_iso()
    for it in ded:
        it.setdefault("first_seen", now)
        it["last_seen"] = now
        it.setdefault("status", "activo")
        it.setdefault("timezone", "Europe/Madrid")
        it.setdefault("parse_confidence", 0.7)

    write_jsonl(CATALOG, ded)
   
