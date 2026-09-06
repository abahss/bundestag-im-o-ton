"""Regression tests for subtopic / Drucksache parsing in build_tops_lookup.

Covers the session-83 TOP-15 data-quality bug: a Zusatzpunkt folded into a joint
debate whose Drucksache bled onto the preceding c) subtopic, plus the older
last-wins bug where a Beschlussempfehlung overwrote the originating Gesetzentwurf.
"""
from pathlib import Path

from practicepreach.tools import build_tops_lookup

# Minimal plenary-protocol XML: TOP 15 bundles 15a-15c plus ZP 8, and 15a carries
# both its Gesetzentwurf and a later Beschlussempfehlung Drucksache.
_XML = """<?xml version="1.0" encoding="UTF-8"?>
<dbtplenarprotokoll sitzung-nr="83" sitzung-datum="11.06.2026">
  <sitzungsverlauf>
    <tagesordnungspunkt top-id="Tagesordnungspunkt 15">
      <p klasse="J">Ich rufe jetzt auf die Tagesordnungspunkte 15a bis 15c sowie Zusatzpunkt 8:</p>
      <p klasse="T_NaS">15\ta)\tErste Beratung des von der Bundesregierung eingebrachten Entwurfs eines Gesetzes zur Sicherung der Versorgungssicherheit Strom</p>
      <p klasse="T_Drs">Drucksache 21/6279</p>
      <p klasse="T_NaS">Beschlussempfehlung und Bericht des Ausschusses fuer Wirtschaft und Energie</p>
      <p klasse="T_Drs">Drucksache 21/9999</p>
      <p klasse="T_NaS">b)\tBeratung des Antrags der Abgeordneten und der Fraktion BUENDNIS 90/DIE GRUENEN</p>
      <p klasse="T_fett">Effiziente Kapazitaetsausschreibungen mit Zukunft</p>
      <p klasse="T_Drs">Drucksache 21/6369</p>
      <p klasse="T_NaS">c)\tBeratung des Antrags der Abgeordneten und der Fraktion Die Linke</p>
      <p klasse="T_fett">Energieversorgung sichern - Bezahlbar, erneuerbar und dezentral</p>
      <p klasse="T_Drs">Drucksache 21/6360</p>
      <p klasse="T_ZP_NaS">ZP 8\tErste Beratung des vom Bundesrat eingebrachten Entwurfs eines Gesetzes zur AEnderung des Erneuerbare-Energien-Gesetzes</p>
      <p klasse="T_Drs">Drucksache 21/5920</p>
      <p klasse="T_Ueberweisung">UEberweisungsvorschlag: Ausschuss fuer Wirtschaft und Energie</p>
      <rede id="ID1"><p klasse="redner"><redner><name><fraktion>SPD</fraktion></name></redner></p><p klasse="J_1">Rede.</p></rede>
    </tagesordnungspunkt>
  </sitzungsverlauf>
</dbtplenarprotokoll>
"""


def _lookup(tmp_path: Path) -> dict:
    xml = tmp_path / "21083.xml"
    xml.write_text(_XML, encoding="utf-8")
    return build_tops_lookup(str(xml))["83_Tagesordnungspunkt 15"]


def test_zusatzpunkt_drucksache_does_not_bleed_onto_preceding_subtopic(tmp_path):
    subs = {s["key"]: s for s in _lookup(tmp_path)["subtopics"]}

    assert subs["c"]["drucksache"] == "21/6360"
    assert "21/5920" not in subs["c"]["drucksachen"]

    assert "ZP 8" in subs, "bundled Zusatzpunkt must become its own subtopic"
    assert subs["ZP 8"]["drucksache"] == "21/5920"


def test_first_drucksache_wins_over_later_beschlussempfehlung(tmp_path):
    subs = {s["key"]: s for s in _lookup(tmp_path)["subtopics"]}

    assert subs["a"]["drucksache"] == "21/6279"
    assert subs["a"]["drucksachen"] == ["21/6279", "21/9999"]


def test_bundled_top_has_no_own_title(tmp_path):
    top = _lookup(tmp_path)
    assert top["title"] == ""
    assert [s["key"] for s in top["subtopics"]] == ["a", "b", "c", "ZP 8"]


# --- Bug A: a regular-agenda TOP folded into a neighbouring debate block -------------
# Session 53 (15.01.2026) TOP 31: "Ich rufe auf die Tagesordnungspunkte 31a, 31b, 22
# sowie Zusatzpunkt 4". The "22 Beratung des Antrags ..." line has no "a)" and no "ZP",
# so today its T_fett title and Drucksache 21/3601 bled onto subtopic 31b.
_XML_53 = """<?xml version="1.0" encoding="UTF-8"?>
<dbtplenarprotokoll sitzung-nr="53" sitzung-datum="15.01.2026">
  <sitzungsverlauf>
    <tagesordnungspunkt top-id="Tagesordnungspunkt 31">
      <p klasse="J">Ich rufe auf die Tagesordnungspunkte 31a, 31b, 22 sowie Zusatzpunkt 4:</p>
      <p klasse="T_NaS">31\ta)\tErste Beratung des von der Bundesregierung eingebrachten Entwurfs eines Gesetzes zur Durchführung einer Verordnung der Europäischen Union</p>
      <p klasse="T_Drs">Drucksache 21/3484</p>
      <p klasse="T_NaS">b)\tErste Beratung des von der Bundesregierung eingebrachten Entwurfs eines Ersten Gesetzes zur Änderung des Eurojust-Gesetzes</p>
      <p klasse="T_Drs">Drucksache 21/3483</p>
      <p klasse="T_NaS">22\tBeratung des Antrags der Abgeordneten Clara Bünger, Bodo Ramelow, weiterer Abgeordneter und der Fraktion Die Linke</p>
      <p klasse="T_fett">Humanitäres Bleiberecht für jesidische Geflüchtete vor dem Hintergrund des Genozids</p>
      <p klasse="T_Drs">Drucksache 21/3601</p>
      <p klasse="T_ZP_NaS">ZP 4\tBeratung des Antrags der Abgeordneten und der Fraktion Die Linke</p>
      <p klasse="T_fett">Bundeskaderathletinnen und -athleten finanziell und sozial absichern</p>
      <p klasse="T_Drs">Drucksache 21/3616</p>
      <p klasse="J">Es handelt sich um Überweisungen im vereinfachten Verfahren ohne Debatte.</p>
    </tagesordnungspunkt>
  </sitzungsverlauf>
</dbtplenarprotokoll>
"""


def test_folded_numbered_top_becomes_its_own_toplevel_entry(tmp_path):
    xml = tmp_path / "21053.xml"
    xml.write_text(_XML_53, encoding="utf-8")
    tops = build_tops_lookup(str(xml))

    host = tops["53_Tagesordnungspunkt 31"]
    subs = {s["key"]: s for s in host["subtopics"]}
    assert list(subs) == ["a", "b", "ZP 4"]
    # 31b keeps only its own Gesetzentwurf — 21/3601 belonged to the folded TOP 22
    assert subs["b"]["drucksachen"] == ["21/3483"]
    assert "21/3601" not in subs["b"]["drucksachen"]
    assert subs["b"]["title"].startswith("Entwurf eines Ersten Gesetzes zur Änderung des Eurojust")

    assert "53_Tagesordnungspunkt 22" in tops, "folded regular-agenda TOP must be split off"
    folded = tops["53_Tagesordnungspunkt 22"]
    assert folded["title"] == "Humanitäres Bleiberecht für jesidische Geflüchtete vor dem Hintergrund des Genozids"
    assert folded["drucksache"] == "21/3601"
    assert folded["drucksachen"] == ["21/3601"]
    assert folded["date"] == "15.01.2026"
    assert folded["subtopics"] == []


# Session 56 (29.01.2026): "Ich rufe jetzt auf den Zusatzpunkt 3 sowie Tagesordnungspunkt
# 25". The host (ZP 3) has no lettered subtopics; TOP 25 is a wholly unrelated item whose
# T_fett title and Drucksachen bled into ZP 3's top-level fields.
_XML_56 = """<?xml version="1.0" encoding="UTF-8"?>
<dbtplenarprotokoll sitzung-nr="56" sitzung-datum="29.01.2026">
  <sitzungsverlauf>
    <tagesordnungspunkt top-id="Zusatzpunkt 3">
      <p klasse="J">Ich rufe jetzt auf den Zusatzpunkt 3 sowie Tagesordnungspunkt 25:</p>
      <p klasse="T_NaS">Zweite und dritte Beratung des von der Bundesregierung eingebrachten Entwurfs eines Gesetzes zur Umsetzung der Richtlinie (EU) 2022/2555</p>
      <p klasse="T_Drs">Drucksache 21/2510</p>
      <p klasse="T_NaS">Beschlussempfehlung und Bericht des Innenausschusses (4. Ausschuss)</p>
      <p klasse="T_Drs">Drucksache 21/3906</p>
      <p klasse="T_NaS">25\tBeratung der Beschlussempfehlung und des Berichts des Innenausschusses (4. Ausschuss) zu dem Antrag der Abgeordneten Dr. Konstantin von Notz</p>
      <p klasse="T_fett">Deutschland resilient machen – Für einen ganzheitlichen Schutz unserer kritischen Infrastruktur</p>
      <p klasse="T_Drs">Drucksachen 21/2725, 21/3761</p>
      <rede id="ID1"><p klasse="redner"><redner><name><fraktion>CDU/CSU</fraktion></name></redner></p><p klasse="J_1">Rede.</p></rede>
    </tagesordnungspunkt>
  </sitzungsverlauf>
</dbtplenarprotokoll>
"""


def test_folded_top_split_when_host_has_no_lettered_subtopics(tmp_path):
    xml = tmp_path / "21056.xml"
    xml.write_text(_XML_56, encoding="utf-8")
    tops = build_tops_lookup(str(xml))

    host = tops["56_Zusatzpunkt 3"]
    assert host["drucksachen"] == ["21/2510", "21/3906"]
    assert host["drucksache"] == "21/2510"
    assert "21/2725" not in host["drucksachen"]
    assert host["title"].startswith("Entwurf eines Gesetzes zur Umsetzung der Richtlinie")

    assert "56_Tagesordnungspunkt 25" in tops
    folded = tops["56_Tagesordnungspunkt 25"]
    assert folded["title"] == "Deutschland resilient machen – Für einen ganzheitlichen Schutz unserer kritischen Infrastruktur"
    assert folded["drucksachen"] == ["21/2725", "21/3761"]
    assert folded["drucksache"] == "21/2725"


# --- Bug B: the Gesetzentwurf's Drucksachennummer lands in a T_fett, not a T_Drs -------
# Session 59 (26.02.2026) ZP 6: "<p klasse='T_fett'>Drucksache 21/1941</p>". Today the
# canonical Drucksache became the Beschlussempfehlung 21/4325 and the title became the
# literal string "Drucksache 21/1941".
_XML_59 = """<?xml version="1.0" encoding="UTF-8"?>
<dbtplenarprotokoll sitzung-nr="59" sitzung-datum="26.02.2026">
  <sitzungsverlauf>
    <tagesordnungspunkt top-id="Zusatzpunkt 6">
      <p klasse="J">Ich rufe auf den Zusatzpunkt 6:</p>
      <p klasse="T_NaS">–\tZweite und dritte Beratung des von der Bundesregierung eingebrachten Entwurfs eines Gesetzes zur Stärkung der Tarifautonomie</p>
      <p klasse="T_fett">Drucksache 21/1941</p>
      <p klasse="T_NaS">Beschlussempfehlung und Bericht des Ausschusses für Arbeit und Soziales (11. Ausschuss)</p>
      <p klasse="T_Drs">Drucksache 21/4325</p>
      <p klasse="T_NaS">–\tBericht des Haushaltsausschusses (8. Ausschuss) gemäß § 96 der Geschäftsordnung</p>
      <p klasse="T_Drs">Drucksache 21/4344</p>
      <rede id="ID1"><p klasse="redner"><redner><name><fraktion>SPD</fraktion></name></redner></p><p klasse="J_1">Rede.</p></rede>
    </tagesordnungspunkt>
  </sitzungsverlauf>
</dbtplenarprotokoll>
"""


def test_drucksachennummer_in_t_fett_is_read_as_drucksache(tmp_path):
    xml = tmp_path / "21059.xml"
    xml.write_text(_XML_59, encoding="utf-8")
    top = build_tops_lookup(str(xml))["59_Zusatzpunkt 6"]

    assert top["drucksachen"] == ["21/1941", "21/4325", "21/4344"]
    assert top["drucksache"] == "21/1941"
    assert top["title"] == "Entwurf eines Gesetzes zur Stärkung der Tarifautonomie"


# --- Bug D: a Beschlussempfehlung/Bericht sub-line mislabelled as T_fett ---------------
# Session 53 (15.01.2026) TOP 13: the Beschlussempfehlung line carries klasse="T_fett"
# instead of "T_NaS" and became the TOP title, hiding the actual bill title.
_XML_53_TOP13 = """<?xml version="1.0" encoding="UTF-8"?>
<dbtplenarprotokoll sitzung-nr="53" sitzung-datum="15.01.2026">
  <sitzungsverlauf>
    <tagesordnungspunkt top-id="Tagesordnungspunkt 13">
      <p klasse="J">Ich rufe auf den Tagesordnungspunkt 13:</p>
      <p klasse="T_NaS">Zweite und dritte Beratung des von den Fraktionen der CDU/CSU und SPD eingebrachten Entwurfs eines Zweiten Gesetzes zur Änderung des Tierhaltungskennzeichnungsgesetzes</p>
      <p klasse="T_Drs">Drucksache 21/3292</p>
      <p klasse="T_fett">Beschlussempfehlung und Bericht des Ausschusses für Landwirtschaft, Ernährung und Heimat (10. Ausschuss)</p>
      <p klasse="T_Drs">Drucksache 21/3632</p>
      <rede id="ID1"><p klasse="redner"><redner><name><fraktion>CDU/CSU</fraktion></name></redner></p><p klasse="J_1">Rede.</p></rede>
    </tagesordnungspunkt>
  </sitzungsverlauf>
</dbtplenarprotokoll>
"""


def test_beschlussempfehlung_mislabelled_as_t_fett_is_not_the_title(tmp_path):
    xml = tmp_path / "21053b.xml"
    xml.write_text(_XML_53_TOP13, encoding="utf-8")
    top = build_tops_lookup(str(xml))["53_Tagesordnungspunkt 13"]

    assert top["title"] == "Entwurf eines Zweiten Gesetzes zur Änderung des Tierhaltungskennzeichnungsgesetzes"
    assert top["drucksachen"] == ["21/3292", "21/3632"]
    assert top["drucksache"] == "21/3292"


# --- Bug F: a Geschäftsordnungsdebatte about withdrawing a TOP is mistaken for that TOP -
# Session 88 (08.07.2026): "Zur Geschäftsordnung" (no digit in its own top-id) contains a
# motion to withdraw "Tagesordnungspunkt 22a" from today's agenda. The top_id fallback
# (scans J paragraphs for "Tagesordnungspunkt N" when top-id has no digit) picks up "22"
# from that sentence and mislabels the whole procedural debate as TOP 22 — which then has
# no T_NaS/T_fett/T_Drs at all, i.e. a completely empty entry.
_XML_88_GO = """<?xml version="1.0" encoding="UTF-8"?>
<dbtplenarprotokoll sitzung-nr="88" sitzung-datum="08.07.2026">
  <sitzungsverlauf>
    <tagesordnungspunkt top-id="Zur Geschäftsordnung">
      <p klasse="J">Bevor wir zur Feststellung der Tagesordnung kommen, müssen wir noch einen Antrag zur Geschäftsordnung beraten.</p>
      <p klasse="J">Die Fraktion Bündnis 90/Die Grünen und die Fraktion Die Linke haben beantragt, Tagesordnungspunkt 22a abzusetzen.</p>
      <rede id="ID1"><p klasse="redner"><redner><name><fraktion>BÜNDNIS 90/DIE GRÜNEN</fraktion></name></redner></p><p klasse="J_1">Rede.</p></rede>
    </tagesordnungspunkt>
    <tagesordnungspunkt top-id="Tagesordnungspunkt 1">
      <p klasse="T_NaS">Befragung der Bundesregierung</p>
    </tagesordnungspunkt>
  </sitzungsverlauf>
</dbtplenarprotokoll>
"""


def test_geschaeftsordnungsdebatte_about_withdrawing_a_top_is_dropped(tmp_path):
    xml = tmp_path / "21088.xml"
    xml.write_text(_XML_88_GO, encoding="utf-8")
    tops = build_tops_lookup(str(xml))

    assert "88_Tagesordnungspunkt 22" not in tops
    assert "88_Tagesordnungspunkt 1" in tops, "a real, content-bearing TOP must not be dropped"
