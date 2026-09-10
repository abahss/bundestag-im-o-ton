"""Phase-1 Schritt 4: annotate every Drucksache in the live tops.json with a
`drucksache_verified` flag, ready to run by hand right before a deploy.

Unlike bin/verify_drucksache_matches.py (which re-parses XMLs to hunt down parser
bugs), this runs over `data/tops.json` as it will actually be shipped and writes the
result back into it:
  1. data/drucksache_overrides.json is checked first — a manually-curated
     {"top_key|sub_key": "correct nr"} map for cases no automated check can resolve
     (e.g. two unrelated Anträge bundled with no structural marker at all, see
     75_Tagesordnungspunkt 4 / 2026-09-04). An override always wins: it replaces the
     canonical `drucksache`/`drucksache_url` and is trusted without a DIP call.
  2. Otherwise the DIP cross-check from practicepreach.drucksache_verify runs, cached
     in data/dip_drucksache_cache.json by Drucksachennummer + a hash of the compared
     text (title/nas) so re-runs only pay for genuinely new or changed entries.

`drucksache_verified: false` (no override, DIP disagrees) means: no automatic
Drucksachen-Zusammenfassung for that TOP/Subtopic, PDF-link only.

The check itself lives in practicepreach.drucksache_verify.verify_tops so the update
pipeline (bin/update_speeches.py) can run it too; this script is the by-hand CLI
wrapper around it.

Usage:
    uv run python bin/verify_tops_drucksachen.py                  # check + write
    uv run python bin/verify_tops_drucksachen.py --dry-run         # check only, print summary
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from practicepreach.drucksache_verify import _buckets, verify_tops

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

TOPS_JSON = Path("data/tops.json")
OVERRIDES_JSON = Path("data/drucksache_overrides.json")
CACHE_JSON = Path("data/dip_drucksache_cache.json")


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tops", type=Path, default=TOPS_JSON)
    ap.add_argument("--overrides", type=Path, default=OVERRIDES_JSON)
    ap.add_argument("--cache", type=Path, default=CACHE_JSON)
    ap.add_argument("--sleep", type=float, default=0.12)
    ap.add_argument("--dry-run", action="store_true", help="check only, do not write tops.json/cache")
    args = ap.parse_args()

    tops = _load_json(args.tops, {})
    overrides = _load_json(args.overrides, {})
    cache = _load_json(args.cache, {})
    if not tops:
        print(f"No TOPs found in {args.tops} — nothing to do.")
        return

    n_buckets = sum(len(_buckets(k, t)) for k, t in tops.items())
    print(f"{n_buckets} Drucksache-Buckets in {args.tops}\n")

    counts = verify_tops(tops, overrides, cache, sleep=args.sleep)
    print(f"{counts}\n")

    flagged = [
        (k, b["sub_key"], b["container"]["drucksache"])
        for k, t in tops.items()
        for b in _buckets(k, t)
        if b["container"].get("drucksache_verified") is False
    ]
    if flagged:
        print(f"{len(flagged)} unverified — no automatic summary, PDF-link only:")
        for top_key, sub_key, nr in flagged:
            reasons = cache.get(nr, {}).get("reasons") or cache.get(nr, {}).get("verdict", "")
            print(f"  {top_key:<40} {sub_key:<6} {nr:<9} {reasons}")
    else:
        print("Nothing unverified.")

    if args.dry_run:
        print("\n--dry-run: tops.json/cache not written.")
        return

    args.tops.write_text(json.dumps(tops, ensure_ascii=False, indent=2), encoding="utf-8")
    args.cache.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote drucksache_verified into {args.tops}, cache updated at {args.cache}.")


if __name__ == "__main__":
    sys.exit(main())
