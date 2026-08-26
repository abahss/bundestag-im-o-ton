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
from practicepreach.updater import prewarm_summaries

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

    stats = prewarm_summaries(rag, tops, active_keys)

    logger.info(f"Done. {stats}")
    logger.info("Upload cache to GCS:")
    logger.info("  gcloud storage cp data/summaries_cache.json gs://batch-2170-political-reality-check/data/summaries_cache.json")


if __name__ == "__main__":
    main()
