"""prewarm_summaries regenerates only the stale `general` summaries and hands the TOP's
title to the document-less prompt."""
import json

import pytest

from practicepreach import updater
from practicepreach.constants import PARTIES_LIST

UNATTRIBUTED = "**Eingebracht von:** nicht erkennbar\n\n**Im Kern:** X.\n\n- A"
NAMED = "**Eingebracht von:** SPD\n\n**Im Kern:** Ein Gesetz.\n\n- A"
VERLAUF = "**Verlauf:** Kontrovers.\n\n- A"
HAUSHALTSWOCHE = "Die Haushaltswoche war von Konfliktlinien geprägt."
NEW = "**Verlauf:** Neu erzeugt.\n\n- A"


class FakeRag:
    def __init__(self):
        self.general_calls = []

    def summarize_topic_general(self, *args):
        self.general_calls.append(args)
        return NEW


def _top(title, **extra):
    return {"top_id": "Tagesordnungspunkt 3", "title": title, "subtitle": "", "drucksache": "", **extra}


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    path = tmp_path / "summaries_cache.json"
    monkeypatch.setattr(updater, "SUMMARIES_CACHE", path)
    monkeypatch.setattr(updater, "DRUCKSACHE_SUMMARIES_CACHE", tmp_path / "drs.json")
    monkeypatch.setattr(updater, "PREWARM_SLEEP_BETWEEN_TOPS", 0)
    return path


def _complete(general):
    entry = {p: {"kernposition": "k", "quotes_text": "q", "count": 0} for p in PARTIES_LIST}
    entry["general"] = {"summary": general}
    return entry


def test_only_unattributed_summaries_are_regenerated_and_get_the_title(cache_file):
    tops = {
        "98_TOP 3": _top("Drei Jahre nach dem Überfall der Hamas"),
        "98_TOP 4": _top("Ein Gesetz"),
        "98_TOP 5": _top("Schon aktuell"),
        "91_Haushaltswoche": {"top_id": "Haushaltswoche", "title": "Haushaltswoche"},
    }
    cache_file.write_text(json.dumps({
        "98_TOP 3": _complete(UNATTRIBUTED),
        "98_TOP 4": _complete(NAMED),
        "98_TOP 5": _complete(VERLAUF),
        "91_Haushaltswoche": {"general": {"summary": HAUSHALTSWOCHE}},
    }))
    rag = FakeRag()

    active = {k for k, t in tops.items() if t['top_id'] != 'Haushaltswoche'}  # hubs have no speeches
    result = updater.prewarm_summaries(rag, tops, active)

    assert [c[0] for c in rag.general_calls] == ["98_TOP 3"], rag.general_calls
    top_key, subtitle, drs_context, force_verlauf, title = rag.general_calls[0]
    assert title == "Drei Jahre nach dem Überfall der Hamas"
    assert drs_context == "" and force_verlauf is False

    cache = json.loads(cache_file.read_text())
    assert cache["98_TOP 3"]["general"]["summary"] == NEW
    assert cache["98_TOP 4"]["general"]["summary"] == NAMED          # named proposer: untouched
    assert cache["98_TOP 5"]["general"]["summary"] == VERLAUF
    assert cache["91_Haushaltswoche"]["general"]["summary"] == HAUSHALTSWOCHE
    assert result["processed"] == 1
