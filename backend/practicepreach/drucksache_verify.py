"""Shared DIP cross-check logic for Drucksachen-Zuordnung (Phase 1, Schritt 2/4).

Compares a TOP/Subtopic's parsed Drucksachennummer against DIP metadata:
  - DIP `titel`         vs the subtopic title      (difflib ratio)
  - DIP `drucksachetyp` vs what the NaS announces  (Antrag / Gesetzentwurf / ...)
  - DIP `urheber`       vs the NaS urheber          (Bundesregierung / Bundesrat / Fraktion X)

Used by both `bin/verify_drucksache_matches.py` (throwaway trial/investigation tool,
runs over freshly-parsed XMLs) and `bin/verify_tops_drucksachen.py` (the actual
pre-deploy Schritt-4 step, runs over the live `tops.json`). Keep the heuristics here so
the two never drift apart.
"""
import difflib
import hashlib
import logging
import re
import time

import requests

from practicepreach.params import BUNDESTAG_API_KEY
from practicepreach.tools import _drucksache_pdf_url

logger = logging.getLogger(__name__)

BASE = "https://search.dip.bundestag.de/api/v1"

_FRAKTIONEN = r"(?:CDU/CSU|SPD|BÜNDNIS\s*90/DIE\s*GRÜNEN|DIE\s*LINKE|AfD|FDP|SSW)"


def _norm_title(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[–—-]", " ", s)
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _nas_core(nas: str) -> str:
    """Drop the procedural prefix so the fallback title comparison sees the actual subject.

    "c) Beratung des Antrags der Abgeordneten ... und der Fraktion Die Linke <title>"
    "a) Erste Beratung des von der Bundesregierung eingebrachten Entwurfs eines Gesetzes ..."
    """
    n = re.sub(r"^\s*(?:\d+\s+)?[a-z]\)\s*", "", nas)
    n = re.sub(r"^\s*ZP\s*\d+[a-z]?\s*", "", n, flags=re.IGNORECASE)
    # Strip the procedural lead-in up to the sponsor clause. The sponsor list itself may
    # contain commas ("der Abgeordneten Dr. X, Y, weiterer Abgeordneter und der Fraktion
    # Z <title>"), so anchor on "eingebrachten" or a known Fraktion name rather than
    # stopping at the first comma.
    n = re.sub(
        rf"^(?:–\s*)?(?:Erste|Zweite|Dritte|Zweite und dritte)?\s*Beratung\s+"
        rf"(?:des|der)\s+.*?"
        rf"(?:eingebrachten\s+|und\s+der\s+Fraktion(?:en)?\s+(?:der\s+)?{_FRAKTIONEN}"
        rf"(?:\s+und\s+(?:der\s+)?{_FRAKTIONEN})?\s+)",
        "", n, flags=re.IGNORECASE,
    )
    return n.strip()


def _expected_typ(nas: str) -> str | None:
    n = nas.lower()
    # "Beratung der Beschlussempfehlung ... zu dem Antrag ..." — the originating doc is the Antrag
    if re.search(r"zu dem (antrag|gesetzentwurf)", n):
        return "Gesetzentwurf" if "gesetzentwurf" in n.split("zu dem", 1)[1][:20] else "Antrag"
    # "Entwurfs eines Gesetzes" (genitive, e.g. "... eingebrachten Entwurfs eines
    # Gesetzes ...") — must be checked before the "antrag" substring match below, which
    # otherwise false-positives on titles like "antragslosen Kindergeldes".
    if re.search(r"\bentwurfs?\s+eines\b", n) and "gesetz" in n:
        return "Gesetzentwurf"
    if re.search(r"\bantrag(?:s|es)?\b", n):
        return "Antrag"
    if "unterrichtung" in n:
        return "Unterrichtung"
    return None


def _expected_urheber(nas: str) -> str | None:
    n = nas.lower()
    # Only an explicit "von der Bundesregierung/vom Bundesrat eingebracht(en)" announces
    # the Urheber — the bare word "bundesregierung" also turns up inside bill titles
    # ("... Amtsbezüge durch Mitglieder der Bundesregierung ...").
    if re.search(r"von der bundesregierung eingebracht", n):
        return "bundesregierung"
    if re.search(r"vom bundesrat eingebracht|des bundesrates eingebracht", n):
        return "bundesrat"
    m = re.search(
        rf"fraktion(?:en)?\s+(?:der\s+)?({_FRAKTIONEN}(?:\s+und\s+(?:der\s+)?{_FRAKTIONEN})?)",
        nas, re.IGNORECASE,
    )
    if m:
        return _norm_urheber(m.group(1))
    return None


def _norm_urheber(s: str) -> str:
    s = s.lower()
    s = s.replace("fraktion", "").replace("bündnis 90/", "").replace("bündnis 90", "")
    s = re.sub(r"[^\w\s/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fetch_dip(nr: str) -> dict | None:
    url = f"{BASE}/drucksache?f.dokumentnummer={nr}&apikey={BUNDESTAG_API_KEY}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    docs = r.json().get("documents", [])
    # DIP can return several rows for one number (versions) — take the first
    return docs[0] if docs else None


def verdict(sub_title: str, nas: str, dip: dict) -> tuple[str, dict]:
    dip_titel = dip.get("titel", "")
    dip_typ = dip.get("drucksachetyp", "")
    dip_urh = [u.get("titel", "") for u in dip.get("urheber", [])]

    ref = sub_title or _nas_core(nas)
    score = difflib.SequenceMatcher(None, _norm_title(ref), _norm_title(dip_titel)).ratio()
    # DIP titles for a bundled entry sometimes prepend the sibling ("a) ... b) ..."); also try
    # the best-matching contiguous window so a real match is not buried by extra text.
    if score < 0.55 and len(dip_titel) > len(ref) * 1.4:
        blocks = difflib.SequenceMatcher(None, _norm_title(ref), _norm_title(dip_titel)) \
            .get_matching_blocks()
        matched = sum(b.size for b in blocks)
        score = max(score, matched / max(len(_norm_title(ref)), 1))
    exp_typ = _expected_typ(nas)
    exp_urh = _expected_urheber(nas)

    urh_norm = " ".join(_norm_urheber(u) for u in dip_urh)
    urh_ok = exp_urh is None or exp_urh in urh_norm or any(
        tok and tok in urh_norm for tok in exp_urh.split("/")
    )
    typ_ok = exp_typ is None or exp_typ.lower() in dip_typ.lower() or (
        exp_typ == "Gesetzentwurf" and "gesetz" in dip_typ.lower()
    )

    reasons = []
    if score < 0.55:
        reasons.append(f"TITLE({score:.2f})")
    if not typ_ok:
        reasons.append(f"TYP(exp {exp_typ}, dip {dip_typ})")
    if not urh_ok:
        reasons.append(f"URHEBER(exp {exp_urh}, dip {dip_urh})")

    v = "OK" if not reasons else "MISMATCH"
    return v, {
        "score": round(score, 2),
        "dip_titel": dip_titel,
        "dip_typ": dip_typ,
        "dip_urheber": dip_urh,
        "expected_typ": exp_typ,
        "expected_urheber": exp_urh,
        "reasons": reasons,
    }


def _ref_hash(sub_title: str, nas: str) -> str:
    return hashlib.sha1(f"{sub_title}|{nas}".encode("utf-8")).hexdigest()[:12]


def _buckets(top_key: str, top: dict) -> list[dict]:
    """One bucket per verifiable canonical Drucksache: top-level ('-') plus each subtopic."""
    buckets = []
    if top.get("drucksache"):
        buckets.append({"sub_key": "-", "title": top.get("title", ""),
                        "nas": top.get("subtitle", ""), "container": top})
    for sub in top.get("subtopics", []):
        if sub.get("drucksache"):
            buckets.append({"sub_key": sub["key"], "title": sub.get("title", ""),
                            "nas": sub.get("nas", ""), "container": sub})
    for b in buckets:
        b["top_key"] = top_key
        b["override_key"] = f"{top_key}|{b['sub_key']}"
    return buckets


def verify_tops(tops: dict, overrides: dict, cache: dict, *, sleep: float = 0.12) -> dict:
    """Annotate every canonical Drucksache in `tops` with `drucksache_verified`.
    Mutates `tops` (the flag, and the number itself when an override replaces it) and
    `cache` (new DIP verdicts) in place. Order of precedence per Drucksache:
    manual override → cached DIP verdict (matched by title/nas hash) → live DIP check.
    Returns a verdict-count dict."""
    buckets = [b for top_key, top in tops.items() for b in _buckets(top_key, top)]
    counts = {"override": 0, "cache_hit": 0, "OK": 0, "MISMATCH": 0, "DIP_EMPTY": 0, "ERROR": 0}

    for b in buckets:
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
            logger.warning(f"verify {nr} ({b['top_key']}): DIP error {exc}")
            container["drucksache_verified"] = False
            time.sleep(sleep)
            continue

        if not dip:
            counts["DIP_EMPTY"] += 1
            container["drucksache_verified"] = False
            cache[nr] = {"verdict": "DIP_EMPTY", "ref_hash": h}
            time.sleep(sleep)
            continue

        v, detail = verdict(b["title"], b["nas"], dip)
        counts[v] += 1
        container["drucksache_verified"] = v == "OK"
        cache[nr] = {"verdict": v, "ref_hash": h, **detail}
        if v == "MISMATCH":
            logger.info(f"verify {nr} ({b['top_key']}): MISMATCH {detail.get('reasons')}")
        time.sleep(sleep)

    return counts
