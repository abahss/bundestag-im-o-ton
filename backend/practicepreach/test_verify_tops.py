"""verify_tops: the importable core of bin/verify_tops_drucksachen.py — annotate every
canonical Drucksache in a tops dict with `drucksache_verified` (override → DIP cache →
live DIP cross-check). No network: fetch_dip is monkeypatched."""
import practicepreach.drucksache_verify as dv


def _top(**kw):
    return {"top_key": "T", "title": "", "subtitle": "", "drucksache": "", "subtopics": [], **kw}


def test_matching_drucksache_is_marked_verified(monkeypatch):
    monkeypatch.setattr(dv, "fetch_dip", lambda nr: {
        "titel": "Entwurf eines Haushaltsbegleitgesetzes 2027",
        "drucksachetyp": "Gesetzentwurf",
        "urheber": [{"titel": "Bundesregierung"}],
    })
    tops = {"91_Einzelplan 08": _top(
        top_key="91_Einzelplan 08",
        title="Entwurf eines Haushaltsbegleitgesetzes 2027",
        subtitle="Allgemeine Finanzdebatte",
        drucksache="21/7860",
    )}
    cache = {}

    stats = dv.verify_tops(tops, overrides={}, cache=cache, sleep=0)

    assert tops["91_Einzelplan 08"]["drucksache_verified"] is True
    assert cache["21/7860"]["verdict"] == "OK"
    assert stats["OK"] == 1


def test_mismatch_marks_unverified(monkeypatch):
    monkeypatch.setattr(dv, "fetch_dip", lambda nr: {
        "titel": "Ein völlig anderer Antrag zu einem anderen Thema",
        "drucksachetyp": "Antrag",
        "urheber": [{"titel": "Fraktion DIE LINKE"}],
    })
    tops = {"T": _top(
        title="Entwurf eines Gesetzes zur Stärkung der Tarifautonomie",
        subtitle="Erste Beratung des von der Bundesregierung eingebrachten Entwurfs eines Gesetzes zur Stärkung der Tarifautonomie",
        drucksache="21/1000",
    )}

    dv.verify_tops(tops, overrides={}, cache={}, sleep=0)

    assert tops["T"]["drucksache_verified"] is False


def test_override_wins_without_a_dip_call(monkeypatch):
    calls = []
    monkeypatch.setattr(dv, "fetch_dip", lambda nr: calls.append(nr))
    tops = {"T": _top(title="x", drucksache="21/1", drucksache_url="old")}

    dv.verify_tops(tops, overrides={"T|-": "21/2"}, cache={}, sleep=0)

    assert tops["T"]["drucksache"] == "21/2"
    assert tops["T"]["drucksache_verified"] is True
    assert calls == [], "an override is trusted without hitting DIP"


def test_dip_cache_hit_skips_the_network(monkeypatch):
    calls = []
    monkeypatch.setattr(dv, "fetch_dip", lambda nr: calls.append(nr))
    tops = {"T": _top(title="Titel A", subtitle="NaS A", drucksache="21/1")}
    cache = {"21/1": {"verdict": "OK", "ref_hash": dv._ref_hash("Titel A", "NaS A")}}

    dv.verify_tops(tops, overrides={}, cache=cache, sleep=0)

    assert tops["T"]["drucksache_verified"] is True
    assert calls == []


def test_hub_and_documentless_tops_are_left_alone(monkeypatch):
    monkeypatch.setattr(dv, "fetch_dip", lambda nr: 1 / 0)  # must never be called
    tops = {
        "91_Haushaltswoche": _top(top_key="91_Haushaltswoche", title="Bundeshaushalt 2027 – 1. Lesung"),
        "89_Zusatzpunkt 3": _top(top_key="89_Zusatzpunkt 3", title="Zur aktuellen politischen Lage"),
    }

    stats = dv.verify_tops(tops, overrides={}, cache={}, sleep=0)

    assert "drucksache_verified" not in tops["91_Haushaltswoche"]
    assert stats["OK"] == 0
