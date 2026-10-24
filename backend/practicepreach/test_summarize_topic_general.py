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


def test_document_less_tops_get_the_debate_only_prompt_not_eingebracht_von():
    """Without a Drucksache there is nobody to attribute a proposal to — the old prompt
    forced an **Eingebracht von:** line, which came out as 'nicht erkennbar'."""
    rag = _bare_rag()
    out = rag.summarize_topic_general(
        "98_TOP 3", "", "", title="Drei Jahre nach dem Überfall der Hamas auf Israel"
    )

    assert out.startswith("**Verlauf:**")
    prompt = rag.model.last_prompt
    assert "**Eingebracht von:**" not in prompt
    assert "**Im Kern:**" not in prompt
    assert "**Verlauf:**" in prompt and "AUSSPRACHE" in prompt
    assert "Drei Jahre nach dem Überfall der Hamas auf Israel" in prompt   # the title is the only anchor
    assert "Auszüge aus Plenardebatten" in prompt


def test_document_less_prompt_does_not_let_the_model_guess_the_kind_of_debate():
    """14 of 35 document-less summaries claimed 'erste Lesung' (UN-Sicherheitsrat, Tag der
    Menschenrechte ...) because the template demanded a 'Art der Beratung'."""
    from practicepreach.rag import GEN_GENERAL_OHNE_VORLAGE

    assert "Art der Beratung und Grundtenor" not in GEN_GENERAL_OHNE_VORLAGE
    assert "Eine Lesung nie vermuten" in GEN_GENERAL_OHNE_VORLAGE
    assert GEN_GENERAL_OHNE_VORLAGE != GEN_GENERAL_VARIANTE_D


def test_variante_d_wording_is_untouched_for_document_backed_tops():
    # the 428 existing summaries were generated with this text; changing it changes them
    assert "Art der Beratung und Grundtenor der Aussprache" in GEN_GENERAL_VARIANTE_D
    assert "Eine Lesung nie vermuten" not in GEN_GENERAL_VARIANTE_D


def test_title_is_not_sent_for_document_backed_tops():
    rag = _bare_rag()
    rag.summarize_topic_general("s_TOP 1", "Beratung", "Drucksache 21/1: X", title="EIN-TITEL-XYZ")
    assert rag.model.last_prompt.startswith(GEN_GENERAL_VARIANTE_D)
    assert "EIN-TITEL-XYZ" not in rag.model.last_prompt


def test_title_is_not_repeated_when_it_equals_the_subtitle():
    # updater.py hands the title over as `subtitle` when a TOP has no subtitle
    rag = _bare_rag()
    rag.summarize_topic_general("s_TOP 1", "Gleicher Text", "", title="Gleicher Text")
    assert rag.model.last_prompt.count("Gleicher Text") == 1


def test_subtitle_is_kept_next_to_the_title():
    rag = _bare_rag()
    rag.summarize_topic_general("s_TOP 1", "auf Verlangen der Fraktion der AfD", "", title="Ein Titel")
    prompt = rag.model.last_prompt
    assert "Ein Titel" in prompt and "auf Verlangen der Fraktion der AfD" in prompt


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
