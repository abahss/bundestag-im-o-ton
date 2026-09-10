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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from requests.exceptions import ChunkedEncodingError, ConnectionError

from langchain.chat_models import init_chat_model

from practicepreach.tools import (
    build_tops_lookup,
    haushaltswoche_hub_entries,
    process_bundestag_xml,
)
from practicepreach.params import BUNDESTAG_API_KEY, GOOGLE_API_KEY, USE_GCS_CHROMA
from practicepreach.constants import PARTY_NAME_MAP, PARTIES_LIST
from practicepreach.abgeordnetenwatch import fetch_polls, fetch_poll_votes, extract_drucksachen_from_intro
from practicepreach.drucksache_summary import (
    DrucksacheNotAvailable,
    drucksache_context_for_top,
    summarize_drucksache,
    verified_drucksache_numbers,
)
from practicepreach.search_index import write_search_index

logger = logging.getLogger(__name__)

BASE_URL = "https://search.dip.bundestag.de/api/v1"
XML_DIR = Path("data/xml_updates")
TOPS_JSON = Path("data/tops.json")
ABSTIMMUNGEN_JSON = Path("data/abstimmungen.json")
SUMMARIES_CACHE = Path("data/summaries_cache.json")
DRUCKSACHE_SUMMARIES_CACHE = Path("data/drucksache_summaries.json")
PREWARM_SLEEP_BETWEEN_TOPS = 2
PREWARM_MAX_RETRIES = 3


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

    # Synthetic Haushaltswoche hubs, derived from the merged set (a session's Einzelplan
    # blocks and its Einbringung TOP can arrive in different update runs).
    for hub_key, hub in haushaltswoche_hub_entries(existing).items():
        prev_topic = existing.get(hub_key, {}).get("topic")
        existing[hub_key] = {**hub, "topic": prev_topic or "Bundeshaushalt"}

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

    def _add(numbers, top_key, sub_key, date):
        for nr in numbers:
            entry = (top_key, sub_key, date)
            if entry not in index[nr]:
                index[nr].append(entry)

    for top_key, top in tops.items():
        date = top.get("date", "")
        _add(top.get("drucksachen") or ([top["drucksache"]] if top.get("drucksache") else []),
             top_key, None, date)
        for sub in top.get("subtopics", []):
            _add(sub.get("drucksachen") or ([sub["drucksache"]] if sub.get("drucksache") else []),
                 top_key, sub["key"], date)
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


def _get_lightweight_model():
    """A chat-model-only client, without the embeddings/Chroma setup Rag() carries.
    Avoids downloading the full vector store just to summarize some text."""
    return init_chat_model(
        "google_genai:gemini-2.5-flash",
        google_api_key=GOOGLE_API_KEY,
        thinking_budget=0,
        temperature=0,
    )


def _summarize_poll_intro(model, intro_html: str) -> str:
    """Condense abgeordnetenwatch's field_intro into a short, neutral description."""
    text = re.sub(r"<[^>]+>", "", intro_html or "").strip()
    if not text:
        return ""
    response = model.invoke(
        "Du bist ein politischer Analyst. Fasse die folgende Beschreibung einer "
        "Bundestagsabstimmung in 1-2 sachlichen Sätzen zusammen. Nenne keine "
        "einzelnen Namen von Abgeordneten. Bleibe neutral, ohne eigene Wertung. "
        "Wiederhole nicht das Abstimmungsergebnis (Ja-/Nein-Stimmen, angenommen/abgelehnt) "
        "— das wird an anderer Stelle bereits angezeigt. Antworte nur mit der "
        "Zusammenfassung, keine Einleitung.\n\n"
        + text
    )
    return response.content.strip()


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
    model = _get_lightweight_model()

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
        try:
            beschreibung = _summarize_poll_intro(model, poll.get("field_intro", ""))
        except Exception as exc:
            logger.warning(f"Poll-Zusammenfassung fehlgeschlagen für poll_id={poll.get('id')}: {exc}")
            beschreibung = ""
        entry = {
            "poll_id": poll.get("id"),
            "label": poll.get("label"),
            "beschreibung": beschreibung,
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


def _read_summaries_cache() -> dict:
    if SUMMARIES_CACHE.exists():
        return json.loads(SUMMARIES_CACHE.read_text())
    return {}


def _write_summaries_cache(cache: dict) -> None:
    SUMMARIES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


def _split_summary_text(text: str) -> tuple[str, str]:
    kernposition = ""
    quote_lines = []
    for line in text.strip().splitlines():
        s = line.strip()
        if s.startswith("**Kernposition:**"):
            kernposition = s
        elif s.startswith('*"') or s.startswith('"'):
            quote_lines.append(line)
    return kernposition, "\n".join(quote_lines)


def _call_with_retry(fn, *args, retries=PREWARM_MAX_RETRIES):
    for attempt in range(retries):
        try:
            return fn(*args)
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                wait = 30 * (attempt + 1)
                logger.warning(f"Rate limit hit, waiting {wait}s before retry {attempt + 1}/{retries}...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {retries} retries")


def prewarm_summaries(rag, tops: dict, active_keys: set[str]) -> dict:
    """
    Generate + cache missing summaries (general + per party) for all active TOPs, so
    the persistent cache stays complete instead of relying on on-demand generation
    that only lives on the current container's ephemeral disk. Skips TOPs that
    already have a complete cache entry, so it's cheap to re-run on every update.

    Runs after prewarm_drucksache_summaries: a document-backed TOP gets the
    "Variante D" general summary (debate only, **Verlauf:** format) with its
    Drucksachen-Zusammenfassung as "do not repeat" context. An older general summary
    of a now-document-backed TOP is regenerated.
    """
    active_tops = {k: v for k, v in tops.items() if k in active_keys}
    cache = _read_summaries_cache()
    drs_cache = (json.loads(DRUCKSACHE_SUMMARIES_CACHE.read_text())
                 if DRUCKSACHE_SUMMARIES_CACHE.exists() else {})
    processed = skipped = failed = 0

    for i, (top_key, top) in enumerate(active_tops.items()):
        cached = cache.get(top_key, {})
        missing_parties = [p for p in PARTIES_LIST if p not in cached]

        drs_context = drucksache_context_for_top(top, drs_cache)
        # Einzelplan ressort debates are a pure Aussprache with no bill — use the
        # debate-only **Verlauf:** format anyway.
        force_verlauf = top.get("top_id", "").startswith("Einzelplan")
        cached_general = (cached["general"].get("summary", "")
                          if isinstance(cached.get("general"), dict) else "")
        # A pre-Variante-D general summary of a TOP that should now be **Verlauf:** is stale.
        general_stale = (bool(drs_context) or force_verlauf) and bool(cached_general) and \
            not cached_general.lstrip().startswith("**Verlauf:**")
        needs_general = not cached_general or general_stale

        if not missing_parties and not needs_general:
            skipped += 1
            continue

        subtitle = top.get("subtitle", "") or top.get("title", "")
        logger.info(f"Prewarming [{i + 1}/{len(active_tops)}] {top_key}"
                    f"{' (general stale)' if general_stale else ''}")

        if needs_general:
            try:
                general_text = _call_with_retry(
                    rag.summarize_topic_general, top_key, subtitle, drs_context, force_verlauf
                )
                if general_text:
                    cache.setdefault(top_key, {})["general"] = {"summary": general_text}
                    _write_summaries_cache(cache)
            except Exception as e:
                logger.warning(f"General summary failed for {top_key}: {e}")
                general_text = cached_general
                failed += 1
        else:
            general_text = cached_general

        def generate_party(party):
            return party, _call_with_retry(rag.summarize_by_top_key, top_key, party, general_text)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(generate_party, p): p for p in missing_parties}
            for future in as_completed(futures):
                try:
                    party, summary = future.result()
                    if summary:
                        kp, qt = _split_summary_text(summary)
                        cache.setdefault(top_key, {})[party] = {"kernposition": kp, "quotes_text": qt, "count": 0}
                except Exception as e:
                    logger.warning(f"Party summary failed for {futures[future]}: {e}")
                    failed += 1

        _write_summaries_cache(cache)
        processed += 1
        time.sleep(PREWARM_SLEEP_BETWEEN_TOPS)

    logger.info(f"Prewarm done. Processed: {processed}, skipped: {skipped}, failed: {failed}")
    return {"processed": processed, "skipped": skipped, "failed": failed}


HAUSHALTSWOCHE_MIN_EINZELPLAENE = 2


def prewarm_haushaltswoche_overview(rag, tops: dict) -> dict:
    """For every synthetic Haushaltswoche hub, build the cross-cutting `general` summary
    from its Einzelplan `general` summaries (which prewarm_summaries has already put in
    the cache). Cheap to re-run: skips hubs that already have one."""
    hubs = {k: v for k, v in tops.items() if v.get("top_id") == "Haushaltswoche"}
    if not hubs:
        return {"processed": 0, "skipped": 0, "failed": 0}

    cache = _read_summaries_cache()
    processed = skipped = failed = 0

    for hub_key, hub in hubs.items():
        if isinstance(cache.get(hub_key, {}).get("general"), dict):
            skipped += 1
            continue

        ep_summaries = [
            cache[k]["general"]["summary"]
            for k in hub.get("einzelplaene", [])
            if isinstance(cache.get(k, {}).get("general"), dict)
            and cache[k]["general"].get("summary")
        ]
        if len(ep_summaries) < HAUSHALTSWOCHE_MIN_EINZELPLAENE:
            logger.info(f"Skipping {hub_key}: only {len(ep_summaries)} Einzelplan summaries cached")
            skipped += 1
            continue

        try:
            text = _call_with_retry(rag.summarize_haushaltswoche_overview, ep_summaries)
        except Exception as e:
            logger.warning(f"Haushaltswoche overview failed for {hub_key}: {e}")
            failed += 1
            continue

        if text:
            cache.setdefault(hub_key, {})["general"] = {"summary": text}
            _write_summaries_cache(cache)
            processed += 1
            logger.info(f"Prewarmed Haushaltswoche overview for {hub_key}")

    logger.info(f"Haushaltswoche overview prewarm done. "
                f"Processed: {processed}, skipped: {skipped}, failed: {failed}")
    return {"processed": processed, "skipped": skipped, "failed": failed}


def prewarm_drucksache_summaries(tops: dict, active_keys: set[str]) -> dict:
    """Generate + cache a Drucksachen-Zusammenfassung for every verified canonical
    Drucksache of an active TOP that is still missing one. Cheap to re-run: skips
    numbers already cached, including ones permanently marked as having no
    machine-readable DIP text."""
    cache = json.loads(DRUCKSACHE_SUMMARIES_CACHE.read_text()) if DRUCKSACHE_SUMMARIES_CACHE.exists() else {}
    numbers = verified_drucksache_numbers(tops, active_keys)
    todo = sorted(nr for nr in numbers if nr not in cache)
    processed = failed = 0

    for i, nr in enumerate(todo):
        logger.info(f"Prewarming Drucksache [{i + 1}/{len(todo)}] {nr}")
        try:
            entry = _call_with_retry(summarize_drucksache, nr)
            entry.pop("raw", None)
            cache[nr] = entry
            processed += 1
        except DrucksacheNotAvailable as e:
            cache[nr] = {"nummer": nr, "error": str(e)}
            logger.warning(f"No DIP text for {nr}: {e}")
        except Exception as e:
            logger.warning(f"Drucksache summary failed for {nr}: {e}")
            failed += 1
            continue
        DRUCKSACHE_SUMMARIES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
        time.sleep(PREWARM_SLEEP_BETWEEN_TOPS)

    logger.info(f"Drucksache prewarm done. Processed: {processed}, failed: {failed}, "
                f"skipped: {len(numbers) - len(todo)}")
    return {"processed": processed, "failed": failed, "skipped": len(numbers) - len(todo)}


OVERRIDES_JSON = Path("data/drucksache_overrides.json")
DIP_CACHE_JSON = Path("data/dip_drucksache_cache.json")


def verify_drucksachen_in_tops_json() -> dict:
    """Run the DIP cross-check over the on-disk tops.json and write `drucksache_verified`
    back into it (+ update the DIP verdict cache). Needs the machine-local overrides /
    DIP-cache files, so it is opt-in — the /admin/update path in Cloud Run skips it."""
    from practicepreach.drucksache_verify import verify_tops

    if not TOPS_JSON.exists():
        return {}
    tops = json.loads(TOPS_JSON.read_text())
    overrides = json.loads(OVERRIDES_JSON.read_text()) if OVERRIDES_JSON.exists() else {}
    cache = json.loads(DIP_CACHE_JSON.read_text()) if DIP_CACHE_JSON.exists() else {}

    counts = verify_tops(tops, overrides, cache)

    TOPS_JSON.write_text(json.dumps(tops, ensure_ascii=False, indent=2))
    DIP_CACHE_JSON.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
    logger.info(f"drucksache_verified written into tops.json: {counts}")
    return counts


def run_update(rag, since_date: str = None, prune_weeks: int = 4,
               verify_drucksachen: bool = False) -> dict:
    """
    Full weekly update pipeline:
    1. Fetch new session XMLs since `since_date` (defaults to day after last embedded speech)
    2. Parse, normalize, and embed new speeches into ChromaDB
    3. Prune speeches older than `prune_weeks` weeks from ChromaDB
    4. Rebuild tops.json with newly classified TOPs
    5. Prewarm summaries_cache.json for all active TOPs still missing an entry
    6. Upload vector store + tops.json + summaries_cache.json to GCS (when GCS_CHROMA_PATH is configured)

    Returns a summary dict: {new_sessions, embedded, pruned, prewarmed}.
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

    # DIP cross-check → drucksache_verified. Before the Drucksachen-Zusammenfassung
    # prewarm below, so a brand-new document-backed TOP gets its summary on the same run.
    verified = {}
    if xml_files and verify_drucksachen:
        verified = verify_drucksachen_in_tops_json()

    # Fetch and link namentliche Abstimmungen (needs fresh tops.json for Drucksachen-Zuordnung)
    if xml_files:
        tops = json.loads(TOPS_JSON.read_text()) if TOPS_JSON.exists() else {}
        _update_abstimmungen_json(tops, since_date=since_date)

    # Prewarm summaries for active TOPs so the persistent cache stays complete —
    # cheap to re-run since it skips TOPs that already have a full cache entry.
    tops = json.loads(TOPS_JSON.read_text()) if TOPS_JSON.exists() else {}
    active_keys = {
        m["top_key"]
        for m in rag.vector_store._collection.get(
            where={"type": {"$eq": "speech"}}, include=["metadatas"]
        )["metadatas"]
        if m.get("top_key")
    }
    # Drucksachen-Zusammenfassungen first: the general summary of a document-backed TOP
    # takes its Drucksachen-Zusammenfassung as "do not repeat" context.
    drucksache_prewarmed = prewarm_drucksache_summaries(tops, active_keys)

    prewarmed = prewarm_summaries(rag, tops, active_keys)

    # Haushaltswoche hubs: cross-cutting overview from the fresh Einzelplan generals.
    haushaltswoche_prewarmed = prewarm_haushaltswoche_overview(rag, tops)

    # Client-side search index (title + summaries + Drucksachen-Zusammenfassungen)
    indexed = write_search_index(tops=tops)
    logger.info(f"Wrote search_index.json — {indexed} TOPs")

    # Persist to GCS so next cold start picks up the fresh data
    if USE_GCS_CHROMA:
        logger.info("Uploading updated store to GCS...")
        rag.upload_to_gcs()

    return {
        "new_sessions": len(session_urls),
        "embedded": n_embedded,
        "pruned": pruned,
        "prewarmed": prewarmed,
        "drucksache_prewarmed": drucksache_prewarmed,
        "haushaltswoche_prewarmed": haushaltswoche_prewarmed,
        "drucksache_verified": verified,
        "search_indexed": indexed,
    }
