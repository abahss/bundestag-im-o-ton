#!/usr/bin/env python
"""
Pre-warm summaries_cache.json for all active TOPs.
Skips TOPs that are already fully cached. Safe to re-run.

Usage:
    cd practice-vs-preach
    uv run python bin/prewarm_cache.py
"""

import json
import logging
from pathlib import Path

from practicepreach.rag import Rag
from practicepreach.search_index import write_search_index
from practicepreach.updater import (
    prewarm_drucksache_summaries,
    prewarm_haushaltswoche_overview,
    prewarm_summaries,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

TOPS_JSON = Path("data/tops.json")


def main():
    logger.info("Initializing RAG (downloads chroma from GCS)...")
    rag = Rag()

    tops = json.loads(TOPS_JSON.read_text())

    col = rag.vector_store._collection
    result = col.get(where={"type": {"$eq": "speech"}}, include=["metadatas"])
    active_keys = {m["top_key"] for m in result["metadatas"] if m.get("top_key")}
    logger.info(f"{len(active_keys)} active TOP keys found")

    # Drucksachen-Zusammenfassungen first: the general summary of a document-backed TOP
    # takes its Drucksachen-Zusammenfassung as "do not repeat" context (same order as
    # the full run_update() pipeline).
    drs_stats = prewarm_drucksache_summaries(tops, active_keys)
    stats = prewarm_summaries(rag, tops, active_keys)
    hw_stats = prewarm_haushaltswoche_overview(rag, tops)

    # Rebuild the client-side search index from the freshly warmed caches (same
    # step run_update() does after prewarming).
    indexed = write_search_index(tops=tops)

    logger.info(
        f"Done. drucksachen={drs_stats} summaries={stats} haushaltswoche={hw_stats} "
        f"search_indexed={indexed}"
    )
    logger.info("Upload caches to GCS:")
    logger.info("  gcloud storage cp data/summaries_cache.json gs://batch-2170-political-reality-check/data/summaries_cache.json")
    logger.info("  gcloud storage cp data/drucksache_summaries.json gs://batch-2170-political-reality-check/data/drucksache_summaries.json")
    logger.info("  gcloud storage cp data/search_index.json gs://batch-2170-political-reality-check/data/search_index.json")


if __name__ == "__main__":
    main()
