"""
Client for the public abgeordnetenwatch.de API v2 (CC0 1.0, no auth required).
Used to fetch namentliche Abstimmungen (roll-call votes) for the Bundestag —
these aren't reliably extractable from the Bundestag plenary-protocol XML itself
(free-text announcement sentences, hundreds of per-MP name lines), but
abgeordnetenwatch.de already provides them fully structured.
"""

import logging
import re
from collections import defaultdict

import requests

from practicepreach.constants import PARTY_NAME_MAP

logger = logging.getLogger(__name__)

BASE_URL = "https://www.abgeordnetenwatch.de/api/v2"
CURRENT_LEGISLATURE_ID = 161  # "Bundestag 2025 - 2029" (21. Wahlperiode)

# Matches Drucksachen-PDF links as embedded in a poll's field_intro, e.g.
# https://dserver.bundestag.de/btd/21/070/2107006.pdf -> wp=21, num=07006
_DRUCKSACHE_RE = re.compile(r'dserver\.bundestag\.de/btd/(?P<wp>\d+)/\d+/(?P=wp)(?P<num>\d+)\.pdf')

_VOTE_KEY_MAP = {"yes": "ja", "no": "nein", "abstain": "enthalten", "no_show": "nicht_abgestimmt"}


def extract_drucksachen_from_intro(field_intro_html: str) -> list[str]:
    """Extract Drucksachen-Nummern (e.g. '21/7006') referenced as PDF links in a poll's intro text."""
    return [
        f"{m.group('wp')}/{int(m.group('num'))}"
        for m in _DRUCKSACHE_RE.finditer(field_intro_html or "")
    ]


def fetch_polls(legislature_id: int = CURRENT_LEGISLATURE_ID, since_date: str = None) -> list[dict]:
    """Fetch all polls (Abstimmungen) for a legislature, optionally since a given date (YYYY-MM-DD)."""
    params = {
        "field_legislature": legislature_id,
        "sort_by": "field_poll_date",
        "sort_direction": "asc",
        "range_end": 1000,
    }
    if since_date:
        params["field_poll_date[gte]"] = since_date

    response = requests.get(f"{BASE_URL}/polls", params=params, timeout=30)
    response.raise_for_status()
    polls = response.json().get("data", [])
    logger.info(f"Fetched {len(polls)} polls since {since_date or 'start of legislature'}")
    return polls


def fetch_poll_votes(poll_id: int) -> dict:
    """Fetch aggregated Ja/Nein/Enthaltung/nicht-abgestimmt counts + per-party breakdown for one poll."""
    response = requests.get(
        f"{BASE_URL}/polls/{poll_id}", params={"related_data": "votes"}, timeout=30
    )
    response.raise_for_status()
    votes = response.json()["data"]["related_data"]["votes"]

    totals = {"ja": 0, "nein": 0, "enthalten": 0, "nicht_abgestimmt": 0}
    parteien = defaultdict(lambda: {"ja": 0, "nein": 0, "enthalten": 0, "nicht_abgestimmt": 0})

    for v in votes:
        key = _VOTE_KEY_MAP.get(v.get("vote"))
        if key is None:
            continue
        totals[key] += 1
        raw_party = (v.get("fraction") or {}).get("label", "")
        party_name = raw_party.split(" (")[0].strip()
        party_code = PARTY_NAME_MAP.get(party_name, party_name)
        parteien[party_code][key] += 1

    return {**totals, "parteien": dict(parteien)}
