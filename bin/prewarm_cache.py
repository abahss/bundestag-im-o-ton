#!/usr/bin/env python
"""
Pre-warm summaries_cache.json for all active TOPs.
Skips TOPs that are already fully cached. Safe to re-run.

Usage:
    cd practice-vs-preach
    uv run python bin/prewarm_cache.py
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from practicepreach.constants import PARTIES_LIST
from practicepreach.rag import Rag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

TOPS_JSON = Path("data/tops.json")
SUMMARIES_CACHE = Path("data/summaries_cache.json")
SLEEP_BETWEEN_TOPS = 2
MAX_RETRIES = 3


def read_cache() -> dict:
    if SUMMARIES_CACHE.exists():
        return json.loads(SUMMARIES_CACHE.read_text())
    return {}


def write_cache(cache: dict):
    SUMMARIES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


def split_summary(text: str) -> tuple[str, str]:
    kernposition = ""
    quote_lines = []
    for line in text.strip().splitlines():
        s = line.strip()
        if s.startswith("**Kernposition:**"):
            kernposition = s
        elif s.startswith('*"') or s.startswith('"'):
            quote_lines.append(line)
    return kernposition, "\n".join(quote_lines)


def call_with_retry(fn, *args, retries=MAX_RETRIES):
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


def main():
    logger.info("Initializing RAG (downloads chroma from GCS)...")
    rag = Rag()

    tops = json.loads(TOPS_JSON.read_text())

    col = rag.vector_store._collection
    result = col.get(where={"type": {"$eq": "speech"}}, include=["metadatas"])
    active_keys = {m["top_key"] for m in result["metadatas"] if m.get("top_key")}
    active_tops = {k: v for k, v in tops.items() if k in active_keys}
    logger.info(f"{len(active_tops)} active TOPs found")

    cache = read_cache()
    skipped = 0
    processed = 0
    failed = 0

    for i, (top_key, top) in enumerate(active_tops.items()):
        cached = cache.get(top_key, {})
        missing_parties = [p for p in PARTIES_LIST if p not in cached]
        has_general = "general" in cached

        if not missing_parties and has_general:
            skipped += 1
            continue

        subtitle = top.get("subtitle", "") or top.get("title", "")
        logger.info(f"[{i+1}/{len(active_tops)}] {top_key}")

        # General summary
        if not has_general:
            try:
                general_text = call_with_retry(rag.summarize_topic_general, top_key, subtitle)
                if general_text:
                    cache.setdefault(top_key, {})["general"] = {"summary": general_text}
                    write_cache(cache)
            except Exception as e:
                logger.warning(f"General summary failed for {top_key}: {e}")
                general_text = ""
                failed += 1
        else:
            general_text = cached["general"].get("summary", "") if isinstance(cached.get("general"), dict) else ""

        # Party summaries in parallel
        def generate_party(party):
            return party, call_with_retry(rag.summarize_by_top_key, top_key, party, general_text)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(generate_party, p): p for p in missing_parties}
            for future in as_completed(futures):
                try:
                    party, summary = future.result()
                    if summary:
                        kp, qt = split_summary(summary)
                        cache.setdefault(top_key, {})[party] = {
                            "kernposition": kp,
                            "quotes_text": qt,
                            "count": 0,
                        }
                except Exception as e:
                    logger.warning(f"Party summary failed for {futures[future]}: {e}")
                    failed += 1

        write_cache(cache)
        processed += 1
        time.sleep(SLEEP_BETWEEN_TOPS)

    logger.info(f"Done. Processed: {processed}, skipped: {skipped}, failed: {failed}")
    logger.info("Upload cache to GCS:")
    logger.info("  gsutil cp data/summaries_cache.json gs://batch-2170-political-reality-check/data/summaries_cache.json")


if __name__ == "__main__":
    main()
