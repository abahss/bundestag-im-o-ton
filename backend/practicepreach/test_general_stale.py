"""Old document-less summaries read '**Eingebracht von:** nicht erkennbar'. They are
stale and regenerate on the next hit / prewarm — but nothing else may be touched: not the
63 summaries with a real 'Eingebracht von', not the Haushaltswoche overview prose that is
stored under the same `general` key."""
import json
from types import SimpleNamespace

import pytest

from practicepreach import fast
from practicepreach.rag import general_is_stale

UNATTRIBUTED = "**Eingebracht von:** nicht erkennbar\n\n**Im Kern:** Die Debatte befasst sich mit X.\n\n- A"
NAMED = "**Eingebracht von:** SPD, CDU/CSU\n\n**Im Kern:** Ein Gesetz.\n\n- A"
VERLAUF = "**Verlauf:** Die Debatte war kontrovers.\n\n- A"
HAUSHALTSWOCHE = "Die Haushaltswoche war von mehreren übergreifenden Konfliktlinien geprägt."


@pytest.mark.parametrize("text", [UNATTRIBUTED, "  \n" + UNATTRIBUTED])
@pytest.mark.parametrize("has_drs,force", [(False, False), (True, False), (False, True)])
def test_unattributed_old_summary_is_stale_on_every_path(text, has_drs, force):
    assert general_is_stale(text, has_drs, force) is True


def test_summaries_that_name_a_proposer_are_not_touched_without_a_document():
    assert general_is_stale(NAMED, False, False) is False


def test_haushaltswoche_overview_is_never_stale():
    assert general_is_stale(HAUSHALTSWOCHE, False, False) is False


def test_current_verlauf_summary_is_not_stale():
    assert general_is_stale(VERLAUF, False, False) is False
    assert general_is_stale(VERLAUF, True, True) is False


def test_empty_cache_entry_is_not_stale_it_is_missing():
    assert general_is_stale("", True, True) is False


@pytest.mark.parametrize("has_drs,force", [(True, False), (False, True)])
def test_existing_rule_pre_variante_d_summary_of_a_document_backed_tops_is_stale(has_drs, force):
    # characterisation of the rule that already existed in fast.py and updater.py
    assert general_is_stale(NAMED, has_drs, force) is True


@pytest.fixture
def tops_file(tmp_path, monkeypatch):
    tops = {
        "98_Tagesordnungspunkt 3": {"top_id": "Tagesordnungspunkt 3", "title": "Hamas", "drucksache": ""},
        "90_Tagesordnungspunkt 1": {"top_id": "Tagesordnungspunkt 1", "drucksache": "21/1", "drucksache_verified": True},
    }
    path = tmp_path / "tops.json"
    path.write_text(json.dumps(tops))
    monkeypatch.setattr(fast, "TOPS_JSON", path)


def test_summaries_endpoint_regenerates_unattributed_summaries(tops_file):
    assert fast._general_needs_regen("98_Tagesordnungspunkt 3", UNATTRIBUTED) is True


def test_summaries_endpoint_leaves_named_and_current_ones_alone(tops_file):
    assert fast._general_needs_regen("98_Tagesordnungspunkt 3", NAMED) is False
    assert fast._general_needs_regen("98_Tagesordnungspunkt 3", VERLAUF) is False
    assert fast._general_needs_regen("91_Haushaltswoche", HAUSHALTSWOCHE) is False


def test_summaries_endpoint_keeps_the_existing_document_rule(tops_file):
    assert fast._general_needs_regen("90_Tagesordnungspunkt 1", NAMED) is True


def test_generate_general_summary_passes_the_title(tops_file, monkeypatch):
    seen = {}

    class FakeRag:
        def summarize_topic_general(self, *args, **kwargs):
            seen["args"], seen["kwargs"] = args, kwargs
            return "**Verlauf:** x"

    fast._generate_general_summary(FakeRag(), "98_Tagesordnungspunkt 3")
    passed = list(seen["args"]) + list(seen["kwargs"].values())
    assert "Hamas" in passed
