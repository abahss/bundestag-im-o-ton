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

Usage:
    uv run python bin/verify_tops_drucksachen.py                  # check + write
    uv run python bin/verify_tops_drucksachen.py --dry-run         # check only, print summary
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from practicepreach.drucksache_verify import fetch_dip, verdict

TOPS_JSON = Path("data/tops.json")
OVERRIDES_JSON = Path("data/drucksache_overrides.json")
CACHE_JSON = Path("data/dip_drucksache_cache.json")


def _ref_hash(sub_title: str, nas: str) -> str:
    return hashlib.sha1(f"{sub_title}|{nas}".encode("utf-8")).hexdigest()[:12]


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _buckets(top_key: str, top: dict) -> list[dict]:
    """One bucket per verifiable canonical Drucksache: top-level ('-') plus each subtopic."""
    buckets = []
    if top.get("drucksache"):
        buckets.append({"sub_key": "-", "title": top.get("title", ""), "nas": top.get("subtitle", ""),
                         "container": top})
    for sub in top.get("subtopics", []):
        if sub.get("drucksache"):
            buckets.append({"sub_key": sub["key"], "title": sub.get("title", ""), "nas": sub.get("nas", ""),
                             "container": sub})
    for b in buckets:
        b["top_key"] = top_key
        b["override_key"] = f"{top_key}|{b['sub_key']}"
    return buckets


def _drucksache_pdf_url(nr: str) -> str:
    try:
        wp, num = nr.split("/")
        return f"https://dserver.bundestag.de/btd/{wp}/{num.zfill(5)[:3]}/{wp}{num.zfill(5)}.pdf"
    except Exception:
        return ""


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

    buckets = [b for top_key, top in tops.items() for b in _buckets(top_key, top)]
    print(f"{len(buckets)} Drucksache-Buckets in {args.tops}\n")

    counts = {"override": 0, "cache_hit": 0, "OK": 0, "MISMATCH": 0, "DIP_EMPTY": 0, "ERROR": 0}
    flagged = []
    for i, b in enumerate(buckets, 1):
        container = b["container"]
        nr = container["drucksache"]
        override_nr = overrides.get(b["override_key"])

        if override_nr:
            counts["override"] += 1
            if override_nr != nr:
                container["drucksache"] = override_nr
                container["drucksache_url"] = _drucksache_pdf_url(override_nr)
            container["drucksache_verified"] = True
            continue

        h = _ref_hash(b["title"], b["nas"])
        cached = cache.get(nr)
        if cached and cached.get("ref_hash") == h:
            counts["cache_hit"] += 1
            container["drucksache_verified"] = cached["verdict"] == "OK"
            continue

        try:
            dip = fetch_dip(nr)
        except Exception as exc:
            counts["ERROR"] += 1
            print(f"{i:>4}. {nr:<9} ERROR {exc}")
            container["drucksache_verified"] = False
            flagged.append({**b, "verdict": "ERROR", "error": str(exc)})
            time.sleep(args.sleep)
            continue

        if not dip:
            counts["DIP_EMPTY"] += 1
            container["drucksache_verified"] = False
            cache[nr] = {"verdict": "DIP_EMPTY", "ref_hash": h}
            flagged.append({**b, "verdict": "DIP_EMPTY"})
            time.sleep(args.sleep)
            continue

        v, detail = verdict(b["title"], b["nas"], dip)
        counts[v] += 1
        container["drucksache_verified"] = v == "OK"
        cache[nr] = {"verdict": v, "ref_hash": h, **detail}
        if v == "MISMATCH":
            flagged.append({**b, "verdict": v, **detail})
        time.sleep(args.sleep)

    print(f"{counts}\n")
    if flagged:
        print(f"{len(flagged)} unverified — no automatic summary, PDF-link only:")
        for f in flagged:
            print(f"  {f['top_key']:<40} {f['sub_key']:<6} {f['container']['drucksache']:<9} "
                  f"{f['verdict']}  {f.get('reasons', f.get('error', ''))}")
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
