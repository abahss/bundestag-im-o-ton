#!/usr/bin/env python
"""
Re-run attach_citation_ids over every cached quote, without calling the LLM.

Useful after a fix to the citation-matching logic in rag.py (case-sensitivity,
trailing punctuation, "[...]"-elided quotes, ...): re-derives the [IDxxx] tags
for quotes already sitting in summaries_cache.json, using the current chunks
in ChromaDB. Only uploads summaries_cache.json back to GCS (not the vector
store, which this script never touches) -- much cheaper than a full
--purge-summaries regeneration.

Usage:
    cd backend
    direnv exec . uv run python bin/repair_citation_ids.py            # dry run, just reports
    direnv exec . uv run python bin/repair_citation_ids.py --write    # writes + uploads
"""

import argparse
import json
import logging
import subprocess
from collections import defaultdict
from pathlib import Path

import chromadb

from practicepreach.fast import _split_summary, _combine_summary
from practicepreach.quote_matching import attach_citation_ids
from practicepreach.params import GCS_CHROMA_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

CHROMA_LOCAL = "/tmp/chroma_store_gemini"
CACHE = Path("data/summaries_cache.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write changes and upload to GCS")
    args = parser.parse_args()

    client = chromadb.PersistentClient(path=CHROMA_LOCAL)
    col = client.get_collection("political_collection")
    results = col.get(where={"type": {"$eq": "speech"}}, include=["documents", "metadatas"])

    chunks_by_key = defaultdict(list)
    seen = defaultdict(set)
    for doc, meta in zip(results["documents"], results["metadatas"]):
        key = (meta.get("top_key"), meta.get("party"))
        if doc not in seen[key]:
            seen[key].add(doc)
            chunks_by_key[key].append((doc, meta.get("id", "unknown")))

    cache = json.loads(CACHE.read_text())
    changed = 0
    newly_fixed = 0
    for top_key, parties in cache.items():
        for party, entry in parties.items():
            if party == "general" or not isinstance(entry, dict):
                continue

            has_summary_format = "summary" in entry
            raw_text = entry["summary"] if has_summary_format else _combine_summary(
                entry.get("kernposition", ""), entry.get("quotes_text", "")
            )
            if not raw_text.strip():
                continue

            chunks = chunks_by_key.get((top_key, party), [])
            new_text = attach_citation_ids(raw_text, chunks)
            if new_text == raw_text:
                continue

            changed += 1
            before_missing = raw_text.count('*"') - raw_text.count("[ID")
            after_missing = new_text.count('*"') - new_text.count("[ID")
            if after_missing < before_missing:
                newly_fixed += before_missing - after_missing

            if has_summary_format:
                entry["summary"] = new_text
            else:
                kp, qt = _split_summary(new_text)
                entry["kernposition"] = kp
                entry["quotes_text"] = qt

    logger.info(f"{changed} TOP+Partei-Einträge geändert, ~{newly_fixed} Zitate neu mit Quell-ID versehen")

    if not args.write:
        logger.info("Dry run -- keine Datei geschrieben. Mit --write erneut aufrufen zum Speichern.")
        return

    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
    logger.info(f"{CACHE} aktualisiert")

    gcs_base = GCS_CHROMA_PATH.rsplit("/", 1)[0]
    r = subprocess.run(
        ["gsutil", "cp", str(CACHE), f"{gcs_base}/summaries_cache.json"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"GCS upload failed: {r.stderr}")
    logger.info(f"Hochgeladen nach {gcs_base}/summaries_cache.json")


if __name__ == "__main__":
    main()
