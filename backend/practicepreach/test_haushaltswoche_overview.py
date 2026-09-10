"""summarize_haushaltswoche_overview: one cross-cutting summary built from the already
generated Einzelplan `general` summaries. No Chroma, no real LLM."""
import json

from practicepreach.rag import Rag
from practicepreach.updater import prewarm_haushaltswoche_overview


class _FakeModel:
    def __init__(self, content="Quer durch alle Ressortdebatten ...\n\nDie Vorlagen wurden überwiesen."):
        self.last_prompt = None
        self._content = content

    def invoke(self, prompt):
        self.last_prompt = prompt
        return type("_Resp", (), {"content": self._content})()


def _bare_rag(model=None):
    rag = Rag.__new__(Rag)
    rag.model = model or _FakeModel()
    return rag


_EP_SUMMARIES = [
    "**Verlauf:** Allgemeine Finanzdebatte. Streit um die Neuverschuldung.\n\n- Die AfD lehnt den Etat ab.",
    "**Verlauf:** Aussprache über den Verkehrsetat.\n\n- Sanierung vor Neubau.",
    "**Verlauf:** Aussprache über den Umweltetat.\n\n- Kürzungen bei Klimaanpassung kritisiert.",
]


def test_overview_is_built_from_the_einzelplan_summaries():
    rag = _bare_rag()

    out = rag.summarize_haushaltswoche_overview(_EP_SUMMARIES)

    assert out == "Quer durch alle Ressortdebatten ...\n\nDie Vorlagen wurden überwiesen."
    prompt = rag.model.last_prompt
    # every Einzelplan summary is fed in verbatim
    for s in _EP_SUMMARIES:
        assert s in prompt
    # it is a cross-cutting brief, not a per-TOP one
    assert "Querschnitt" in prompt or "quer" in prompt.lower()
    # no quoting, stays neutral — same house rules as the other general prompts
    assert "Anführungszeichen" in prompt


def test_overview_returns_none_without_input_summaries():
    rag = _bare_rag()
    assert rag.summarize_haushaltswoche_overview([]) is None


def test_overview_strips_surrounding_whitespace():
    rag = _bare_rag(_FakeModel(content="  \n Überblickstext \n "))
    assert rag.summarize_haushaltswoche_overview(_EP_SUMMARIES) == "Überblickstext"


# --- prewarm step: hub `general` summary from the cached Einzelplan generals -----------

def _hub_tops():
    return {
        "91_Haushaltswoche": {
            "top_key": "91_Haushaltswoche", "top_id": "Haushaltswoche",
            "einzelplaene": ["91_Einzelplan 08", "91_Einzelplan 12", "91_Einzelplan 16"],
            "einbringung": "91_Tagesordnungspunkt 3",
        },
        "91_Einzelplan 08": {"top_id": "Einzelplan 08"},
        "91_Einzelplan 12": {"top_id": "Einzelplan 12"},
        "91_Einzelplan 16": {"top_id": "Einzelplan 16"},
    }


def _seed_cache(tmp_path, monkeypatch, cache):
    import practicepreach.updater as u
    f = tmp_path / "summaries_cache.json"
    f.write_text(json.dumps(cache), encoding="utf-8")
    monkeypatch.setattr(u, "SUMMARIES_CACHE", f)
    return f


def test_prewarm_builds_hub_overview_from_cached_einzelplan_generals(tmp_path, monkeypatch):
    f = _seed_cache(tmp_path, monkeypatch, {
        "91_Einzelplan 08": {"general": {"summary": "**Verlauf:** Finanzdebatte."}},
        "91_Einzelplan 12": {"general": {"summary": "**Verlauf:** Verkehrsetat."}},
        "91_Einzelplan 16": {"general": {"summary": "**Verlauf:** Umweltetat."}},
    })
    rag = _bare_rag(_FakeModel(content="Querschnitt über die Woche."))

    stats = prewarm_haushaltswoche_overview(rag, _hub_tops())

    out = json.loads(f.read_text())
    assert out["91_Haushaltswoche"]["general"] == {"summary": "Querschnitt über die Woche."}
    assert stats["processed"] == 1
    for part in ("Finanzdebatte.", "Verkehrsetat.", "Umweltetat."):
        assert part in rag.model.last_prompt


def test_prewarm_skips_hub_that_already_has_an_overview(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch, {
        "91_Haushaltswoche": {"general": {"summary": "schon da"}},
        "91_Einzelplan 08": {"general": {"summary": "a"}},
        "91_Einzelplan 12": {"general": {"summary": "b"}},
        "91_Einzelplan 16": {"general": {"summary": "c"}},
    })
    rag = _bare_rag()

    stats = prewarm_haushaltswoche_overview(rag, _hub_tops())

    assert stats["processed"] == 0
    assert rag.model.last_prompt is None


def test_prewarm_skips_hub_with_too_few_einzelplan_generals(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch, {
        "91_Einzelplan 08": {"general": {"summary": "only one so far"}},
    })
    rag = _bare_rag()

    stats = prewarm_haushaltswoche_overview(rag, _hub_tops())

    assert stats == {"processed": 0, "skipped": 1, "failed": 0}
    assert rag.model.last_prompt is None
