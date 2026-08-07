#!/usr/bin/env python
"""
One-off: fetch namentliche Abstimmungen (roll-call votes) from abgeordnetenwatch.de
and link them to existing tops.json entries, for a given date range.

Exemplary run for Sessions 88-90 only (the only sessions with verified reference
values so far) — no re-embedding, no Rag()/ChromaDB needed.

Usage:
    uv run python bin/backfill_abstimmungen.py --since 2026-07-08
"""

import argparse
import json
import logging
from pathlib import Path

from practicepreach.updater import TOPS_JSON, ABSTIMMUNGEN_JSON, _update_abstimmungen_json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2026-07-08", help="ISO date (YYYY-MM-DD), inclusive")
    args = parser.parse_args()

    tops = json.loads(TOPS_JSON.read_text())
    summary = _update_abstimmungen_json(tops, since_date=args.since)

    print(f"\nPolls gefunden: {summary['polls_found']}")
    print(f"Verknüpft:      {summary['linked']}")
    print(f"Unmatched:      {len(summary['unmatched'])}")
    for u in summary["unmatched"]:
        print(f"  - {u}")

    print(f"\nGeschrieben nach {ABSTIMMUNGEN_JSON}")


if __name__ == "__main__":
    main()
