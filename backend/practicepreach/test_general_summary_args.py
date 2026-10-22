"""The offline paths (update prewarm, `update_speeches.py --purge-summaries`) must build the
same general summary for the same TOP. They used to disagree: the CLI never passed the
Drucksachen-context, so a document-backed TOP came out in the wrong format."""
import importlib.util
import json
from pathlib import Path

import pytest

from practicepreach import updater
from practicepreach.constants import PARTIES_LIST

DOC_TOP = {
    "top_id": "Tagesordnungspunkt 5", "title": "Gesetz zur Wärmewende", "subtitle": "Beratung des Antrags",
    "drucksache": "21/100", "drucksache_verified": True, "subtopics": [],
}
DRS_CACHE = {"21/100": {"nummer": "21/100", "im_kern": "Die Fraktion will die Wärmewende beschleunigen.", "punkte": ["Punkt A"]}}
PLAIN_TOP = {"top_id": "Tagesordnungspunkt 3", "title": "Hamas-Überfall", "subtitle": ""}
EINZELPLAN_TOP = {"top_id": "Einzelplan 12", "title": "Verkehr", "subtitle": "Geschäftsbereich X"}


def test_document_backed_top_gets_its_drucksachen_context():
    subtitle, ctx, force, title = updater.general_summary_args(DOC_TOP, DRS_CACHE)
    assert "Die Fraktion will die Wärmewende beschleunigen." in ctx
    assert (subtitle, force, title) == ("Beratung des Antrags", False, "Gesetz zur Wärmewende")


def test_document_less_top_falls_back_to_the_title_as_subtitle_and_has_no_context():
    assert updater.general_summary_args(PLAIN_TOP, {}) == ("Hamas-Überfall", "", False, "Hamas-Überfall")


def test_einzelplan_forces_the_verlauf_format():
    _, ctx, force, _ = updater.general_summary_args(EINZELPLAN_TOP, {})
    assert force is True and ctx == ""


def test_unsummarisable_drucksache_gives_no_context():
    top = {**DOC_TOP}
    assert updater.general_summary_args(top, {"21/100": {"error": "kein DIP-Text"}})[1] == ""


# ---- the CLI ------------------------------------------------------------------------
def _load_cli():
    path = Path(__file__).resolve().parent.parent / "bin" / "update_speeches.py"
    spec = importlib.util.spec_from_file_location("update_speeches_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeRag:
    def __init__(self):
        self.general_calls = []

    def summarize_topic_general(self, *args):
        self.general_calls.append(args)
        return "**Verlauf:** neu"

    def summarize_by_top_key(self, key, party, general_text):
        return f"Kernposition {party}"


@pytest.fixture
def cli(tmp_path, monkeypatch):
    mod = _load_cli()
    tops = {"90_TOP 5": DOC_TOP, "98_TOP 3": PLAIN_TOP, "91_Einzelplan 12": EINZELPLAN_TOP}
    (tmp_path / "tops.json").write_text(json.dumps(tops))
    (tmp_path / "drs.json").write_text(json.dumps(DRS_CACHE))
    monkeypatch.setattr(mod, "TOPS_JSON", tmp_path / "tops.json")
    monkeypatch.setattr(mod, "SUMMARIES_CACHE", tmp_path / "summaries.json")
    monkeypatch.setattr(mod, "DRUCKSACHE_SUMMARIES_CACHE", tmp_path / "drs.json")
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    return mod


def test_cli_regeneration_passes_the_drucksachen_context_like_the_prewarm(cli):
    rag = FakeRag()
    cli.regenerate_summaries(rag, ["90_TOP 5"])
    top_key, subtitle, ctx, force, title = rag.general_calls[0]
    assert top_key == "90_TOP 5" and subtitle == "Beratung des Antrags"
    assert "Die Fraktion will die Wärmewende beschleunigen." in ctx
    assert force is False and title == "Gesetz zur Wärmewende"


def test_cli_regeneration_of_a_document_less_top_has_no_context(cli):
    rag = FakeRag()
    cli.regenerate_summaries(rag, ["98_TOP 3"])
    assert rag.general_calls[0] == ("98_TOP 3", "Hamas-Überfall", "", False, "Hamas-Überfall")


def test_cli_regeneration_of_an_einzelplan_forces_the_verlauf_format(cli):
    rag = FakeRag()
    cli.regenerate_summaries(rag, ["91_Einzelplan 12"])
    assert rag.general_calls[0] == ("91_Einzelplan 12", "Geschäftsbereich X", "", True, "Verkehr")
