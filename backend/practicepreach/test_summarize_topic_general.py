"""summarize_topic_general picks the right prompt and injects the Drucksachen-context.
No Chroma, no real LLM — a bare Rag instance with fakes for vector_store and model."""
from practicepreach.rag import GEN_GENERAL_VARIANTE_D, Rag


class _FakeCollection:
    def get(self, where=None, include=None):
        return {
            "documents": ["Redebeitrag der SPD ...", "Redebeitrag der CDU/CSU ..."],
            "metadatas": [{"party": "SPD", "id": "1"}, {"party": "CDU/CSU", "id": "2"}],
        }


class _FakeVectorStore:
    _collection = _FakeCollection()


class _FakeModel:
    def __init__(self):
        self.last_prompt = None

    def invoke(self, prompt):
        self.last_prompt = prompt

        class _Resp:
            content = "**Verlauf:** Beratung.\n\n- Konflikt eins.\n"

        return _Resp()


def _bare_rag():
    rag = Rag.__new__(Rag)  # skip __init__ (no Chroma / no embeddings client)
    rag.vector_store = _FakeVectorStore()
    rag.model = _FakeModel()
    return rag


def test_variante_d_prompt_used_with_drucksache_context():
    rag = _bare_rag()
    ctx = "Drucksache 21/1: Die Fraktion will X.\n- Punkt A"
    out = rag.summarize_topic_general("s_TOP 1", "Beratung des Antrags", ctx)

    assert out.startswith("**Verlauf:**")
    prompt = rag.model.last_prompt
    assert "**Verlauf:**" in prompt and "AUSSPRACHE" in prompt  # the Variante-D prompt
    assert "**Eingebracht von:**" not in prompt      # not the fallback
    assert ctx in prompt                             # context injected verbatim
    assert "NICHT wiederholen" in prompt


def test_fallback_prompt_used_without_drucksache_context():
    rag = _bare_rag()
    rag.summarize_topic_general("s_TOP 1", "Aktuelle Stunde", "")

    prompt = rag.model.last_prompt
    assert "**Eingebracht von:**" in prompt          # the older format
    assert GEN_GENERAL_VARIANTE_D not in prompt


def test_force_verlauf_uses_variante_d_prompt_without_a_drucksache():
    """Ressort debates (Einzelplan blocks) have no bill — but the debate-only
    **Verlauf:** format still fits them better than **Eingebracht von:**."""
    rag = _bare_rag()
    rag.summarize_topic_general("91_Einzelplan 12", "Geschäftsbereich …", "", force_verlauf=True)

    prompt = rag.model.last_prompt
    assert GEN_GENERAL_VARIANTE_D in prompt
    assert "**Eingebracht von:**" not in prompt
    assert "NICHT wiederholen" not in prompt          # no Drucksache to not-repeat
    assert "Auszüge aus Plenardebatten" in prompt     # speech context still injected


def test_returns_none_when_no_speeches():
    rag = _bare_rag()
    rag.vector_store._collection.get = lambda where=None, include=None: {"documents": [], "metadatas": []}
    assert rag.summarize_topic_general("s_TOP 1", "", "x") is None
