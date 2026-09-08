from practicepreach.search_index import build_search_index

TOPS = {
    "90_Tagesordnungspunkt 3": {
        "title": "Zweite und dritte Beratung",
        "subtitle": "Entwurf eines Wolfsgesetzes",
        "topic": "Wolf, Artenschutz",
        "drucksache": "21/5000",
        "drucksachen": [],
        "subtopics": [],
    },
    "90_Zusatzpunkt 8": {
        "title": "",
        "subtitle": "",
        "topic": "Sammel-TOP",
        "drucksache": "",
        "drucksachen": [],
        "subtopics": [
            {"title": "Antrag der Grünen", "nas": "Klimageld auszahlen", "drucksache": "21/6001", "drucksachen": []},
        ],
    },
}

SUMMARIES = {
    "90_Tagesordnungspunkt 3": {
        "general": {"summary": "**Verlauf:** Die Debatte war strittig."},
        "SPD": {"kernposition": "**Kernposition:** Die SPD stimmt zu.", "quotes_text": '*"Weidetierhaltung schützen."* [ID217001]'},
    },
}

DRUCKSACHEN = {
    "21/5000": {
        "titel": "Entwurf eines Gesetzes zur Regulierung des Wolfs",
        "im_kern": "Aufnahme des Wolfs ins Jagdrecht.",
        "punkte": ["Länder legen Abschussquoten fest.", "Monitoring wird ausgebaut."],
    },
    "21/6001": {"error": "Kein DIP-Text"},
}


def test_blob_covers_all_sources():
    idx = build_search_index(TOPS, SUMMARIES, DRUCKSACHEN)
    blob = idx["90_Tagesordnungspunkt 3"]
    assert "wolfsgesetzes" in blob
    assert "wolf, artenschutz" in blob
    assert "die debatte war strittig" in blob
    assert "die spd stimmt zu" in blob
    assert "weidetierhaltung schützen" in blob  # quote body kept
    assert "abschussquoten" in blob  # drucksache Punkt
    assert "regulierung des wolfs" in blob  # drucksache title


def test_normalisation_strips_markup_and_id_markers():
    blob = build_search_index(TOPS, SUMMARIES, DRUCKSACHEN)["90_Tagesordnungspunkt 3"]
    assert "**" not in blob
    assert "id217001" not in blob
    assert blob == blob.lower()


def test_bundled_top_uses_subtopics_and_skips_errored_drucksache():
    blob = build_search_index(TOPS, SUMMARIES, DRUCKSACHEN)["90_Zusatzpunkt 8"]
    assert "antrag der grünen" in blob
    assert "klimageld auszahlen" in blob
    assert "kein dip-text" not in blob  # errored Drucksache contributes nothing


def test_every_top_gets_an_entry():
    idx = build_search_index(TOPS, {}, {})
    assert set(idx) == set(TOPS)
