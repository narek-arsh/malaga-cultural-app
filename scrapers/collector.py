# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import json
import logging
from importlib import import_module
from typing import Any, Dict, List

import yaml

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_DIR = os.path.abspath(DATA_DIR)
CATALOG = os.path.join(DATA_DIR, "catalog.jsonl")
CATALOG_LAST_OK = os.path.join(DATA_DIR, "catalog.jsonl.last_ok")
CURATED = os.path.join(DATA_DIR, "curated.json")
MANUAL = os.path.join(DATA_DIR, "manual_events.csv")
SOURCES_DIR = os.path.join(DATA_DIR, "sources")
FEEDS = os.path.join(os.path.dirname(__file__), "..", "config", "feeds.yaml")
FEEDS = os.path.abspath(FEEDS)

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SOURCES_DIR, exist_ok=True)

def load_feeds() -> List[Dict[str, Any]]:
    with open(FEEDS, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return doc.get("feeds", [])

def write_jsonl(path: str, items: List[Dict[str, Any]]):
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

def collect():
    ensure_dirs()
    log.info("=== Collector start ===")
    feeds = load_feeds()
    all_items: List[Dict[str, Any]] = []

    for feed in feeds:
        iid = feed.get("id")
        active = feed.get("active", True)
        if not active:
            continue

        log.info("[%s] import module", iid)
        try:
            mod = import_module(f"scrapers.institutions.{iid}")
        except Exception as e:
            log.exception("[%s] import failed: %s", iid, e)
            continue

        try:
            got = mod.collect(feed)
            log.info("[%s] total -> %d (written)", iid, len(got))
            all_items.extend(got)
        except Exception as e:
            log.exception("[%s] collect failed: %s", iid, e)

    # dedupe by source_url
    dedup: Dict[str, Dict[str, Any]] = {}
    for it in all_items:
        k = it.get("source_url") or it.get("id") or json.dumps(it, sort_keys=True)
        dedup[k] = it
    items = list(dedup.values())
    log.info("Collected items (dedup): %d", len(items))

    if items:
        # backup previous ok
        try:
            if os.path.exists(CATALOG):
                with open(CATALOG, "rb") as src, open(CATALOG_LAST_OK, "wb") as dst:
                    dst.write(src.read())
        except Exception:
            pass
        write_jsonl(CATALOG, items)
        log.info("[OK] catalog -> %d items", len(items))
    else:
        log.warning("No items collected. Keeping previous catalog.jsonl (if any).")

    log.info("=== Collector end ===")

if __name__ == "__main__":
    collect()
