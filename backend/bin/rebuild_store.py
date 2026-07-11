"""
Download last week's Bundestag XMLs and rebuild ChromaDB from scratch.
Usage: uv run python bin/rebuild_store.py
"""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import NLTKTextSplitter
from langchain_community.document_loaders.csv_loader import CSVLoader

sys.path.insert(0, str(Path(__file__).parent))
from update_speeches import fetch_session_xml_urls, download_xmls, PARTY_NAME_MAP

load_dotenv()

SINCE_DATE = "2026-04-13"
XML_DIR = Path("data/xml_updates")
SPEECHES_CSV = Path("data/speeches_with_topkey.csv")
MANIFESTO_CSV = Path("data/data_manifestos_normalized.csv")
PERSIST_DIR = "data/chroma_store_e5_new"


def parse_xmls(xml_files: list[Path]) -> pd.DataFrame:
    from practicepreach.tools import process_bundestag_xml
    df = pd.DataFrame(columns=['type', 'date', 'id', 'party', 'top_key', 'text'])
    for xml_file in xml_files:
        print(f"  Parsing {xml_file.name}...")
        process_bundestag_xml(str(xml_file), df)
    df = df.reset_index(drop=True)
    df['party'] = df['party'].map(PARTY_NAME_MAP).fillna(df['party'])
    return df


def embed_csv(vector_store, csv_path: Path, metadata_cols: list):
    print(f"Loading {csv_path}...")
    loader = CSVLoader(file_path=str(csv_path), metadata_columns=metadata_cols)
    data = loader.load()
    for doc in data:
        date_str = doc.metadata.get("date", "")
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
            doc.metadata["date"] = int(dt.strftime("%Y%m%d"))
        except ValueError:
            pass
    text_splitter = NLTKTextSplitter(chunk_size=500, chunk_overlap=200)
    splits = text_splitter.split_documents(data)
    print(f"  Embedding {len(splits)} chunks...")
    for i in range(0, len(splits), 500):
        vector_store.add_documents(documents=splits[i:i + 500])
        print(f"  Batch {i // 500 + 1} done")


# --- Step 1: Download last week's XMLs ---
print(f"Fetching sessions since {SINCE_DATE}...")
session_urls = fetch_session_xml_urls(SINCE_DATE)
if not session_urls:
    print("No sessions found for last week. Exiting.")
    sys.exit(0)
xml_files = download_xmls(session_urls, XML_DIR)
print(f"Downloaded {len(xml_files)} XML files")

# --- Step 2: Parse XMLs → CSV + tops.json ---
print("Parsing XMLs...")
df = parse_xmls(xml_files)
print(f"Parsed {len(df)} speech rows")
df.to_csv(SPEECHES_CSV, index=False)
print(f"Saved {SPEECHES_CSV}")

import json
from practicepreach.tools import build_tops_lookup
tops = {}
for xml_file in xml_files:
    tops.update(build_tops_lookup(str(xml_file)))
tops_json = Path("data/tops.json")
tops_json.write_text(json.dumps(tops, ensure_ascii=False, indent=2))
print(f"Saved {tops_json} ({len(tops)} TOPs)")

# --- Step 3: Rebuild store ---
if os.path.exists(PERSIST_DIR):
    shutil.rmtree(PERSIST_DIR)
    print(f"Deleted existing store at {PERSIST_DIR}")

device = os.environ.get("TORCH_DEVICE", "cpu")
print(f"Loading embedding model on {device}...")
embeddings = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-large",
    model_kwargs={"device": device},
    encode_kwargs={"batch_size": 8},
)
vector_store = Chroma(
    collection_name="political_collection",
    persist_directory=PERSIST_DIR,
    embedding_function=embeddings,
)

embed_csv(vector_store, SPEECHES_CSV, ['date', 'id', 'party', 'type', 'top_key'])

# Manifestos: GRÜNEN only, no top_key
print("Loading manifestos (GRÜNEN only)...")
manifesto_loader = CSVLoader(file_path=str(MANIFESTO_CSV), metadata_columns=['date', 'id', 'party', 'type'])
manifesto_data = [doc for doc in manifesto_loader.load() if doc.metadata.get("party") == "GRÜNEN"]
print(f"  {len(manifesto_data)} manifesto rows")
for doc in manifesto_data:
    try:
        doc.metadata["date"] = int(datetime.strptime(doc.metadata["date"], "%d.%m.%Y").strftime("%Y%m%d"))
    except ValueError:
        pass
manifesto_splits = NLTKTextSplitter(chunk_size=500, chunk_overlap=200).split_documents(manifesto_data)
print(f"  Embedding {len(manifesto_splits)} chunks...")
for i in range(0, len(manifesto_splits), 500):
    vector_store.add_documents(documents=manifesto_splits[i:i + 500])

print(f"\nDone. Total vectors: {vector_store._collection.count()}")
