"""
Speech update pipeline: fetch new Bundestag plenary speeches, embed into ChromaDB,
prune speeches older than `prune_weeks` weeks, and rebuild tops.json.

Can be called from the CLI (bin/update_speeches.py) or the API (/admin/update).
"""
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from requests.exceptions import ChunkedEncodingError, ConnectionError

from practicepreach.tools import process_bundestag_xml, build_tops_lookup
from practicepreach.params import BUNDESTAG_API_KEY, USE_GCS_CHROMA
from practicepreach.constants import PARTY_NAME_MAP
from practicepreach.abgeordnetenwatch import fetch_polls, fetch_poll_votes, extract_drucksachen_from_intro

logger = logging.getLogger(__name__)

BASE_URL = "https://search.dip.bundestag.de/api/v1"
XML_DIR = Path("data/xml_updates")
TOPS_JSON = Path("data/tops.json")
ABSTIMMUNGEN_JSON = Path("data/abstimmungen.json")


def fetch_session_xml_urls(since_date: str) -> list[tuple[str, str]]:
    """Query Bundestag API for plenary sessions since since_date. Returns (datum, xml_url) pairs."""
    results = []
    end_date = datetime.today().strftime('%Y-%m-%d')
    max_attempts = 3

    while True:
        url = (
            f"{BASE_URL}/plenarprotokoll"
            f"?f.zuordnung=BT"
            f"&f.datum.start={since_date}"
            f"&f.datum.end={end_date}"
            f"&apikey={BUNDESTAG_API_KEY}"
        )
        payload = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                payload = response.json()
                break
            except (ChunkedEncodingError, ConnectionError) as exc:
                logger.warning(f"Attempt {attempt}/{max_attempts} failed: {exc}")
                if attempt < max_attempts:
                    time.sleep(2 * attempt)
            except requests.HTTPError as exc:
                logger.error(f"HTTP {exc.response.status_code}: {exc}")
                break

        if not payload:
            break
        docs = payload.get("documents", [])
        if not docs:
            break

        for doc in docs:
            fundstelle = doc.get("fundstelle", {})
            xml_url = fundstelle.get("xml_url")
            if xml_url:
                results.append((doc.get("datum"), xml_url))

        dates = [doc["datum"] for doc in docs if "datum" in doc]
        new_end = min(dates)
        if new_end >= end_date or new_end < since_date:
            break
        end_date = new_end

    logger.info(f"Found {len(results)} sessions since {since_date}")
    return results


def download_xmls(session_urls: list[tuple[str, str]], xml_dir: Path) -> list[Path]:
    """Download XML files, skipping already-downloaded ones."""
    xml_dir.mkdir(parents=True, exist_ok=True)
    local_files = []
    for datum, url in session_urls:
        filename = url.split("/")[-1]
        local_path = xml_dir / filename
        if local_path.exists():
            logger.info(f"Already downloaded: {filename}, skipping")
            local_files.append(local_path)
            continue
        try:
            logger.info(f"Downloading {filename} ({datum})...")
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            local_path.write_bytes(r.content)
            local_files.append(local_path)
        except Exception as exc:
            logger.error(f"Failed to download {url}: {exc}")
    return local_files


def parse_xmls_to_df(xml_files: list[Path]) -> pd.DataFrame:
    df = pd.DataFrame(columns=['type', 'date', 'id', 'party', 'top_key', 'text'])
    for xml_file in xml_files:
        logger.info(f"Parsing {xml_file.name}...")
        process_bundestag_xml(str(xml_file), df)
    return df.reset_index(drop=True)


def normalize_parties(df: pd.DataFrame) -> pd.DataFrame:
    before = set(df['party'].unique())
    df['party'] = df['party'].map(PARTY_NAME_MAP).fillna(df['party'])
    after = set(df['party'].unique())
    unmapped = after - set(PARTY_NAME_MAP.values())
    if unmapped:
        logger.warning(f"Unmapped party names (kept as-is): {unmapped}")
    logger.info(f"Party names: {before} → {after}")
    return df


def get_last_embedded_date(rag) -> str:
    """Return the day after the latest embedded speech date (auto-start date for next fetch)."""
    meta = rag.vector_store._collection.get(include=["metadatas"])["metadatas"]
    dates = [m["date"] for m in meta if m.get("type") == "speech"]
    if not dates:
        return "2021-10-26"  # wahlperiode 20 start
    dt = datetime.strptime(str(max(dates)), "%Y%m%d")
    logger.info(f"Last embedded speech date: {dt.date()}")
    return (dt + timedelta(days=1)).strftime("%Y-%m-%d")


def _update_tops_json(xml_files: list[Path], model) -> None:
    """Merge new TOPs from xml_files into tops.json, classifying new keys with Gemini."""
    TOPS_JSON.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if TOPS_JSON.exists():
        existing = json.loads(TOPS_JSON.read_text())

    new_tops = {}
    for xml_file in xml_files:
        new_tops.update(build_tops_lookup(str(xml_file)))

    to_classify = {k: v for k, v in new_tops.items()
                   if (k not in existing or not existing[k].get("topic"))
                   and (not v.get("topic") or len(v.get("topic", "")) > 60)}
    if to_classify:
        def _label(v):
            if v.get('title'):
                return v['title']
            if v.get('subtitle'):
                return v['subtitle']
            subs = v.get('subtopics') or []
            titles = [s['title'] for s in subs if s.get('title')]
            return '; '.join(titles[:3]) if titles else '(kein Titel)'

        lines = "\n".join(
            f"{k}: {_label(v).strip()}"
            for k, v in to_classify.items()
        )
        try:
            response = model.invoke(
                "Du bekommst eine Liste von Bundestagstagesordnungspunkten.\n"
                "Weise jedem ein kurzes, konsistentes Thema zu (2–4 Wörter auf Deutsch).\n"
                "Wenn ein Punkt mehrere Themen umfasst, trenne sie mit Komma (z.B. 'Wahlalter, Grundgesetz').\n"
                "Format: top_key: Thema — eine Zeile pro Punkt, keine Erklärungen.\n\n"
                + lines
            )
            for line in response.content.strip().splitlines():
                if ": " in line:
                    key, _, topic = line.partition(": ")
                    key = key.strip()
                    if key in to_classify:
                        new_tops[key]["topic"] = topic.strip()
            logger.info(f"Classified {len(to_classify)} new TOPs via Gemini")
        except Exception as exc:
            logger.warning(f"Gemini TOP classification failed: {exc}")

    # Fallback: replace missing or generic-sounding Gemini topics with the actual title
    _generic = re.compile(r'^(Tagesordnungspunkt|Zusatzpunkt|TOP|ZP)\s*\d+', re.IGNORECASE)
    for key, v in to_classify.items():
        current = new_tops[key].get("topic", "")
        if not current or _generic.match(current):
            fallback = (v.get("title") or v.get("subtitle") or "").strip()
            if fallback and not _generic.match(fallback):
                new_tops[key]["topic"] = fallback[:80]
                logger.warning(f"Used title as fallback topic for {key}: {fallback[:80]}")

    for key, new_val in new_tops.items():
        if key in existing and not new_val.get("topic") and existing[key].get("topic"):
            new_val["topic"] = existing[key]["topic"]
    existing.update(new_tops)
    TOPS_JSON.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    logger.info(f"tops.json updated: {len(existing)} total TOPs, {len(new_tops)} from this batch")


def _iso_to_de_date(iso_date: str) -> str:
    """'2026-07-10' -> '10.07.2026' (tops.json's date format)."""
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d.%m.%Y")


def _build_drucksache_index(tops: dict) -> dict:
    """Map Drucksachen-Nummer -> list of (top_key, subtopic_key_or_None, date).

    A single Gesetzentwurf accumulates multiple Drucksachen over its lifecycle
    (Erste Beratung, Beschlussempfehlung, ...) and the same Drucksache can also
    resurface across different TOPs/sessions — so this must support multiple
    candidates per Drucksache, disambiguated later by date.
    """
    index = defaultdict(list)
    for top_key, top in tops.items():
        date = top.get("date", "")
        if top.get("drucksache"):
            index[top["drucksache"]].append((top_key, None, date))
        for sub in top.get("subtopics", []):
            if sub.get("drucksache"):
                index[sub["drucksache"]].append((top_key, sub["key"], date))
    return index


def _build_date_index(tops: dict) -> dict:
    """Map date (DD.MM.YYYY) -> list of (top_key, subtopic_key_or_None, title) for fallback matching."""
    index = defaultdict(list)
    for top_key, top in tops.items():
        date = top.get("date", "")
        title = top.get("title") or top.get("subtitle") or ""
        index[date].append((top_key, None, title))
        for sub in top.get("subtopics", []):
            index[date].append((top_key, sub.get("key"), sub.get("title", "")))
    return index


def _update_abstimmungen_json(tops: dict, since_date: str = None) -> dict:
    """
    Fetch namentliche Abstimmungen (roll-call votes) from abgeordnetenwatch.de and
    link them to tops.json entries via Drucksachen-Nummer (primary) or date+title (fallback).
    Merge additively into data/abstimmungen.json. Returns a summary dict.
    """
    ABSTIMMUNGEN_JSON.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if ABSTIMMUNGEN_JSON.exists():
        existing = json.loads(ABSTIMMUNGEN_JSON.read_text())

    drucksache_index = _build_drucksache_index(tops)
    date_index = _build_date_index(tops)

    polls = fetch_polls(since_date=since_date)
    linked = 0
    unmatched = []

    for poll in polls:
        try:
            poll_date_de = _iso_to_de_date(poll.get("field_poll_date", ""))
        except ValueError:
            poll_date_de = ""

        drucksachen = extract_drucksachen_from_intro(poll.get("field_intro", ""))
        candidates = [c for d in drucksachen for c in drucksache_index.get(d, [])]

        match = None
        # Prefer a candidate whose TOP date exactly matches the poll date — a Gesetzentwurf
        # accumulates several Drucksachen across readings (Erste Beratung, Beschlussempfehlung, ...),
        # and a plain "first Drucksache match" can land on an earlier reading instead of the one
        # where the vote actually happened.
        exact_date_candidates = [c for c in candidates if c[2] == poll_date_de]
        if exact_date_candidates:
            match = exact_date_candidates[0][:2]
        elif candidates:
            match = candidates[0][:2]

        if match is None:
            label = (poll.get("label") or "").lower()
            for top_key, sub_key, title in date_index.get(poll_date_de, []):
                if title and (label in title.lower() or title.lower() in label):
                    match = (top_key, sub_key)
                    break

        if match is None:
            unmatched.append({
                "poll_id": poll.get("id"),
                "label": poll.get("label"),
                "date": poll.get("field_poll_date"),
            })
            continue

        top_key, sub_key = match
        vote_data = fetch_poll_votes(poll["id"])
        entry = {
            "poll_id": poll.get("id"),
            "label": poll.get("label"),
            "drucksache": drucksachen[0] if drucksachen else None,
            "angenommen": poll.get("field_accepted"),
            "abgeordnetenwatch_url": poll.get("abgeordnetenwatch_url"),
            **vote_data,
        }
        existing.setdefault(top_key, {})[sub_key or "_top"] = entry
        linked += 1

    ABSTIMMUNGEN_JSON.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    logger.info(f"abstimmungen.json updated: {linked} verknüpft, {len(unmatched)} unmatched (von {len(polls)} Polls)")
    if unmatched:
        logger.warning(f"Unmatched polls: {unmatched}")

    return {"polls_found": len(polls), "linked": linked, "unmatched": unmatched}


def run_update(rag, since_date: str = None, prune_weeks: int = 4) -> dict:
    """
    Full weekly update pipeline:
    1. Fetch new session XMLs since `since_date` (defaults to day after last embedded speech)
    2. Parse, normalize, and embed new speeches into ChromaDB
    3. Prune speeches older than `prune_weeks` weeks from ChromaDB
    4. Rebuild tops.json with newly classified TOPs
    5. Upload vector store + tops.json to GCS (when GCS_CHROMA_PATH is configured)

    Returns a summary dict: {new_sessions, embedded, pruned}.
    """
    since_date = since_date or get_last_embedded_date(rag)
    logger.info(f"Running update pipeline since {since_date} (prune >{prune_weeks}w)")

    session_urls = fetch_session_xml_urls(since_date)
    xml_files = []
    n_embedded = 0

    if session_urls:
        xml_files = download_xmls(session_urls, XML_DIR)
        df = parse_xmls_to_df(xml_files)
        logger.info(f"Parsed {len(df)} speech rows across {len(xml_files)} sessions")

        if not df.empty:
            df = normalize_parties(df)
            Path("data").mkdir(parents=True, exist_ok=True)
            staging_csv = f"data/speeches_update_{since_date}.csv"
            df.to_csv(staging_csv, index=False)
            n_embedded = rag.add_to_vector_store(staging_csv)
            logger.info(f"Embedded {n_embedded} chunks. Total: {rag.get_num_of_vectors()}")
    else:
        logger.info("No new sessions found.")

    # Only prune if new data was successfully embedded
    pruned = 0
    if n_embedded > 0:
        cutoff = datetime.now() - timedelta(weeks=prune_weeks)
        pruned = rag.prune_speeches_before(cutoff)
    else:
        logger.info("Skipping prune — no new data embedded.")

    # Update tops.json with newly parsed TOPs
    if xml_files:
        _update_tops_json(xml_files, rag.model)

    # Fetch and link namentliche Abstimmungen (needs fresh tops.json for Drucksachen-Zuordnung)
    if xml_files:
        tops = json.loads(TOPS_JSON.read_text()) if TOPS_JSON.exists() else {}
        _update_abstimmungen_json(tops, since_date=since_date)

    # Persist to GCS so next cold start picks up the fresh data
    if USE_GCS_CHROMA:
        logger.info("Uploading updated store to GCS...")
        rag.upload_to_gcs()

    return {
        "new_sessions": len(session_urls),
        "embedded": n_embedded,
        "pruned": pruned,
    }
