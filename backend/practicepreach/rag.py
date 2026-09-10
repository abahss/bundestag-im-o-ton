import logging
import os
import time

import chromadb
from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import NLTKTextSplitter

from datetime import datetime

from practicepreach.constants import *
from practicepreach.params import *
from practicepreach.quote_matching import attach_citation_ids

GCS_LOCAL_CACHE = "/tmp/chroma_store_gemini"

# Floor for a healthy vector store. The live corpus (sessions 46+) sits at ~49.5k;
# this only needs to sit well below that and well above a corruption signature
# (Chroma minting a fresh collection leaves it holding just the last batch,
# ~1-2k). Revisit if aggressive pruning (run_update's prune_weeks) is ever turned
# on for real — a legitimately small corpus would trip this.
MIN_HEALTHY_VECTORS = 20_000
# Fallback floor for data_level0.bin when the catalog has no dimension recorded.
MIN_SEGMENT_BIN_BYTES = 100_000
# A complete HNSW data_level0.bin is ~(dimension * 4 + graph-link bytes) per live
# element, i.e. very close to n_vectors * dimension * 4. Requiring at least half
# of that leaves 2x headroom for tombstoned rows / version differences while
# still catching a missing, empty, or half-downloaded segment file.
SEGMENT_BIN_BYTES_PER_VECTOR_FACTOR = 0.5

logger = logging.getLogger(__name__)


class StoreIntegrityError(RuntimeError):
    """A local Chroma store directory is missing or incomplete — refuse to use or
    upload it rather than propagate a partial download into production."""


def _assert_store_healthy(persist_dir: str, min_vectors: int = MIN_HEALTHY_VECTORS) -> int:
    """Raise StoreIntegrityError unless `persist_dir` holds a complete Chroma store:
    a readable chroma.sqlite3 catalog with at least `min_vectors` rows in `embeddings`,
    and a plausibly-sized data_level0.bin for every vector segment. Returns the count."""
    import sqlite3

    sqlite_path = os.path.join(persist_dir, "chroma.sqlite3")
    if not os.path.isfile(sqlite_path):
        raise StoreIntegrityError(f"no chroma.sqlite3 in {persist_dir}")

    try:
        con = sqlite3.connect(sqlite_path)
        try:
            n_vectors = con.execute("SELECT count(*) FROM embeddings").fetchone()[0]
            segments = con.execute(
                "SELECT s.id, c.dimension FROM segments s "
                "JOIN collections c ON c.id = s.collection WHERE s.scope = 'VECTOR'"
            ).fetchall()
        finally:
            con.close()
    except sqlite3.Error as e:
        # A truncated / half-written chroma.sqlite3 lands here — treat it as partial.
        raise StoreIntegrityError(f"chroma.sqlite3 in {persist_dir} is unreadable: {e}") from e

    if n_vectors < min_vectors:
        raise StoreIntegrityError(
            f"only {n_vectors} vectors in {persist_dir} (expected >= {min_vectors})"
        )

    for seg_id, dimension in segments:
        seg_bin = os.path.join(persist_dir, seg_id, "data_level0.bin")
        if not os.path.isfile(seg_bin):
            raise StoreIntegrityError(f"segment {seg_id} has no data_level0.bin in {persist_dir}")
        size = os.path.getsize(seg_bin)
        if dimension:
            floor = int(n_vectors * dimension * 4 * SEGMENT_BIN_BYTES_PER_VECTOR_FACTOR)
        else:
            floor = MIN_SEGMENT_BIN_BYTES
        if size < floor:
            raise StoreIntegrityError(
                f"segment {seg_id} data_level0.bin is {size} bytes, expected >= {floor}"
            )

    return n_vectors


def _download_chroma_store(
    gcs_path: str, local_path: str, *, attempts: int = 3,
    min_vectors: int = MIN_HEALTHY_VECTORS,
) -> int:
    """Mirror the store from GCS into `local_path`, verifying completeness after
    each attempt; wipe and retry on failure, raise if it never lands. Up to
    `attempts` full re-downloads, so keep it small enough for a Cloud Run cold
    start.

    Uses `gcloud storage rsync`, not `cp -r`: `cp -r <dir> <parent>` only nests
    into `<parent>/<dir>/` when <parent> is a real directory — when it is a
    symlink (macOS `/tmp` -> `private/tmp`) cp drops the files flat into the
    symlink target instead, leaving `local_path` empty. rsync always treats both
    endpoints as directories."""
    import shutil
    import subprocess

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        if os.path.exists(local_path):
            shutil.rmtree(local_path)
        os.makedirs(local_path, exist_ok=True)
        result = subprocess.run(
            ["gcloud", "storage", "rsync", "-r", gcs_path, local_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            last_error = RuntimeError(f"GCS download failed: {result.stderr}")
            logger.warning(f"Chroma download attempt {attempt}/{attempts} failed: {result.stderr}")
            continue
        try:
            n_vectors = _assert_store_healthy(local_path, min_vectors)
        except StoreIntegrityError as e:
            last_error = e
            logger.warning(f"Chroma download attempt {attempt}/{attempts} incomplete: {e}")
            continue
        logger.info(f"Downloaded Chroma store to {local_path} ({n_vectors} vectors)")
        return n_vectors

    logger.error(f"Chroma download failed after {attempts} attempts: {last_error}")
    raise last_error or RuntimeError(f"Chroma download did not run (attempts={attempts})")

# General-summary prompt used when the TOP has a separate Drucksachen-Zusammenfassung:
# the "was wird vorgeschlagen"-part lives there now, so this one covers only the debate
# ("Variante D", see memory project_drucksache_summary_plan). Document-less TOPs keep the
# older "**Eingebracht von:** / **Im Kern:**"-prompt below as a fallback.
GEN_GENERAL_VARIANTE_D = (
    "Du bist ein neutraler politischer Analyst. Fasse die parlamentarische AUSSPRACHE zu diesem "
    "Tagesordnungspunkt in RUND 90, höchstens 110 WÖRTERN zusammen.\n\n"
    "Die Zusammenfassung der zugrunde liegenden Drucksache(n) kennt der Leser bereits separat. Wiederhole "
    "NICHT, was vorgeschlagen wird oder welche Forderungen die Vorlage enthält. Beschreibe nur die Debatte: "
    "die zwei bis drei wichtigsten Konfliktlinien und, falls erkennbar, den Verfahrensstand am Ende.\n\n"
    "Antworte AUSSCHLIESSLICH in diesem Format:\n\n"
    "**Verlauf:** [ein Satz: Art der Beratung und Grundtenor der Aussprache]\n\n"
    "- [eine Konfliktlinie, ein Satz, höchstens 20 Wörter]\n\n"
    "- [eine Konfliktlinie, ein Satz, höchstens 20 Wörter]\n\n"
    "- [eine dritte Konfliktlinie oder der Verfahrensstand, ein Satz, höchstens 20 Wörter, optional]\n\n"
    "Regeln: Sachlich und parteiunabhängig. Kein Vorwissen. Kein einziges Anführungszeichen – gib alles in "
    "eigenen Worten wieder, zitiere keine Wortgruppen oder Begriffe aus den Reden, auch nicht zur Betonung. "
    "Beschreibe den Inhalt der Argumente, nicht Wortlaut oder Tonfall. Kein wertender Wortschatz "
    "(nicht \"chaotisch\", \"historisch\", \"gewürdigt\", \"endlich\", \"überfällig\") – beschreibe sachlich. "
    "Den Verfahrensstand nur nennen, wenn er im Kontext erkennbar ist – sonst diesen Punkt weglassen und "
    "NICHT erwähnen, dass er fehlt."
)


# Haushaltswoche overview: one cross-cutting brief built from the per-Einzelplan general
# summaries, sitting one level above the individual ressort debate. Plain prose, no
# header prefix — it renders where the Drucksachen-Zusammenfassung normally sits.
GEN_HAUSHALTSWOCHE_OVERVIEW = (
    "Du bist ein neutraler politischer Analyst. Dir liegen die Zusammenfassungen der "
    "einzelnen Ressortdebatten einer Haushaltswoche vor (1. Lesung des Bundeshaushalts). "
    "Schreibe daraus einen QUERSCHNITT über die ganze Woche in RUND 120, höchstens 160 "
    "WÖRTERN.\n\n"
    "Beschreibe die zwei bis vier Konfliktlinien, die sich durch MEHRERE Ressortdebatten "
    "ziehen — nicht die Einzelheiten eines einzelnen Etats. Nenne am Ende in einem Satz "
    "den Verfahrensstand (Überweisung in den Haushaltsausschuss, Schlussabstimmung in der "
    "2./3. Lesung), falls er aus den Vorlagen erkennbar ist.\n\n"
    "Format: Fließtext, zwei bis drei Absätze, getrennt durch eine Leerzeile. Keine "
    "Überschrift, keine Aufzählungszeichen.\n\n"
    "Regeln: Sachlich und parteiunabhängig. Kein Vorwissen über den Kontext hinaus. Kein "
    "einziges Anführungszeichen — gib alles in eigenen Worten wieder. Kein wertender "
    "Wortschatz (nicht \"chaotisch\", \"historisch\", \"überfällig\"). Beschreibe den "
    "Inhalt der Argumente, nicht Wortlaut oder Tonfall."
)


class Rag:
    def __init__(self):
        # Debugging
        if GOOGLE_API_KEY:
            masked_api_key = '*' * len(GOOGLE_API_KEY)
            logger.info(f"Masked API Key: {masked_api_key}")
        else:
            logger.info("API Key not found in environment variables.")

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=GOOGLE_API_KEY,
        )
        self.model = init_chat_model(
            "google_genai:gemini-2.5-flash",
            google_api_key=GOOGLE_API_KEY,
            thinking_budget=0,
            temperature=0,
        )

        # Initialize Chroma - either external, GCS-backed, or embedded
        if USE_EXTERNAL_CHROMA:
            logger.info(f"Connecting to external ChromaDB at {CHROMADB_HOST}:{CHROMADB_PORT}")
            chroma_client = chromadb.HttpClient(
                host=CHROMADB_HOST,
                port=int(CHROMADB_PORT)
            )
            self.vector_store = Chroma(
                client=chroma_client,
                collection_name="political_collection",
                embedding_function=self.embeddings,
            )
        elif USE_GCS_CHROMA:
            logger.info(f"Downloading Chroma store from GCS: {GCS_CHROMA_PATH}")
            self._download_from_gcs(GCS_CHROMA_PATH, GCS_LOCAL_CACHE)
            self.vector_store = Chroma(
                collection_name="political_collection",
                persist_directory=GCS_LOCAL_CACHE,
                embedding_function=self.embeddings,
            )
        else:
            logger.info(f"Using embedded Chroma at {PERSIST_DIR}")
            self.vector_store = Chroma(
                collection_name="political_collection",
                persist_directory=PERSIST_DIR,
                embedding_function=self.embeddings,
            )


        num_of_stored = self.vector_store._collection.count()
        logger.info(f"Vector store has {num_of_stored} vectores.")

    def _download_from_gcs(self, gcs_path: str, local_path: str):
        """Download Chroma store + tops.json from GCS to local cache directory."""
        import subprocess

        # rsync (not cp -r) into local_path, verify completeness, retry, and raise
        # rather than hand back an incomplete store. See _download_chroma_store.
        _download_chroma_store(gcs_path, local_path)

        # Download tops.json alongside the vector store
        gcs_base = gcs_path.rsplit('/', 1)[0]
        from pathlib import Path
        tops_local = Path("data/tops.json")
        tops_local.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["gcloud", "storage", "cp", f"{gcs_base}/tops.json", str(tops_local)],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            logger.info("Downloaded tops.json from GCS")
        else:
            logger.warning("tops.json not in GCS yet — will be created on first update")

        # Download summaries_cache.json
        cache_local = Path("data/summaries_cache.json")
        r2 = subprocess.run(
            ["gcloud", "storage", "cp", f"{gcs_base}/summaries_cache.json", str(cache_local)],
            capture_output=True, text=True
        )
        if r2.returncode == 0:
            logger.info("Downloaded summaries_cache.json from GCS")
        else:
            logger.warning("summaries_cache.json not in GCS yet — starting with empty cache")

        # Download drucksache_summaries.json
        drs_local = Path("data/drucksache_summaries.json")
        r_drs = subprocess.run(
            ["gcloud", "storage", "cp", f"{gcs_base}/drucksache_summaries.json", str(drs_local)],
            capture_output=True, text=True
        )
        if r_drs.returncode == 0:
            logger.info("Downloaded drucksache_summaries.json from GCS")
        else:
            logger.warning("drucksache_summaries.json not in GCS yet — starting with empty cache")

        # Download abstimmungen.json
        abstimmungen_local = Path("data/abstimmungen.json")
        r3 = subprocess.run(
            ["gcloud", "storage", "cp", f"{gcs_base}/abstimmungen.json", str(abstimmungen_local)],
            capture_output=True, text=True
        )
        if r3.returncode == 0:
            logger.info("Downloaded abstimmungen.json from GCS")
        else:
            logger.warning("abstimmungen.json not in GCS yet — will be created on first update")

        # Download search_index.json
        search_index_local = Path("data/search_index.json")
        r4 = subprocess.run(
            ["gcloud", "storage", "cp", f"{gcs_base}/search_index.json", str(search_index_local)],
            capture_output=True, text=True
        )
        if r4.returncode == 0:
            logger.info("Downloaded search_index.json from GCS")
        else:
            logger.warning("search_index.json not in GCS yet — will be created on next update")

    def upload_to_gcs(self, gcs_path: str = None):
        """Upload local Chroma cache + JSON sidecars back to GCS after an update."""
        import subprocess
        from pathlib import Path
        target = gcs_path or GCS_CHROMA_PATH
        gcs_base = target.rsplit('/', 1)[0]

        # Sidecars first — they are independent of vector-store integrity, so an
        # unhealthy store below must not cost us freshly generated summaries/tops.
        for name in ("tops.json", "summaries_cache.json", "drucksache_summaries.json",
                     "abstimmungen.json", "search_index.json"):
            local = Path("data") / name
            if not local.exists():
                continue
            r = subprocess.run(
                ["gcloud", "storage", "cp", str(local), f"{gcs_base}/{name}"],
                capture_output=True, text=True,
            )
            if r.returncode == 0:
                logger.info(f"Uploaded {name} to {gcs_base}/{name}")
            else:
                logger.warning(f"Failed to upload {name}: {r.stderr}")

        # Never push a partial store back to GCS — that is how a bad download
        # becomes production corruption. Raises after the sidecars, before the
        # store upload.
        _assert_store_healthy(GCS_LOCAL_CACHE)

        result = subprocess.run(
            ["gcloud", "storage", "cp", "-r", GCS_LOCAL_CACHE, os.path.dirname(target)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"GCS upload failed: {result.stderr}")
        logger.info(f"Uploaded Chroma store to {target}")

    def prune_speeches_before(self, cutoff_date: datetime) -> int:
        """Delete all speech chunks with date < cutoff_date from the vector store.
        Returns the number of chunks deleted.
        """
        cutoff_int = int(cutoff_date.strftime("%Y%m%d"))
        collection = self.vector_store._collection
        result = collection.get(
            where={"$and": [{"type": {"$eq": "speech"}}, {"date": {"$lt": cutoff_int}}]},
            include=[],
        )
        ids = result.get("ids", [])
        if ids:
            collection.delete(ids=ids)
            logger.info(f"Pruned {len(ids)} speech chunks older than {cutoff_date.date()}")
        else:
            logger.info(f"No speech chunks to prune before {cutoff_date.date()}")
        return len(ids)

    def get_num_of_vectors(self) -> int:
        """Get the number of vectors stored in the vector store."""
        return self.vector_store._collection.count()

    def add_to_vector_store(self, data_source):
        """Add new documents to the vector store from CSV file"""
        logger.info(f'Processing file: {data_source}')
        loader = CSVLoader(file_path=data_source, metadata_columns=['date','id','party','type','top_key'])
        data = loader.load()

        for doc in data:
            date_str = doc.metadata["date"]   # e.g. "27.11.2025"
            doc.metadata["date"] = self.convert_date_eu_to_int(date_str)

        text_splitter = NLTKTextSplitter(
            chunk_size=500,
            chunk_overlap=200
        )
        num_of_chunks = self.embed_and_store(data, text_splitter)
        return num_of_chunks

    def convert_date_eu_to_int(self,date_str: str) -> int:
        """Convert 'DD.MM.YYYY' → 20251127."""
        dt = datetime.strptime(date_str, "%d.%m.%Y")
        return int(dt.strftime("%Y%m%d"))


    def embed_and_store(self, doc, text_splitter, batch_size=100):
        """Split documents into chunks and store them in a vector store."""
        all_splits = text_splitter.split_documents(doc)
        num_of_splits = len(all_splits)
        logger.info(f"Total chunks to embed: {num_of_splits}")

        for i in range(0, num_of_splits, batch_size):
            batch = all_splits[i:i + batch_size]
            self.vector_store.add_documents(documents=batch)
            logger.info(f"Embedded {min(i + batch_size, num_of_splits)}/{num_of_splits} chunks")
            time.sleep(2)

        return num_of_splits

    def _get_context_chunks(self, top_key: str, party: str) -> list[tuple[str, str]] | None:
        """Return deduplicated (text, speech_id) pairs for top_key + party, or None if no chunks."""
        col = self.vector_store._collection
        results = col.get(
            where={"$and": [
                {"type": {"$eq": "speech"}},
                {"top_key": {"$eq": top_key}},
                {"party": {"$eq": party}},
            ]},
            include=["documents", "metadatas"],
        )
        if not results["documents"]:
            return None
        seen_docs = set()
        chunks = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            if doc not in seen_docs:
                seen_docs.add(doc)
                chunks.append((doc, meta.get("id", "unknown")))
        return chunks

    def _get_context(self, top_key: str, party: str) -> str | None:
        """Return deduplicated context string for top_key + party, or None if no chunks."""
        chunks = self._get_context_chunks(top_key, party)
        if chunks is None:
            return None
        return "\n\n".join(f"[{cid}] {doc}" for doc, cid in chunks)

    def summarize_by_top_key(self, top_key: str, party: str, general_context: str = "") -> str | None:
        """Fetch all speech chunks for a TOP + party and generate a summary."""
        chunks = self._get_context_chunks(top_key, party)
        if chunks is None:
            return None

        from collections import defaultdict
        chunks_by_speech: dict[str, list[str]] = defaultdict(list)
        for doc, cid in chunks:
            chunks_by_speech[cid].append(doc)
        context = "\n\n".join(
            f"=== Redebeitrag [{cid}] ===\n" + "\n\n".join(f"[{cid}] {doc}" for doc in docs)
            for cid, docs in chunks_by_speech.items()
        )

        general_hint = (
            f"\n\nAllgemeine Einleitung zum Tagesordnungspunkt (bereits bekannt): \"{general_context}\"\n"
            "Wiederhole diese Informationen nicht. Fokussiere ausschließlich auf die Position dieser Partei."
        ) if general_context else ""

        coverage_hint = (
            f"\n\nDer Kontext enthält {len(chunks_by_speech)} unterschiedliche Redebeiträge dieser Partei "
            "(jeweils markiert mit \"=== Redebeitrag [id] ===\"). Bevorzuge Zitate aus möglichst vielen "
            "verschiedenen Redebeiträgen, statt alle Zitate nur aus einem einzigen zu nehmen — aber nur, "
            "wenn ein Redebeitrag auch ein Zitat hergibt, das die Verständlichkeitsregel unten erfüllt."
        ) if len(chunks_by_speech) > 1 else ""

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", f"""Du bist ein politischer Analyst. Fasse zusammen, was die Partei zu diesem Tagesordnungspunkt gesagt hat.
Antworte AUSSCHLIESSLICH auf Basis des bereitgestellten Kontexts. Verwende kein Vorwissen.
Formuliere sachlich und ohne eigene Wertung, auch wenn der Kontext selbst wertend ist.
Wähle mindestens 3 wörtliche Zitate aus dem Kontext, die die Kernposition belegen. Verwende so viele wie nötig.
Verständlichkeitsregel: Jedes Zitat muss für sich allein verständlich sein, auch ohne den umgebenden Text zu kennen. Wähle KEIN Zitat, dessen Bezug unklar bleibt — z. B. Sätze, die nur mit einem nicht aufgelösten Pronomen ("es", "das", "sie", "dies") auf etwas vorher Gesagtes verweisen, oder die erkennbar mitten aus einem Gedankengang gerissen sind. Verständlichkeit hat immer Vorrang vor Zitatanzahl oder Abdeckung mehrerer Redebeiträge.
Wortlauttreue: "Exaktes wörtliches Zitat" heißt zeichengenau — kein einziges Wort darf verändert, ersetzt oder ergänzt werden, auch nicht, um ein Zitat verständlicher zu machen (z. B. ein Pronomen durch das Nomen ersetzen, ein einleitendes "Und"/"Aber" hinzufügen, einen Einschub weglassen). Wenn du dafür etwas am Anfang, in der Mitte oder am Ende weglassen musst, markiere GENAU diese Lücke mit "[...]" anstatt sie stillschweigend zu glätten — auch am Zitatanfang, wenn du z. B. mit "[...]" statt mit einem umformulierten Einleitewort beginnst. Ein Zitat mit "[...]" ist besser als ein exakt wirkendes Zitat, das in Wahrheit umformuliert wurde.{coverage_hint}{general_hint}
Formatiere deine Antwort genau so:
**Kernposition:** [ein Satz]

*"[exaktes wörtliches Zitat aus dem Kontext]"*
*"[exaktes wörtliches Zitat aus dem Kontext]"*
*"[exaktes wörtliches Zitat aus dem Kontext]"*
...

Gib nur das Zitat selbst an, keine ID oder Quellenangabe — das wird separat ergänzt."""),
            ("human", "Kontext: {context}"),
        ])
        prompt = prompt_template.invoke({"context": context})
        answer = self.model.invoke(prompt)
        return attach_citation_ids(answer.content, chunks)

    def summarize_topic_general(
        self, top_key: str, subtitle: str = "", drucksache_context: str = "",
        force_verlauf: bool = False,
    ) -> str | None:
        """Neutral, party-independent summary of a TOP.

        With `drucksache_context` (the TOP's Drucksachen-Zusammenfassung(en)) the summary
        covers only the debate ("Variante D", **Verlauf:** format) and is told not to
        repeat the proposal. `force_verlauf` picks the same debate-only format without a
        Drucksache — for TOPs that are a pure Aussprache (Einzelplan ressort debates).
        Otherwise — document-less TOPs — the older **Eingebracht von:** / **Im Kern:**
        format is used.
        """
        col = self.vector_store._collection
        results = col.get(
            where={"$and": [
                {"type": {"$eq": "speech"}},
                {"top_key": {"$eq": top_key}},
            ]},
            include=["documents", "metadatas"],
        )
        if not results["documents"]:
            return None

        from collections import defaultdict
        party_chunks: dict[str, list[str]] = defaultdict(list)
        seen_ids_per_party: dict[str, set] = defaultdict(set)
        for doc, meta in zip(results["documents"], results["metadatas"]):
            party = meta.get("party", "unknown")
            speech_id = meta.get("id", "")
            if speech_id not in seen_ids_per_party[party]:
                seen_ids_per_party[party].add(speech_id)
                party_chunks[party].append(doc)

        unique_chunks = []
        party_queues = {p: iter(chunks) for p, chunks in party_chunks.items()}
        while len(unique_chunks) < 15 and party_queues:
            exhausted = []
            for party, queue in party_queues.items():
                chunk = next(queue, None)
                if chunk is None:
                    exhausted.append(party)
                else:
                    unique_chunks.append(chunk)
                if len(unique_chunks) >= 15:
                    break
            for p in exhausted:
                del party_queues[p]

        context = "\n\n".join(unique_chunks)
        procedural = f"\nProzeduraler Kontext: {subtitle}" if subtitle else ""

        if drucksache_context or force_verlauf:
            drs_block = (
                f"\n\nZusammenfassung der zugrunde liegenden Drucksache(n) — NICHT wiederholen:\n"
                + drucksache_context
            ) if drucksache_context else ""
            prompt = (
                GEN_GENERAL_VARIANTE_D
                + drs_block
                + f"{procedural}\n\n"
                + f"Kontext (Auszüge aus Plenardebatten):\n{context}"
            )
        else:
            prompt = (
                "Du bist ein neutraler politischer Analyst. "
                "Analysiere den folgenden Tagesordnungspunkt und antworte AUSSCHLIESSLICH in diesem Format – keine Abweichungen:\n\n"
                "**Eingebracht von:** [Verwende ausschließlich einen oder mehrere dieser Namen (kommagetrennt): 'SPD', 'CDU/CSU', 'AfD', 'Bündnis 90/Die Grünen', 'Die Linke', 'Bundesregierung' – oder 'nicht erkennbar']\n\n"
                "**Im Kern:** [ein bis zwei Sätze: was wird konkret vorgeschlagen oder debattiert. Sätze simpel halten und so wenig wie möglich verschachteln.]\n\n"
                "- [Detail-Stichpunkt 1]\n\n"
                "- [Detail-Stichpunkt 2]\n\n"
                "- [Detail-Stichpunkt 3, optional]\n\n"
                "Bleibe sachlich und parteiunabhängig. Verwende kein Vorwissen außerhalb des Kontexts."
                f"{procedural}\n\n"
                f"Kontext (Auszüge aus Plenardebatten):\n{context}"
            )

        response = self.model.invoke(prompt)
        return response.content.strip()

    def summarize_haushaltswoche_overview(self, ep_summaries: list[str]) -> str | None:
        """Cross-cutting brief for a Haushaltswoche, built from the already generated
        per-Einzelplan `general` summaries. Returns None when given nothing to work from."""
        summaries = [s.strip() for s in ep_summaries if s and s.strip()]
        if not summaries:
            return None

        blocks = "\n\n".join(
            f"=== Ressortdebatte {i} ===\n{s}" for i, s in enumerate(summaries, 1)
        )
        prompt = f"{GEN_HAUSHALTSWOCHE_OVERVIEW}\n\nZusammenfassungen der Ressortdebatten:\n{blocks}"
        response = self.model.invoke(prompt)
        return response.content.strip()

    def regenerate_kernposition(self, top_key: str, party: str) -> str | None:
        """Re-generate only the Kernposition line from the same chunks."""
        context = self._get_context(top_key, party)
        if context is None:
            return None

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Du bist ein politischer Analyst. Fasse in einem Satz zusammen, was die Partei zu diesem Tagesordnungspunkt gesagt hat.
Antworte AUSSCHLIESSLICH auf Basis des bereitgestellten Kontexts. Verwende kein Vorwissen.
Formuliere sachlich und ohne eigene Wertung, auch wenn der Kontext selbst wertend ist.
Antworte NUR mit dieser einen Zeile:
**Kernposition:** [ein Satz]"""),
            ("human", "Kontext: {context}"),
        ])
        prompt = prompt_template.invoke({"context": context})
        answer = self.model.invoke(prompt)
        return answer.content.strip()

    def shutdown(self):
        """Clean up resources if needed."""
        pass
