#!/usr/bin/env python
"""
Update ChromaDB with new Bundestag speeches since a given date.
Optionally purge specific top_keys from the vector store, tops.json, and summaries cache.

Usage:
    uv run python bin/update_speeches.py --since 2025-11-28
    uv run python bin/update_speeches.py   # auto-detects last embedded date from ChromaDB
    uv run python bin/update_speeches.py --purge-keys "88_Tagesordnungspunkt 22"
    uv run python bin/update_speeches.py --xml-urls https://www.bundestag.de/resource/blob/1194732/21090.xml
"""

import argparse
import json
import logging
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from practicepreach.rag import Rag
from practicepreach.updater import run_update, TOPS_JSON, XML_DIR, parse_xmls_to_df, normalize_parties, _update_tops_json
from practicepreach.params import USE_GCS_CHROMA
from practicepreach.constants import PARTIES_LIST

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SUMMARIES_CACHE = Path("data/summaries_cache.json")


def purge_top_keys(rag: Rag, top_keys: list[str]) -> None:
    """Remove top_keys from vector store, tops.json, and summaries cache."""
    col = rag.vector_store._collection

    for key in top_keys:
        # Vector store
        result = col.get(where={"top_key": {"$eq": key}}, include=[])
        ids = result.get("ids", [])
        if ids:
            col.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} vectors for '{key}'")
        else:
            logger.warning(f"No vectors found for '{key}'")

        # tops.json
        if TOPS_JSON.exists():
            tops = json.loads(TOPS_JSON.read_text())
            if key in tops:
                del tops[key]
                TOPS_JSON.write_text(json.dumps(tops, ensure_ascii=False, indent=2))
                logger.info(f"Removed '{key}' from tops.json")
            else:
                logger.warning(f"'{key}' not found in tops.json")

        # summaries cache
        if SUMMARIES_CACHE.exists():
            cache = json.loads(SUMMARIES_CACHE.read_text())
            if key in cache:
                del cache[key]
                SUMMARIES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
                logger.info(f"Removed '{key}' from summaries_cache.json")


def regenerate_summaries(rag: Rag, top_keys: list[str]) -> None:
    """Delete summary cache entries for top_keys and regenerate them."""
    tops = json.loads(TOPS_JSON.read_text()) if TOPS_JSON.exists() else {}
    cache = json.loads(SUMMARIES_CACHE.read_text()) if SUMMARIES_CACHE.exists() else {}

    for key in top_keys:
        if key in cache:
            del cache[key]
            logger.info(f"Cleared summary cache for '{key}'")
        else:
            logger.warning(f"'{key}' not in summaries cache — will generate fresh")

    SUMMARIES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))

    for key in top_keys:
        top = tops.get(key, {})
        subtitle = top.get("subtitle", "") or top.get("title", "")
        logger.info(f"Regenerating summaries for '{key}'...")

        try:
            general_text = rag.summarize_topic_general(key, subtitle)
            if general_text:
                cache.setdefault(key, {})["general"] = {"summary": general_text}
                SUMMARIES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.warning(f"General summary failed for {key}: {e}")
            general_text = ""

        def generate_party(party):
            return party, rag.summarize_by_top_key(key, party, general_text)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(generate_party, p): p for p in PARTIES_LIST}
            for future in as_completed(futures):
                try:
                    party, summary = future.result()
                    if summary:
                        cache.setdefault(key, {})[party] = {"summary": summary}
                except Exception as e:
                    logger.warning(f"Party summary failed for {futures[future]}: {e}")

        SUMMARIES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
        logger.info(f"Done: '{key}'")
        time.sleep(2)


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
    parser.add_argument(
        "--purge-keys",
        nargs="+",
        metavar="TOP_KEY",
        help="top_keys to delete from vector store, tops.json, and summaries cache before updating.",
    )
    parser.add_argument(
        "--purge-only",
        action="store_true",
        help="Only purge, skip the update pipeline (still uploads to GCS).",
    )
    parser.add_argument(
        "--xml-urls",
        nargs="+",
        metavar="URL",
        help="Process specific XML URLs directly, bypassing the Bundestag API search.",
    )
    parser.add_argument(
        "--purge-summaries",
        nargs="+",
        metavar="TOP_KEY",
        help="Delete summary cache entries for these top_keys and regenerate them (ChromaDB untouched).",
    )
    args = parser.parse_args()

    logger.info("Initialising RAG (downloads ChromaDB + JSONs from GCS)...")
    rag = Rag()

    if args.purge_summaries:
        logger.info(f"Regenerating summaries for {len(args.purge_summaries)} key(s): {args.purge_summaries}")
        regenerate_summaries(rag, args.purge_summaries)
        if USE_GCS_CHROMA:
            logger.info("Uploading updated summaries cache to GCS...")
            rag.upload_to_gcs()
        logger.info("Done.")
        return

    if args.purge_keys:
        logger.info(f"Purging {len(args.purge_keys)} key(s): {args.purge_keys}")
        purge_top_keys(rag, args.purge_keys)

    if args.purge_only:
        if USE_GCS_CHROMA:
            logger.info("Uploading purged state to GCS...")
            rag.upload_to_gcs()
        logger.info("Purge complete.")
        return

    if args.xml_urls:
        XML_DIR.mkdir(parents=True, exist_ok=True)
        xml_files = []
        for url in args.xml_urls:
            filename = url.split("/")[-1]
            local_path = XML_DIR / filename
            if local_path.exists():
                logger.info(f"Already downloaded: {filename}, skipping")
            else:
                logger.info(f"Downloading {url}...")
                r = requests.get(url, timeout=60)
                r.raise_for_status()
                local_path.write_bytes(r.content)
            xml_files.append(local_path)

        df = parse_xmls_to_df(xml_files)
        logger.info(f"Parsed {len(df)} speech rows")
        n_embedded = 0
        if not df.empty:
            df = normalize_parties(df)
            Path("data").mkdir(parents=True, exist_ok=True)
            staging_csv = "data/speeches_xml_urls.csv"
            df.to_csv(staging_csv, index=False)
            n_embedded = rag.add_to_vector_store(staging_csv)
            logger.info(f"Embedded {n_embedded} chunks")
        _update_tops_json(xml_files, rag.model)
        if USE_GCS_CHROMA:
            logger.info("Uploading to GCS...")
            rag.upload_to_gcs()
        logger.info(f"Done. Embedded {n_embedded} chunks.")
        return

    result = run_update(rag, since_date=args.since, prune_weeks=args.prune_weeks)
    logger.info(f"Update complete: {result}")


if __name__ == "__main__":
    main()
