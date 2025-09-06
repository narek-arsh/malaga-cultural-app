# ... deja el resto igual (incluyendo logs si ya los añadiste)

def collect():
    logger = setup_logger()
    logger.info("=== Collector start ===")

    # Carga de config con mensaje claro si falta
    cfg_path = "config/feeds.yaml"
    if not os.path.exists(cfg_path):
        logger.error(f"Config not found: {cfg_path}")
        return

    cfg = load_yaml(cfg_path)
    all_items = []
    # (tu bucle por instituciones aquí, igual que lo tenías)
    # ...
    # al final:
    uniq = {it["id"]: it for it in all_items}
    deduped = list(uniq.values())
    logger.info(f"Collected items (dedup): {len(deduped)}")

    # Escritura segura: si no hay items, NO sobreescribas el catálogo
    tmp_path = CATALOG + ".tmp"
    if deduped:
        with open(tmp_path, "w", encoding="utf-8") as f:
            for it in deduped:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        # backup del último bueno
        if os.path.exists(CATALOG):
            try:
                os.replace(CATALOG, CATALOG + ".last_ok")
            except Exception:
                pass
        os.replace(tmp_path, CATALOG)
        logger.info(f"[OK] catalog -> {len(deduped)} items")
    else:
        logger.warning("No items collected. Keeping previous catalog.jsonl (if any).")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    logger.info("=== Collector end ===")
