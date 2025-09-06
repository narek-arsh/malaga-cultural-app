# scrapers/collector.py
import os, sys, json, yaml, logging
from importlib import import_module

OUT_DIR = "data/sources"
CATALOG = "data/catalog.jsonl"
LOG_PATH = "data/run.log"
CFG_PATH = "config/feeds.yaml"

def setup_logger():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logger = logging.getLogger("collector")
    logger.setLevel(logging.INFO)
    logger.handlers[:] = []
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    fh = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(sh); logger.addHandler(fh)
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
    if not os.path.exists(CFG_PATH):
        logger.error(f"Config not found: {CFG_PATH}")
        return

    cfg = load_yaml(CFG_PATH)
    all_items = []

    for inst in cfg.get("institutions", []):
        if not inst.get("active", True):
            logger.info(f"[{inst['id']}] SKIP (inactive)")
            continue

        iid = inst["id"]
        urls = inst.get("urls", {})
        logger.info(f"[{iid}] import module")
        try:
            mod = import_module(f"scrapers.institutions.{iid}")
        except Exception as e:
            logger.exception(f"[{iid}] import failed: {e}")
            continue

        inst_items = []

        if inst["sections"].get("expos") and hasattr(mod, "fetch_expos") and urls.get("expos_list"):
            try:
                logger.info(f"[{iid}] expos scraping: {urls['expos_list']}")
                ex = mod.fetch_expos(urls["expos_list"])
            except Exception as e:
                logger.exception(f"[{iid}] expos error: {e}")
                ex = []
            logger.info(f"[{iid}] expos -> {len(ex)}")
            inst_items += ex

        if inst["sections"].get("activities") and hasattr(mod, "fetch_activities") and urls.get("activities_list"):
            try:
                logger.info(f"[{iid}] activities scraping: {urls['activities_list']}")
                ac = mod.fetch_activities(urls["activities_list"])
            except Exception as e:
                logger.exception(f"[{iid}] activities error: {e}")
                ac = []
            logger.info(f"[{iid}] activities -> {len(ac)}")
            inst_items += ac

        write_json(os.path.join(OUT_DIR, f"{iid}.json"), inst_items)
        logger.info(f"[{iid}] total -> {len(inst_items)} (written)")

        all_items.extend(inst_items)

    # Dedupe por id
    uniq = {it["id"]: it for it in all_items if "id" in it}
    deduped = list(uniq.values())
    logger.info(f"Collected items (dedup): {len(deduped)}")

    # Escritura segura del catálogo
    tmp = CATALOG + ".tmp"
    if deduped:
        with open(tmp, "w", encoding="utf-8") as f:
            for it in deduped:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        # backup del anterior si existe
        if os.path.exists(CATALOG):
            try:
                os.replace(CATALOG, CATALOG + ".last_ok")
            except Exception:
                pass
        os.replace(tmp, CATALOG)
        logger.info(f"[OK] catalog -> {len(deduped)} items")
    else:
        if os.path.exists(tmp):
            os.remove(tmp)
        logger.warning("No items collected. Keeping previous catalog.jsonl (if any).")

    logger.info("=== Collector end ===")

if __name__ == "__main__":
    # Permite ejecutar local: python -m scrapers.collector
    collect()
