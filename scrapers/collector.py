# scrapers/collector.py
import yaml, json, os, logging, sys
from datetime import datetime
from importlib import import_module

OUT_DIR = "data/sources"
CATALOG = "data/catalog.jsonl"
LOG_PATH = "data/run.log"

def setup_logger():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logger = logging.getLogger("collector")
    logger.setLevel(logging.INFO)
    logger.handlers[:] = []
    # Consola
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    # Archivo
    fh = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    ch.setFormatter(fmt); fh.setFormatter(fmt)
    logger.addHandler(ch); logger.addHandler(fh)
    return logger

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def collect():
    logger = setup_logger()
    logger.info("=== Collector start ===")

    cfg = load_yaml("config/feeds.yaml")
    all_items = []
    for inst in cfg.get("institutions", []):
        if not inst.get("active", True):
            logger.info(f"[{inst['id']}] SKIP (inactive)")
            continue

        iid = inst["id"]
        urls = inst.get("urls", {})
        logger.info(f"[{iid}] importing module...")
        try:
            mod = import_module(f"scrapers.institutions.{iid}")
        except Exception as e:
            logger.exception(f"[{iid}] import failed: {e}")
            continue

        inst_items = []
        # EXPOs
        if inst["sections"].get("expos") and hasattr(mod, "fetch_expos") and urls.get("expos_list"):
            logger.info(f"[{iid}] expos scraping: {urls['expos_list']}")
            try:
                ex = mod.fetch_expos(urls["expos_list"])
            except Exception as e:
                logger.exception(f"[{iid}] expos error: {e}")
                ex = []
            logger.info(f"[{iid}] expos -> {len(ex)} items")
            inst_items += ex

        # ACTIVIDADES
        if inst["sections"].get("activities") and hasattr(mod, "fetch_activities") and urls.get("activities_list"):
            logger.info(f"[{iid}] activities scraping: {urls['activities_list']}")
            try:
                ac = mod.fetch_activities(urls["activities_list"])
            except Exception as e:
                logger.exception(f"[{iid}] activities error: {e}")
                ac = []
            logger.info(f"[{iid}] activities -> {len(ac)} items")
            inst_items += ac

        write_json(os.path.join(OUT_DIR, f"{iid}.json"), inst_items)
        logger.info(f"[{iid}] total -> {len(inst_items)} items (written to {OUT_DIR}/{iid}.json)")
        all_items.extend(inst_items)

    # DEDUPE por id (último gana)
    uniq = {}
    for it in all_items:
        uniq[it["id"]] = it
    deduped = list(uniq.values())

    os.makedirs(os.path.dirname(CATALOG), exist_ok=True)
    with open(CATALOG, "w", encoding="utf-8") as f:
        for it in deduped:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    logger.info(f"[OK] catalog -> {len(deduped)} items (dedup from {len(all_items)})")
    logger.info("=== Collector end ===")

if __name__ == "__main__":
    collect()
