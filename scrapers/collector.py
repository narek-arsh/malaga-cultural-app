
import yaml, json, os
from datetime import datetime
from importlib import import_module

OUT_DIR = "data/sources"
CATALOG = "data/catalog.jsonl"

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def append_jsonl(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

def collect():
    cfg = load_yaml("config/feeds.yaml")
    all_items = []
    for inst in cfg.get("institutions", []):
        if not inst.get("active", True):
            continue
        iid = inst["id"]
        urls = inst.get("urls", {})
        mod = import_module(f"scrapers.institutions.{iid}")
        inst_items = []
        if inst["sections"].get("expos") and hasattr(mod, "fetch_expos") and urls.get("expos_list"):
            print(f"[{iid}] expos scraping...")
            inst_items += mod.fetch_expos(urls["expos_list"])
        if inst["sections"].get("activities") and hasattr(mod, "fetch_activities") and urls.get("activities_list"):
            print(f"[{iid}] activities scraping...")
            inst_items += mod.fetch_activities(urls["activities_list"])
        write_json(os.path.join(OUT_DIR, f"{iid}.json"), inst_items)
        all_items.extend(inst_items)
    # overwrite catalog
    with open(CATALOG, "w", encoding="utf-8") as f:
        for it in all_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"[OK] catalog -> {len(all_items)} items")

if __name__ == "__main__":
    collect()
