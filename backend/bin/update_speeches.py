#!/usr/bin/env python
"""
Update ChromaDB with new Bundestag speeches since a given date.

Usage:
    uv run python bin/update_speeches.py --since 2025-11-28
    uv run python bin/update_speeches.py   # auto-detects last embedded date from ChromaDB
"""

import argparse
import logging

from practicepreach.rag import Rag
from practicepreach.updater import run_update

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Update ChromaDB with new Bundestag speeches.")
    parser.add_argument(
        "--since",
        help="Fetch sessions on or after this date (YYYY-MM-DD). Defaults to last embedded date.",
    )
    parser.add_argument(
        "--prune-weeks",
        type=int,
        default=52,
        help="Remove speeches older than this many weeks (default: 52).",
    )
    args = parser.parse_args()

    logger.info("Initialising RAG (loads embedding model)...")
    rag = Rag()
    result = run_update(rag, since_date=args.since, prune_weeks=args.prune_weeks)
    logger.info(f"Update complete: {result}")


if __name__ == "__main__":
    main()
