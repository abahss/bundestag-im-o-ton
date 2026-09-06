"""TRIAL / investigation tool for Phase-1 Drucksachen-Zuordnung: re-parses the XMLs in
data/xml_updates/ fresh and cross-checks each Drucksachennummer against DIP metadata.
Use this to hunt down NEW parser bugs against freshly-downloaded sessions.

Comparison logic lives in practicepreach/drucksache_verify.py (shared with the actual
Schritt-4 pre-deploy step, bin/verify_tops_drucksachen.py, which runs over the live
tops.json instead of re-parsing XMLs).

Run on a subset first:  uv run python bin/verify_drucksache_matches.py --limit 60
Also inspect the non-canonical numbers (Beschlussempfehlung, ...):  ... --all-numbers
Full JSON report -> drucksache_match_report.json (cwd; gitignored / throwaway).
"""
import argparse
import json
import sys
import time
from pathlib import Path

from practicepreach.drucksache_verify import fetch_dip, verdict
from practicepreach.tools import build_tops_lookup

XML_DIR = Path("data/xml_updates")


def collect(all_numbers: bool) -> list[dict]:
    """One row per subtopic, for its canonical (first) Drucksache — that is the only
    document the summary feature would ever render. With --all-numbers, emit every
    number in the bucket (Beschlussempfehlung, §96-Bericht, ...) for inspection."""
    tops: dict = {}
    for f in sorted(XML_DIR.glob("*.xml")):
        tops.update(build_tops_lookup(str(f)))

    rows = []
    for top_key, top in tops.items():
        buckets = [{"key": s["key"], "title": s.get("title", ""), "nas": s.get("nas", ""),
                    "nums": s.get("drucksachen") or ([s["drucksache"]] if s.get("drucksache") else [])}
                   for s in top.get("subtopics", [])]
        if not buckets and top.get("drucksache"):
            buckets = [{"key": "-", "title": top.get("title", ""), "nas": top.get("subtitle", ""),
                        "nums": top.get("drucksachen") or [top["drucksache"]]}]
        for b in buckets:
            nums = b["nums"] if all_numbers else b["nums"][:1]
            for nr in nums:
                rows.append({"top_key": top_key, "sub": b["key"],
                             "sub_title": b["title"], "nas": b["nas"], "nr": nr})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40, help="max distinct Drucksachennummern to query")
    ap.add_argument("--all-numbers", action="store_true",
                    help="also check the non-canonical numbers in each bucket (Beschlussempfehlung, ...)")
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--out", default="drucksache_match_report.json")
    args = ap.parse_args()

    rows = collect(args.all_numbers)
    seen: set[str] = set()
    picked = []
    for row in rows:
        if row["nr"] in seen:
            continue
        seen.add(row["nr"])
        picked.append(row)
        if len(picked) >= args.limit:
            break

    print(f"{len(rows)} (sub,nr) pairs total; querying {len(picked)} distinct numbers\n")
    report = []
    counts = {"OK": 0, "MISMATCH": 0, "DIP_EMPTY": 0, "ERROR": 0}
    for i, row in enumerate(picked, 1):
        try:
            dip = fetch_dip(row["nr"])
        except Exception as exc:
            counts["ERROR"] += 1
            print(f"{i:>3}. {row['nr']:<9} ERROR {exc}")
            report.append({**row, "verdict": "ERROR", "error": str(exc)})
            continue
        if not dip:
            counts["DIP_EMPTY"] += 1
            print(f"{i:>3}. {row['nr']:<9} DIP_EMPTY  ({row['top_key']} {row['sub']})")
            report.append({**row, "verdict": "DIP_EMPTY"})
        else:
            v, detail = verdict(row["sub_title"], row["nas"], dip)
            counts[v] += 1
            flag = "  " if v == "OK" else ">>"
            print(f"{flag}{i:>3}. {row['nr']:<9} {v:<9} score={detail['score']} "
                  f"{';'.join(detail['reasons'])}")
            if v == "MISMATCH":
                print(f"       sub : {row['sub_title'][:80]}  [{row['top_key']} {row['sub']}]")
                print(f"       dip : {detail['dip_titel'][:80]}  ({detail['dip_typ']})")
            report.append({**row, "verdict": v, **detail})
        time.sleep(args.sleep)

    print(f"\n{counts}")
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"full report -> {args.out}")


if __name__ == "__main__":
    sys.exit(main())
