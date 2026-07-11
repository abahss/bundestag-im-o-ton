# Practice What You Preach

A RAG-based system that shows what German political parties actually say in the Bundestag — and compares it with what they promised in their election manifestos.

## What it does

For each agenda item (Tagesordnungspunkt) of a Bundestag session, the system generates a per-party summary of speeches, backed by exact quotes linked to the official plenary protocol PDF.

A Streamlit frontend displays the results as a navigable table of contents per session, with cards per party showing:
- **Kernposition** — one-sentence summary of the party's position
- **Zitate** — verbatim quotes with clickable links to the source PDF

### Coming soon: Manifesto comparison

A manifesto comparison feature is currently in development. It will show, per party and agenda item, what the party promised in their election manifesto — and whether their parliamentary speeches align with or contradict those promises.

## Architecture

```
Bundestag API (XML)
        │
        ▼
bin/update_speeches.py          — download, parse, normalize, embed new sessions
        │
        ▼
ChromaDB (local / external)     — speech chunks with metadata: party, date, top_key
        │
data/tops.json                  — TOP titles + subtitles extracted from XML
        │
        ▼
practicepreach/fast.py          — FastAPI backend
  GET /topics                   — TOPs with party speeches in store
  GET /all_topics               — all TOPs (active + inactive) with PDF link
  GET /summaries?top_key=...    — Gemini-generated summaries per party
        │
        ▼
practice-preach-ui/             — Streamlit frontend (separate repo)
```

## Tech stack

- **Python 3.12+** with [uv](https://docs.astral.sh/uv/)
- **ChromaDB** — vector store (embedded local or external HTTP)
- **HuggingFace** `intfloat/multilingual-e5-large` — multilingual embeddings (runs locally)
- **Google Gemini** `gemini-2.5-flash-lite` — summary generation
- **LangChain** — document loading, text splitting, ChromaDB integration
- **FastAPI** — REST API with async parallel party processing
- **Docker + Cloud Run** — deployment

## Project structure

```
practice-vs-preach/
├── practicepreach/
│   ├── fast.py                     # FastAPI app: /topics, /all_topics, /summaries
│   ├── rag.py                      # Vector store, retrieval, Gemini summarization
│   ├── tools.py                    # Bundestag XML parser, tops.json builder
│   ├── constants.py                # Party codes, Wahlperiode dates
│   ├── params.py                   # Environment variable configuration
│   ├── alignment.py                # LLM-based alignment analysis (manifesto comparison)
│   ├── cosine_sim.py               # Cosine similarity between speech/manifesto chunks
│   ├── wahlperiode_converter.py    # Date → Wahlperiode converter
│   ├── generate_manifesto_dataframe.py  # Manifesto texts → chunked CSV
│   └── test.py                     # ChromaDB filter tests
├── bin/
│   ├── update_speeches.py          # Fetch + parse + embed new Bundestag sessions
│   ├── build_tops_json.py          # Build data/tops.json from downloaded XMLs
│   ├── rebuild_store.py            # Rebuild ChromaDB from scratch
│   ├── reembed_manifestos.py       # Re-embed manifesto CSV into ChromaDB
│   └── download_manifestos.py      # Download manifestos from Manifesto Project API
├── data/
│   ├── chroma_store_e5_new/        # ChromaDB vector store
│   ├── tops.json                   # TOP metadata: title, subtitle, date, session
│   ├── speeches_with_topkey.csv    # Parsed speeches for current session(s)
│   ├── data_manifestos_normalized.csv  # Manifesto chunks (GRÜNEN)
│   ├── xml_updates/                # Downloaded XML plenary protocols
│   └── german_manifestos/          # Raw manifesto files from Manifesto Project
├── terraform/                      # GCP Cloud Run infrastructure
├── Dockerfile
└── pyproject.toml
```

## Setup

### Prerequisites

- Python 3.12+, `uv`
- Google AI Studio API key (for Gemini)
- Bundestag API key (free, from [dip.bundestag.de](https://dip.bundestag.de/))

### Install

```bash
git clone <repo-url>
cd practice-vs-preach
uv sync
```

Download NLTK tokenizer:

```python
import nltk
nltk.download('punkt_tab')
```

### Environment

Create a `.env` file:

```bash
GOOGLE_API_KEY=...
BUNDESTAG_API_KEY=...
PERSIST_DIR=data/chroma_store_e5_new
DATA_CSV=data/speeches_with_topkey.csv

# Optional: external ChromaDB (production)
# CHROMADB_HOST=...
# CHROMADB_PORT=8000

# Optional: GCS-backed store
# GCS_CHROMA_PATH=gs://bucket/chroma_store
```

## Data pipeline

### First-time setup

```bash
# 1. Download a session's speeches and embed into ChromaDB
uv run python bin/update_speeches.py --since 2026-04-15

# 2. Build tops.json (TOP titles for all downloaded XMLs)
uv run python bin/build_tops_json.py
```

### Keeping data up to date

```bash
# Fetches sessions since the last embedded date automatically
uv run python bin/update_speeches.py
```

### Full rebuild from scratch

```bash
uv run python bin/rebuild_store.py
```

## Running the API

```bash
uv run uvicorn practicepreach.fast:app --reload
```

## Frontend (Streamlit UI)

The UI lives in a separate repository: [practice-preach-ui](https://github.com/batch-2170-political-reality-check/practice-preach-ui)

### Setup

```bash
git clone git@github.com:batch-2170-political-reality-check/practice-preach-ui.git
cd practice-preach-ui
uv sync
```

### Run

Make sure the FastAPI backend is running on `localhost:8000`, then:

```bash
uv run streamlit run app.py
```

### What the UI shows

- **Home** — table of contents for the current session, with all agenda items listed. Items with party speeches are clickable; items without (e.g. only ministers spoke) are greyed out with a link to the plenary protocol PDF.
- **TOP pages** — one page per agenda item with party cards showing the Kernposition and verbatim quotes. Clicking a quote copies it to the clipboard and opens the source PDF.

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /topics` | TOPs that have party speech data in the store |
| `GET /all_topics` | All TOPs for available sessions, with `active` flag and PDF link |
| `GET /summaries?top_key=70_Tagesordnungspunkt 6` | Gemini summaries per party for a given TOP |

## Supported parties

`AFD`, `SPD`, `CDUCSU`, `GRÜNEN`, `LINKE`

## Deployment

```bash
# Docker
docker build -t practice-vs-preach .
docker run -p 8000:8000 --env-file .env practice-vs-preach

# Cloud Run (via Terraform)
cd terraform && terraform apply
```

## Data sources

- [Bundestag Open Data API](https://dip.bundestag.de/) — plenary protocols as XML
- [Manifesto Project](https://manifesto-project.wzb.eu/) — election manifestos
