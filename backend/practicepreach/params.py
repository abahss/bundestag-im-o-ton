from dotenv import load_dotenv
import os

def require_env(*names: str):
    """Ensure required environment variables are set."""
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

load_dotenv(override=True)

require_env("GOOGLE_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # langchain_google_genai
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Configuration for two deployment modes:
# 1. Local dev: Embedded Chroma with local CSV data (requires PERSIST_DIR, DATA_CSV)
# 2. Deployed: External ChromaDB VM (requires CHROMADB_HOST, no DATA_CSV needed)

BUNDESTAG_API_KEY = os.environ.get("BUNDESTAG_API_KEY")
UPDATE_SECRET_TOKEN = os.environ.get("UPDATE_SECRET_TOKEN")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
CHROMADB_HOST = os.environ.get("CHROMADB_HOST")  # For external ChromaDB (deployed)
CHROMADB_PORT = os.environ.get("CHROMADB_PORT", "8000")  # Default port
PERSIST_DIR = os.environ.get("PERSIST_DIR")  # For embedded Chroma (local dev)
DATA_CSV = os.environ.get("DATA_CSV")  # Only needed for local dev
GCS_CHROMA_PATH = os.environ.get("GCS_CHROMA_PATH")  # e.g. gs://bucket/data/chroma_store_e5

USE_EXTERNAL_CHROMA = bool(CHROMADB_HOST)
USE_GCS_CHROMA = bool(GCS_CHROMA_PATH) and not USE_EXTERNAL_CHROMA

if USE_EXTERNAL_CHROMA:
    print(f"Using external ChromaDB at {CHROMADB_HOST}:{CHROMADB_PORT}")
elif USE_GCS_CHROMA:
    print(f"Using GCS-backed Chroma: {GCS_CHROMA_PATH}")
else:
    if not PERSIST_DIR:
        raise RuntimeError("PERSIST_DIR is required for local dev setup (embedded Chroma mode)")
    if not DATA_CSV:
        raise RuntimeError("DATA_CSV is required for local dev setup (embedded Chroma mode)")
    print(f"Using embedded Chroma storage: {PERSIST_DIR}")
