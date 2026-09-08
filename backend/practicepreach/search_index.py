"""Build data/search_index.json — one lower-cased searchable text blob per TOP.

The website search runs client-side. Today it only sees the TOP title / subtitle
/ Gemini topic / subtopic titles (all in tops.json, loaded on the homepage). This
index adds the bodies that otherwise only load on the detail page: the general
summary, every party Kernposition + its quotes, and the Drucksachen-
Zusammenfassungen (title + im_kern + Punkte). The frontend fetches it after
mount and substring-matches against the blob.
"""
import json
import re
from pathlib import Path

from practicepreach.constants import PARTIES_LIST

SEARCH_INDEX_JSON = Path("data/search_index.json")
TOPS_JSON = Path("data/tops.json")
SUMMARIES_CACHE = Path("data/summaries_cache.json")
DRUCKSACHE_SUMMARIES_CACHE = Path("data/drucksache_summaries.json")

_WS = re.compile(r"\s+")
_ID_MARKER = re.compile(r"\[ID[^\]]*\]")  # speech-ID tags in quotes_text
_DROP = re.compile(r"[*_`\[\]()„“”\"»«]")


def _norm(*parts: object) -> str:
    text = " ".join(str(p) for p in parts if p)
    text = _ID_MARKER.sub(" ", text)
    text = _DROP.sub(" ", text)
    return _WS.sub(" ", text).strip().lower()


def _drucksache_numbers(top: dict) -> list[str]:
    nrs: list[str] = []
    for key in ("drucksache", "drucksachen"):
        val = top.get(key)
        if isinstance(val, str) and val:
            nrs.append(val)
        elif isinstance(val, list):
            nrs.extend(n for n in val if n)
    for sub in top.get("subtopics", []):
        nrs.extend(_drucksache_numbers(sub))
    return list(dict.fromkeys(nrs))


def _blob(top_key: str, top: dict, summaries: dict, drucksachen: dict) -> str:
    parts: list[object] = [top.get("title", ""), top.get("subtitle", ""), top.get("topic", "")]

    for sub in top.get("subtopics", []):
        parts += [sub.get("title", ""), sub.get("nas", "")]

    sc = summaries.get(top_key, {})
    general = sc.get("general")
    if isinstance(general, dict):
        parts.append(general.get("summary", ""))
    for party in PARTIES_LIST:
        pv = sc.get(party)
        if isinstance(pv, dict):
            parts += [pv.get("kernposition", ""), pv.get("quotes_text", "")]

    for nr in _drucksache_numbers(top):
        d = drucksachen.get(nr)
        if not isinstance(d, dict) or d.get("error") or not d.get("im_kern"):
            continue
        parts += [d.get("titel", ""), d.get("im_kern", "")]
        parts += list(d.get("punkte", []))

    return _norm(*parts)


def build_search_index(tops: dict, summaries: dict, drucksachen: dict) -> dict[str, str]:
    """{top_key: lower-cased searchable blob} for every TOP in tops.json."""
    return {top_key: _blob(top_key, top, summaries, drucksachen) for top_key, top in tops.items()}


def write_search_index(
    tops: dict | None = None,
    summaries: dict | None = None,
    drucksachen: dict | None = None,
) -> int:
    """Build the index from the given data (or read the on-disk caches) and write
    data/search_index.json. Returns the number of TOPs indexed."""
    if tops is None:
        tops = json.loads(TOPS_JSON.read_text()) if TOPS_JSON.exists() else {}
    if summaries is None:
        summaries = json.loads(SUMMARIES_CACHE.read_text()) if SUMMARIES_CACHE.exists() else {}
    if drucksachen is None:
        drucksachen = (
            json.loads(DRUCKSACHE_SUMMARIES_CACHE.read_text())
            if DRUCKSACHE_SUMMARIES_CACHE.exists()
            else {}
        )
    index = build_search_index(tops, summaries, drucksachen)
    SEARCH_INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_INDEX_JSON.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return len(index)


if __name__ == "__main__":
    n = write_search_index()
    size_mb = SEARCH_INDEX_JSON.stat().st_size / 1e6
    print(f"Wrote {SEARCH_INDEX_JSON} — {n} TOPs, {size_mb:.2f} MB")
