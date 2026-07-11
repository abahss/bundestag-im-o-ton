#!/usr/bin/env python
"""
Re-embed manifesto data with normalized party names.

Deletes existing manifesto entries from ChromaDB and re-embeds
the manifesto CSV with canonical party names matching PARTIES_LIST.

Usage:
    uv run python bin/reembed_manifestos.py
"""

import logging
import pandas as pd
from pathlib import Path

from practicepreach.rag import Rag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MANIFESTO_CSV = Path("data/data_manifestos-plus-20-and-21-wahlperiode.csv")
NORMALIZED_CSV = Path("data/data_manifestos_normalized.csv")

PARTY_NAME_MAP = {
    'CDU/CSU': 'CDUCSU',
    'AfD': 'AFD',
    'SPD': 'SPD',
    'BÜNDNIS\xa090/DIE GRÜNEN': 'GRÜNEN',
    'BÜNDNIS 90/DIE GRÜNEN': 'GRÜNEN',
    'Die Linke': 'LINKE',
}

PARTIES_LIST = ['AFD', 'SPD', 'CDUCSU', 'GRÜNEN', 'LINKE']


def normalize_and_filter(csv_path: Path, out_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    before = set(df['party'].dropna().unique())
    df['party'] = df['party'].map(PARTY_NAME_MAP).fillna(df['party'])
    df = df[df['party'].isin(PARTIES_LIST)]
    logger.info(f"Party names: {before} → {set(df['party'].unique())}")
    logger.info(f"Rows after filtering to canonical parties: {len(df)}")
    df.to_csv(out_path, index=False)
    logger.info(f"Saved normalized CSV → {out_path}")
    return df


def delete_manifestos(rag: Rag):
    collection = rag.vector_store._collection
    before = collection.count()
    collection.delete(where={'type': {'$eq': 'manifesto'}})
    after = collection.count()
    logger.info(f"Deleted {before - after} manifesto chunks ({after} remaining)")


if __name__ == "__main__":
    logger.info("Normalizing manifesto CSV...")
    normalize_and_filter(MANIFESTO_CSV, NORMALIZED_CSV)

    logger.info("Initialising RAG (loads embedding model)...")
    rag = Rag()
    logger.info(f"Vector store has {rag.get_num_of_vectors()} chunks before cleanup.")

    logger.info("Deleting existing manifesto entries from ChromaDB...")
    delete_manifestos(rag)

    logger.info("Re-embedding manifestos with normalized party names...")
    n = rag.add_to_vector_store(str(NORMALIZED_CSV))
    logger.info(f"Done. Embedded {n} chunks. Total vectors: {rag.get_num_of_vectors()}")
