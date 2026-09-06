"""Tests for the pure helpers in drucksache_summary (no network / no LLM)."""
from practicepreach.drucksache_summary import (
    TEXT_CAP,
    _parse_summary,
    _prepare_text,
    _restructure_gesetzentwurf,
    _strip_anschreiben,
    drucksache_context_for_top,
    public_view,
    top_verified_drucksache_numbers,
    verified_drucksache_numbers,
)

# A miniature Gesetzentwurf with the structure the restructuring keys off of:
# title, Vorblatt A-F, cover letter, article part, Begründung.
_GESETZ = (
    "Deutscher Bundestag Drucksache 21/9999\n"
    "21. Wahlperiode 01.01.2026\n"
    "Gesetzentwurf der Bundesregierung\n"
    "Entwurf eines Gesetzes zur Regelung von Testfällen\n"
    "A. Problem und Ziel\n"
    "Es gibt ein Problem, das gelöst werden soll. " + "Fülltext. " * 40 + "\n"
    "B. Lösung\n"
    "Die Lösung besteht aus mehreren Maßnahmen. " + "Fülltext. " * 40 + "\n"
    "C. Alternativen\n"
    "Keine. " + "Erwägung. " * 200 + "\n"
    "D. Haushaltsausgaben ohne Erfüllungsaufwand\n" + "Haushalt. " * 200 + "\n"
    "E. Erfüllungsaufwand\n" + "Aufwand. " * 400 + "\n"
    "F. Weitere Kosten\n" + "Kosten. " * 200 + "\n"
    "BUNDESREPUBLIK DEUTSCHLAND\n"
    "DER BUNDESKANZLER\n"
    "An die\nPräsidentin des\nDeutschen Bundestages\n"
    "Sehr geehrte Frau Bundestagspräsidentin,\n"
    "hiermit übersende ich den Entwurf. " + "Anschreiben. " * 20 + "\n"
    "Mit freundlichen Grüßen\n"
    "Max Mustermann\n"
    "Der Bundestag hat das folgende Gesetz beschlossen:\n"
    "Artikel 1\n"
    "In Paragraf 5 wird die Frist von drei auf sechs Monate verlängert. " + "Regelung. " * 3000 + "\n"
    "Artikel 2\n"
    "Dieses Gesetz tritt am 1. Januar 2027 in Kraft.\n"
    "Begründung\n"
    "A. Allgemeiner Teil\n" + "Ausführliche Begründung. " * 2000
)


def test_restructure_drops_cover_letter_cost_sections_and_begruendung():
    out = _restructure_gesetzentwurf(_GESETZ)
    assert out is not None
    assert "A. Problem und Ziel" in out
    assert "B. Lösung" in out
    assert "Artikel 1" in out and "1. Januar 2027" in out
    # cover letter, cost sections and Begründung are gone
    assert "Mit freundlichen Grüßen" not in out
    assert "DER BUNDESKANZLER" not in out
    assert "E. Erfüllungsaufwand" not in out
    assert "Ausführliche Begründung." not in out
    # and the result is much smaller than the raw text
    assert len(out) < len(_GESETZ) / 2


def test_restructure_returns_none_without_markers():
    assert _restructure_gesetzentwurf("Ein Antrag ohne jede Gesetzstruktur. " * 50) is None


def test_prepare_text_only_restructures_gesetzentwuerfe():
    _, info_gesetz = _prepare_text(_GESETZ, "Gesetzentwurf")
    assert info_gesetz["restructured"] is True

    antrag = "Deutscher Bundestag Drucksache 21/8888\nAntrag der Fraktion X\n" + "Wir fordern. " * 200
    prepared, info_antrag = _prepare_text(antrag, "Antrag")
    assert info_antrag["restructured"] is False
    assert prepared.startswith("Deutscher Bundestag")


def test_prepare_text_caps_and_reports_truncation():
    long_antrag = "Antrag\n" + "x" * (TEXT_CAP * 2)
    prepared, info = _prepare_text(long_antrag, "Antrag")
    assert len(prepared) == TEXT_CAP
    assert info["text_chars_original"] == len(long_antrag)
    assert info["text_chars_prepared"] > TEXT_CAP  # caller flags truncated from this


def test_strip_anschreiben_is_noop_without_block():
    t = "Antrag der Abgeordneten A, B und Fraktion X\nWir fordern etwas.\n"
    assert _strip_anschreiben(t) == t


def test_parse_summary_reads_im_kern_and_bullets():
    raw = (
        "**Im Kern:** Die Fraktion fordert etwas Konkretes.\n\n"
        "- Erste Forderung.\n"
        "- Zweite Forderung.\n"
        "* Dritte, mit Sternchen.\n"
    )
    im_kern, punkte = _parse_summary(raw)
    assert im_kern == "Die Fraktion fordert etwas Konkretes."
    assert punkte == ["Erste Forderung.", "Zweite Forderung.", "Dritte, mit Sternchen."]


def test_verified_drucksache_numbers_respects_flag_and_active_keys():
    tops = {
        "s_TOP 1": {"drucksache": "21/1", "drucksache_verified": True, "subtopics": []},
        "s_TOP 2": {"drucksache": "21/2", "drucksache_verified": False, "subtopics": []},
        "s_TOP 3": {"drucksache": "", "drucksache_verified": True, "subtopics": [
            {"drucksache": "21/3a", "drucksache_verified": True},
            {"drucksache": "21/3b", "drucksache_verified": False},
        ]},
        "old_TOP 9": {"drucksache": "20/9", "drucksache_verified": True, "subtopics": []},
    }
    assert verified_drucksache_numbers(tops) == {"21/1", "21/3a", "20/9"}
    assert verified_drucksache_numbers(tops, active_keys={"s_TOP 1", "s_TOP 3"}) == {"21/1", "21/3a"}


def test_top_verified_drucksache_numbers_dedupes_in_reading_order():
    top = {
        "drucksache": "21/1", "drucksache_verified": True,
        "subtopics": [
            {"drucksache": "21/2", "drucksache_verified": True},
            {"drucksache": "21/1", "drucksache_verified": True},  # same as top-level
            {"drucksache": "21/3", "drucksache_verified": False},
        ],
    }
    assert top_verified_drucksache_numbers(top) == ["21/1", "21/2"]


def test_drucksache_context_skips_missing_and_errored_entries():
    top = {
        "drucksache": "", "drucksache_verified": False,
        "subtopics": [
            {"drucksache": "21/10", "drucksache_verified": True},
            {"drucksache": "21/11", "drucksache_verified": True},
            {"drucksache": "21/12", "drucksache_verified": True},
        ],
    }
    cache = {
        "21/10": {"im_kern": "Zehn will X.", "punkte": ["Punkt A", "Punkt B"]},
        "21/11": {"nummer": "21/11", "error": "DIP hat keinen Volltext"},
        # 21/12 not in cache at all
    }
    ctx = drucksache_context_for_top(top, cache)
    assert "Drucksache 21/10: Zehn will X." in ctx
    assert "- Punkt A" in ctx
    assert "21/11" not in ctx and "21/12" not in ctx


def test_drucksache_context_empty_when_nothing_usable():
    top = {"drucksache": "21/9", "drucksache_verified": True, "subtopics": []}
    assert drucksache_context_for_top(top, {}) == ""


def test_public_view_drops_internal_fields():
    entry = {
        "nummer": "21/1", "typ": "Antrag", "urheber": "Fraktion X", "datum": "01.01.2026",
        "titel": "Titel", "pdf_url": "http://x", "im_kern": "Kern", "punkte": ["a"],
        "truncated": False, "generated_at": "2026-01-01T00:00:00+00:00",
        "raw": "**Im Kern:** ...", "prep": {"text_chars_original": 100},
    }
    view = public_view(entry)
    assert "raw" not in view and "prep" not in view
    assert view["nummer"] == "21/1" and view["punkte"] == ["a"]
