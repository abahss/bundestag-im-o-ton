import logging
import os
import re
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

GCS_LOCAL_CACHE = "/tmp/chroma_store_gemini"

logger = logging.getLogger(__name__)

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
        import shutil
        if os.path.exists(local_path):
            shutil.rmtree(local_path)
        result = subprocess.run(
            ["gsutil", "-m", "cp", "-r", gcs_path, os.path.dirname(local_path)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"GCS download failed: {result.stderr}")
        logger.info(f"Downloaded Chroma store to {local_path}")

        # Download tops.json alongside the vector store
        gcs_base = gcs_path.rsplit('/', 1)[0]
        from pathlib import Path
        tops_local = Path("data/tops.json")
        tops_local.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["gsutil", "cp", f"{gcs_base}/tops.json", str(tops_local)],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            logger.info("Downloaded tops.json from GCS")
        else:
            logger.warning("tops.json not in GCS yet — will be created on first update")

        # Download summaries_cache.json
        cache_local = Path("data/summaries_cache.json")
        r2 = subprocess.run(
            ["gsutil", "cp", f"{gcs_base}/summaries_cache.json", str(cache_local)],
            capture_output=True, text=True
        )
        if r2.returncode == 0:
            logger.info("Downloaded summaries_cache.json from GCS")
        else:
            logger.warning("summaries_cache.json not in GCS yet — starting with empty cache")

        # Download abstimmungen.json
        abstimmungen_local = Path("data/abstimmungen.json")
        r3 = subprocess.run(
            ["gsutil", "cp", f"{gcs_base}/abstimmungen.json", str(abstimmungen_local)],
            capture_output=True, text=True
        )
        if r3.returncode == 0:
            logger.info("Downloaded abstimmungen.json from GCS")
        else:
            logger.warning("abstimmungen.json not in GCS yet — will be created on first update")

    def upload_to_gcs(self, gcs_path: str = None):
        """Upload local Chroma cache + tops.json back to GCS after an update."""
        import subprocess
        from pathlib import Path
        target = gcs_path or GCS_CHROMA_PATH

        result = subprocess.run(
            ["gsutil", "-m", "cp", "-r", GCS_LOCAL_CACHE, os.path.dirname(target)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"GCS upload failed: {result.stderr}")
        logger.info(f"Uploaded Chroma store to {target}")

        tops_local = Path("data/tops.json")
        if tops_local.exists():
            gcs_base = target.rsplit('/', 1)[0]
            r = subprocess.run(
                ["gsutil", "cp", str(tops_local), f"{gcs_base}/tops.json"],
                capture_output=True, text=True
            )
            if r.returncode == 0:
                logger.info(f"Uploaded tops.json to {gcs_base}/tops.json")
            else:
                logger.warning(f"Failed to upload tops.json: {r.stderr}")

        cache_local = Path("data/summaries_cache.json")
        if cache_local.exists():
            gcs_base = target.rsplit('/', 1)[0]
            r2 = subprocess.run(
                ["gsutil", "cp", str(cache_local), f"{gcs_base}/summaries_cache.json"],
                capture_output=True, text=True
            )
            if r2.returncode == 0:
                logger.info(f"Uploaded summaries_cache.json to {gcs_base}/summaries_cache.json")
            else:
                logger.warning(f"Failed to upload summaries_cache.json: {r2.stderr}")

        abstimmungen_local = Path("data/abstimmungen.json")
        if abstimmungen_local.exists():
            gcs_base = target.rsplit('/', 1)[0]
            r3 = subprocess.run(
                ["gsutil", "cp", str(abstimmungen_local), f"{gcs_base}/abstimmungen.json"],
                capture_output=True, text=True
            )
            if r3.returncode == 0:
                logger.info(f"Uploaded abstimmungen.json to {gcs_base}/abstimmungen.json")
            else:
                logger.warning(f"Failed to upload abstimmungen.json: {r3.stderr}")

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

    @staticmethod
    def _normalize_for_match(text: str) -> str:
        text = text.replace("„", '"').replace("“", '"').replace("‘", "'").replace("’", "'")
        return re.sub(r"\s+", " ", text).strip().lower()

    def _attach_citation_ids(self, text: str, chunks: list[tuple[str, str]]) -> str:
        """Replace whatever ID the LLM echoed after each quote with the real ID of
        the chunk that quote actually came from, found by substring match — never
        trust the model to copy the ID correctly. Drops the tag if no chunk matches
        (e.g. the quote was paraphrased rather than exact)."""
        normalized_chunks = [(self._normalize_for_match(doc), cid) for doc, cid in chunks]
        out_lines = []
        for line in text.splitlines():
            m = re.match(r'^(\*"(.+)"\*)\s*(?:\[[^\]]*\])?\s*$', line.strip())
            if not m:
                out_lines.append(line)
                continue
            quote_part, quote_text = m.group(1), m.group(2)
            needle = self._normalize_for_match(quote_text)
            found_id = next((cid for norm_doc, cid in normalized_chunks if needle in norm_doc), None)
            out_lines.append(f"{quote_part} [{found_id}]" if found_id else quote_part)
        return "\n".join(out_lines)

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
Verständlichkeitsregel: Jedes Zitat muss für sich allein verständlich sein, auch ohne den umgebenden Text zu kennen. Wähle KEIN Zitat, dessen Bezug unklar bleibt — z. B. Sätze, die nur mit einem nicht aufgelösten Pronomen ("es", "das", "sie", "dies") auf etwas vorher Gesagtes verweisen, oder die erkennbar mitten aus einem Gedankengang gerissen sind. Verständlichkeit hat immer Vorrang vor Zitatanzahl oder Abdeckung mehrerer Redebeiträge.{coverage_hint}{general_hint}
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
        return self._attach_citation_ids(answer.content, chunks)

    def summarize_topic_general(self, top_key: str, subtitle: str = "") -> str | None:
        """Generate a neutral, party-independent 2–3 sentence summary of a TOP."""
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

        response = self.model.invoke(
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
