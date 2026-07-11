"""
Quick local tests for ChromaDB filters, including top_key.
Run: uv run python practicepreach/test.py
"""
import chromadb
from dotenv import load_dotenv
import os
from collections import Counter

load_dotenv()

PERSIST_DIR = os.environ.get("PERSIST_DIR", "data/chroma_store_e5_new")

client = chromadb.PersistentClient(path=PERSIST_DIR)
col = client.get_collection("political_collection")

print(f"Total vectors: {col.count()}")
print()

# --- Test 1: What top_keys exist? ---
print("=== Test 1: top_key values in store ===")
results = col.get(
    where={"type": {"$eq": "speech"}},
    include=["metadatas"],
    limit=1000,
)
top_keys = [m.get("top_key", "") for m in results["metadatas"]]
top_key_counts = Counter(top_keys)
print(f"Unique top_keys: {len(top_key_counts)}")
for key, count in sorted(top_key_counts.items()):
    print(f"  {key!r:40s}  {count} chunks")
print()

# --- Test 2: Filter by a specific top_key ---
if top_key_counts:
    sample_key = next(k for k in top_key_counts if k)
    print(f"=== Test 2: Filter by top_key={sample_key!r} ===")
    r2 = col.get(
        where={"$and": [
            {"type": {"$eq": "speech"}},
            {"top_key": {"$eq": sample_key}},
        ]},
        include=["metadatas", "documents"],
        limit=5,
    )
    print(f"Found {len(r2['ids'])} chunks")
    for meta, doc in zip(r2["metadatas"], r2["documents"]):
        print(f"  party={meta.get('party')}  date={meta.get('date')}  id={meta.get('id')}")
        print(f"  text: {doc[:80]}...")
    print()

# --- Test 3: Filter by party + top_key ---
if top_key_counts:
    print(f"=== Test 3: Filter by party=GRÜNEN + top_key={sample_key!r} ===")
    r3 = col.get(
        where={"$and": [
            {"type": {"$eq": "speech"}},
            {"party": {"$eq": "GRÜNEN"}},
            {"top_key": {"$eq": sample_key}},
        ]},
        include=["metadatas"],
        limit=20,
    )
    print(f"Found {len(r3['ids'])} chunks")
    print()

# --- Test 4: Manifesto entries have no top_key ---
print("=== Test 4: Manifesto entries ===")
r4 = col.get(
    where={"type": {"$eq": "manifesto"}},
    include=["metadatas"],
    limit=5,
)
print(f"Found {len(r4['ids'])} manifesto chunks (limit 5)")
for meta in r4["metadatas"]:
    print(f"  party={meta.get('party')}  top_key={meta.get('top_key')!r}")
