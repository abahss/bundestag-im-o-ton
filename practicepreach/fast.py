import json
import logging
import asyncio
import threading
from datetime import datetime, date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import smtplib
import subprocess
from email.mime.text import MIMEText

from practicepreach import constants
from practicepreach.params import LOG_LEVEL, UPDATE_SECRET_TOKEN, GCS_CHROMA_PATH, GMAIL_USER, GMAIL_APP_PASSWORD
from practicepreach.rag import Rag
from practicepreach.updater import run_update

TOPS_JSON = Path("data/tops.json")
SUMMARIES_CACHE = Path("data/summaries_cache.json")
FEEDBACK_FILE = Path("data/feedback.json")
_cache_lock = threading.Lock()
_feedback_lock = threading.Lock()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    # e.g. connect to DB, load ML model, init client, create resources

    app.state.rag = Rag()

    # Update ChromaDB with recent speeches in the background so the API is
    # immediately available while new data is being embedded.
    # threading.Thread(
    #     target=run_update,
    #     args=(app.state.rag,),
    #     daemon=True,
    #     name="speech-updater",
    # ).start()

    logger.info("Starting is complete.")
    yield

    # e.g. close DB connection, free resources
    logger.info("Shutting down...")
    app.state.rag.shutdown()

app = FastAPI(lifespan=lifespan)

# Allowing all middleware is optional, but good practice for dev purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def root():
    return {'greeting': 'PracticePreach FastAPI is running!'}

@app.get("/parameters")
def get_parameters():
    return {
        'political_topics': constants.POLITICAL_TOPICS,
        'bundestag_wahlperiode': constants.BUNDESTAG_WAHLPERIODE,
    }

MAX_REFRESHES = 5

def _read_cache() -> dict:
    if SUMMARIES_CACHE.exists():
        return json.loads(SUMMARIES_CACHE.read_text())
    return {}

def _split_summary(text: str) -> tuple[str, str]:
    """Split LLM output into (kernposition_line, quotes_block)."""
    kernposition = ""
    quote_lines = []
    for line in text.strip().splitlines():
        s = line.strip()
        if s.startswith("**Kernposition:**"):
            kernposition = s
        elif s.startswith('*"') or s.startswith('"'):
            quote_lines.append(line)
    return kernposition, "\n".join(quote_lines)

def _combine_summary(kernposition: str, quotes_text: str) -> str:
    parts = [p for p in [kernposition, quotes_text] if p.strip()]
    return "\n\n".join(parts)

def _normalize_entry(entry) -> dict:
    """Normalize legacy cache entries (plain string or old {summary, count}) to {kernposition, quotes_text, count}."""
    if isinstance(entry, str):
        kp, qt = _split_summary(entry)
        return {"kernposition": kp, "quotes_text": qt, "count": 0}
    if entry and "summary" in entry and "kernposition" not in entry:
        kp, qt = _split_summary(entry["summary"])
        return {"kernposition": kp, "quotes_text": qt, "count": entry.get("count", 0)}
    return entry or {}

def _write_cache(top_key: str, party: str, kernposition: str, quotes_text: str, count: int):
    with _cache_lock:
        cache = _read_cache()
        cache.setdefault(top_key, {})[party] = {
            "kernposition": kernposition,
            "quotes_text": quotes_text,
            "count": count,
        }
        SUMMARIES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))

def _load_tops_with_active_keys(rag: Rag):
    if not TOPS_JSON.exists():
        raise HTTPException(status_code=404, detail="tops.json not found — run build_tops_json.py first")
    tops = json.loads(TOPS_JSON.read_text())
    col = rag.vector_store._collection
    result = col.get(where={"type": {"$eq": "speech"}}, include=["metadatas"])
    active_keys = {m["top_key"] for m in result["metadatas"] if m.get("top_key")}

    # Derive PDF URL per session from speech IDs (format: ID{wp}{session_padded}...)
    session_pdf_urls = {}
    for m in result["metadatas"]:
        sid = m.get("id", "")
        if sid.startswith("ID") and len(sid) >= 8:
            wp = sid[2:4]
            session = sid[4:6].zfill(3)
            session_pdf_urls[sid[4:6]] = f"https://dserver.bundestag.de/btp/{wp}/{wp}{session}.pdf"

    return tops, active_keys, session_pdf_urls

@app.get("/topics")
def get_topics():
    rag: Rag = app.state.rag
    tops, active_keys, _ = _load_tops_with_active_keys(rag)
    return sorted(
        [t for t in tops.values() if t["top_key"] in active_keys],
        key=lambda x: (x["date"], x["top_id"]),
    )

@app.get("/all_topics")
def get_all_topics():
    rag: Rag = app.state.rag
    tops, active_keys, session_pdf_urls = _load_tops_with_active_keys(rag)
    result = []
    for t in sorted(tops.values(), key=lambda x: (x["date"], x["top_id"])):
        pdf_url = session_pdf_urls.get(t["session"], "")
        result.append({**t, "active": t["top_key"] in active_keys, "pdf_url": pdf_url})
    return result

@app.get("/summaries")
async def get_summaries(top_key: str):
    rag: Rag = app.state.rag

    raw_cache = _read_cache().get(top_key, {})
    cached = {p: _normalize_entry(e) for p, e in raw_cache.items()}

    # General summary first — party prompts use it to avoid repetition
    general_text = raw_cache.get("general", {}).get("summary", "") if isinstance(raw_cache.get("general"), dict) else ""
    if not general_text:
        subtitle = ""
        if TOPS_JSON.exists():
            tops = json.loads(TOPS_JSON.read_text())
            subtitle = tops.get(top_key, {}).get("subtitle", "")
        loop = asyncio.get_event_loop()
        general_text = await loop.run_in_executor(None, rag.summarize_topic_general, top_key, subtitle)
        if general_text:
            with _cache_lock:
                cache = _read_cache()
                cache.setdefault(top_key, {})["general"] = {"summary": general_text}
                SUMMARIES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))

    parties_to_generate = [p for p in constants.PARTIES_LIST if p not in cached]

    if parties_to_generate:
        async def process_party(party: str):
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(None, rag.summarize_by_top_key, top_key, party, general_text)
            return party, summary

        logger.info(f"Generating summaries for top_key={top_key}: {parties_to_generate}")
        results = await asyncio.gather(
            *[process_party(p) for p in parties_to_generate],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Party processing failed: {result}")
                continue
            party, summary = result
            if summary is not None:
                kp, qt = _split_summary(summary)
                _write_cache(top_key, party, kp, qt, 0)
                cached[party] = {"kernposition": kp, "quotes_text": qt, "count": 0}
    else:
        logger.info(f"Serving cached summaries for top_key={top_key}")

    response = {
        p: {
            "summary": _combine_summary(e.get("kernposition", ""), e.get("quotes_text", "")),
            "label": None,
            "refresh_count": e.get("count", 0),
        }
        for p, e in cached.items()
    }
    if general_text:
        response["general"] = {"summary": general_text}
    return response


@app.post("/summaries/refresh")
async def refresh_summary(top_key: str, party: str):
    rag: Rag = app.state.rag

    with _cache_lock:
        entry = _normalize_entry(_read_cache().get(top_key, {}).get(party))

    quotes_text = entry.get("quotes_text", "")
    loop = asyncio.get_event_loop()
    logger.info(f"Refreshing Kernposition for top_key={top_key}, party={party}")
    new_kernposition = await loop.run_in_executor(None, rag.regenerate_kernposition, top_key, party)
    return {
        "summary": _combine_summary(new_kernposition or entry.get("kernposition", ""), quotes_text),
        "label": None,
        "refresh_count": None,
    }

@app.post("/summaries/refresh-general")
async def refresh_general_summary(top_key: str):
    rag: Rag = app.state.rag
    subtitle = ""
    if TOPS_JSON.exists():
        tops = json.loads(TOPS_JSON.read_text())
        subtitle = tops.get(top_key, {}).get("subtitle", "")
    loop = asyncio.get_event_loop()
    general_text = await loop.run_in_executor(None, rag.summarize_topic_general, top_key, subtitle)
    if general_text is None:
        raise HTTPException(status_code=404, detail="Keine Redebeiträge gefunden.")
    return {"summary": general_text}


class FeedbackBody(BaseModel):
    text: str
    email: str = ""
    from_url: str = ""

@app.post("/feedback")
async def submit_feedback(body: FeedbackBody):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text darf nicht leer sein.")

    entry = {
        "text": body.text.strip(),
        "email": body.email.strip(),
        "from_url": body.from_url,
        "timestamp": datetime.utcnow().isoformat(),
    }

    with _feedback_lock:
        feedback = json.loads(FEEDBACK_FILE.read_text()) if FEEDBACK_FILE.exists() else []
        feedback.append(entry)
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        FEEDBACK_FILE.write_text(json.dumps(feedback, ensure_ascii=False, indent=2))

    if GMAIL_USER and GMAIL_APP_PASSWORD:
        try:
            body_lines = [
                f"Seite: {body.from_url or '—'}",
                f"E-Mail: {body.email or '—'}",
                "",
                body.text.strip(),
            ]
            msg = MIMEText("\n".join(body_lines), "plain", "utf-8")
            msg["Subject"] = "Neues Feedback – Bundestag im O-Ton"
            msg["From"] = GMAIL_USER
            msg["To"] = GMAIL_USER
            with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                smtp.starttls()
                smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                smtp.send_message(msg)
            logger.info("Feedback email sent")
        except Exception as e:
            logger.warning(f"Feedback email failed: {e}")

    logger.info(f"Feedback received from_url={body.from_url!r}")
    return {"status": "ok"}


def _str2date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


_update_running = False


@app.post("/admin/update")
async def admin_update(request: Request, since_date: str = None):
    """
    Trigger the update pipeline.
    Runs in a background thread so the API stays responsive.
    Protected by the UPDATE_SECRET_TOKEN env var (Bearer token).
    Optional query param: since_date (YYYY-MM-DD) to override auto-detected start date.
    """
    global _update_running

    if not UPDATE_SECRET_TOKEN:
        raise HTTPException(status_code=503, detail="UPDATE_SECRET_TOKEN not configured")
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {UPDATE_SECRET_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    if _update_running:
        return {"status": "already_running"}

    rag: Rag = app.state.rag

    def _do_update():
        global _update_running
        _update_running = True
        try:
            result = run_update(rag, since_date=since_date, prune_weeks=52)
            logger.info(f"Update complete: {result}")
        except Exception as exc:
            logger.error(f"Update failed: {exc}", exc_info=True)
        finally:
            _update_running = False

    threading.Thread(target=_do_update, daemon=True, name="weekly-updater").start()
    return {"status": "started"}
