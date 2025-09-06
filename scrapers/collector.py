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
            ex = mod.fetch_expos(urls["expos_list"])
            print(f"[{iid}] expos: {len(ex)} items")
            inst_items += ex

        if inst["sections"].get("activities") and hasattr(mod, "fetch_activities") and urls.get("activities_list"):
            print(f"[{iid}] activities scraping...")
            ac = mod.fetch_activities(urls["activities_list"])
            print(f"[{iid}] activities: {len(ac)} items")
            inst_items += ac

        write_json(os.path.join(OUT_DIR, f"{iid}.json"), inst_items)
        print(f"[{iid}] total: {len(inst_items)} items")
        all_items.extend(inst_items)

    # DEDUPE por id (último gana)
    uniq = {}
    for it in all_items:
        uniq[it["id"]] = it
    deduped = list(uniq.values())

    with open(CATALOG, "w", encoding="utf-8") as f:
        for it in deduped:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"[OK] catalog -> {len(deduped)} items (dedup from {len(all_items)})")
