"""Every summary prompt (general / fallback / party Kernposition / Drucksache)
carries the shared LESBARKEITS_REGELN block."""
from practicepreach.constants import LESBARKEITS_REGELN
from practicepreach.drucksache_summary import GEN_DRUCKSACHE
from practicepreach.rag import GEN_GENERAL_VARIANTE_D, Rag


class _FakeModel:
    def __init__(self):
        self.last_prompt = None

    def invoke(self, prompt):
        self.last_prompt = prompt.to_string() if hasattr(prompt, "to_string") else str(prompt)

        class _Resp:
            content = "**Kernposition:** Die Partei stimmt zu."

        return _Resp()


class _FakeCollection:
    def get(self, where=None, include=None):
        return {
            "documents": ["Redebeitrag der SPD.", "Redebeitrag der CDU/CSU."],
            "metadatas": [{"party": "SPD", "id": "1"}, {"party": "CDU/CSU", "id": "2"}],
        }


class _FakeVectorStore:
    _collection = _FakeCollection()


def _bare_rag():
    rag = Rag.__new__(Rag)
    rag.vector_store = _FakeVectorStore()
    rag.model = _FakeModel()
    return rag


def test_module_constants_carry_the_rules():
    assert LESBARKEITS_REGELN in GEN_GENERAL_VARIANTE_D
    assert LESBARKEITS_REGELN in GEN_DRUCKSACHE
    assert "15 Wörter" in GEN_GENERAL_VARIANTE_D
    assert "15 Wörter" in GEN_DRUCKSACHE


def test_general_summary_both_paths_carry_the_rules():
    rag = _bare_rag()
    rag.summarize_topic_general("s_TOP 1", "Beratung", "Drucksache 21/1: X.")
    assert LESBARKEITS_REGELN in rag.model.last_prompt  # Variante D

    rag.summarize_topic_general("s_TOP 1", "Aktuelle Stunde", "")
    assert LESBARKEITS_REGELN in rag.model.last_prompt  # fallback


def test_party_kernposition_prompts_carry_the_rules():
    rag = _bare_rag()
    rag._get_context_chunks = lambda tk, p: [("Ein Redebeitrag der SPD.", "ID1")]
    rag.summarize_by_top_key("s_TOP 1", "SPD")
    assert LESBARKEITS_REGELN in rag.model.last_prompt
    assert "15 Wörter" in rag.model.last_prompt

    rag._get_context = lambda tk, p: "Kontext."
    rag.regenerate_kernposition("s_TOP 1", "SPD")
    assert LESBARKEITS_REGELN in rag.model.last_prompt
