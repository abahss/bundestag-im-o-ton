"""Regression tests for subtopic / Drucksache parsing in build_tops_lookup.

Covers the session-83 TOP-15 data-quality bug: a Zusatzpunkt folded into a joint
debate whose Drucksache bled onto the preceding c) subtopic, plus the older
last-wins bug where a Beschlussempfehlung overwrote the originating Gesetzentwurf.
"""
from pathlib import Path

import pandas as pd

from practicepreach.tools import (
    build_tops_lookup,
    haushaltswoche_hub_entries,
    process_bundestag_xml,
)

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


# --- Haushaltswoche (session 91, 08.09.2026): Einzelplan debate blocks ----------------
# The 1. Lesung Bundeshaushalt 2027 splits the ressort debates into <tagesordnungspunkt>
# blocks whose top-id is "Einzelplan 12" etc. — not "Tagesordnungspunkt N". The four pure
# ressort blocks (12/16/24/09) carry no bill text at all, only the spoken intro naming the
# Geschäftsbereich.
_XML_91_EP12 = """<?xml version="1.0" encoding="UTF-8"?>
<dbtplenarprotokoll sitzung-nr="91" sitzung-datum="08.09.2026">
  <sitzungsverlauf>
    <tagesordnungspunkt top-id="Einzelplan 12">
      <p klasse="J">Jetzt kommen wir zum Geschäftsbereich des Bundesministeriums für Verkehr, Einzelplan 12.</p>
      <p klasse="J">Dann eröffne ich hiermit die Aussprache.</p>
      <rede id="ID2191100"><p klasse="redner"><redner><name><fraktion>CDU/CSU</fraktion></name></redner></p><p klasse="J_1">Rede.</p></rede>
    </tagesordnungspunkt>
  </sitzungsverlauf>
</dbtplenarprotokoll>
"""


def test_einzelplan_block_becomes_a_top_with_ressort_subtitle(tmp_path):
    xml = tmp_path / "21091.xml"
    xml.write_text(_XML_91_EP12, encoding="utf-8")
    tops = build_tops_lookup(str(xml))

    assert "91_Einzelplan 12" in tops
    top = tops["91_Einzelplan 12"]
    assert top["top_id"] == "Einzelplan 12"
    assert top["title"] == ""
    assert top["subtitle"] == "Geschäftsbereich des Bundesministeriums für Verkehr"
    assert top["subtopics"] == []
    assert top["date"] == "08.09.2026"


# The Einzelplan 08 block opens the allgemeine Finanzdebatte and carries the only bill of
# the day, the Haushaltsbegleitgesetz 2027 (Drs 21/7860). Its T_NaS opens with a bare
# agenda number ("4\tErste Beratung ..."), which must NOT be split off as its own
# "Tagesordnungspunkt 4" — the block stays one entry, keyed 91_Einzelplan 08, and the
# 15 speeches of the general debate belong to it.
_XML_91_EP08 = """<?xml version="1.0" encoding="UTF-8"?>
<dbtplenarprotokoll sitzung-nr="91" sitzung-datum="08.09.2026">
  <sitzungsverlauf>
    <tagesordnungspunkt top-id="Einzelplan 08">
      <p klasse="J">Nun rufe ich die allgemeine Finanzdebatte einschließlich der Einzelpläne 08, 20, 32 und 60 sowie Tagesordnungspunkt 4 auf:</p>
      <p klasse="T_NaS">4\tErste Beratung des von der Bundesregierung eingebrachten Entwurfs eines Haushaltsbegleitgesetzes 2027</p>
      <p klasse="T_Drs">Drucksache 21/7860</p>
      <p klasse="T_Ueberweisung">Überweisungsvorschlag: Haushaltsausschuss (f) Finanzausschuss</p>
      <p klasse="J">Ich eröffne die Aussprache.</p>
      <rede id="ID2191200"><p klasse="redner"><redner><name><fraktion>AfD</fraktion></name></redner></p><p klasse="J_1">Rede.</p></rede>
    </tagesordnungspunkt>
  </sitzungsverlauf>
</dbtplenarprotokoll>
"""


def test_einzelplan_08_keeps_haushaltsbegleitgesetz_and_is_not_split(tmp_path):
    xml = tmp_path / "21091.xml"
    xml.write_text(_XML_91_EP08, encoding="utf-8")
    tops = build_tops_lookup(str(xml))

    assert "91_Einzelplan 08" in tops
    assert "91_Tagesordnungspunkt 4" not in tops, "the bare '4' must not fold into its own TOP"

    top = tops["91_Einzelplan 08"]
    assert top["subtitle"] == "Allgemeine Finanzdebatte"
    assert top["drucksache"] == "21/7860"
    assert top["drucksachen"] == ["21/7860"]
    assert top["subtopics"] == []
    # no garbled leftover from the "4\tErste Beratung ..." NaS
    assert not top["title"].startswith("4")


def test_process_bundestag_xml_assigns_speeches_to_einzelplan_top_key(tmp_path):
    xml = tmp_path / "21091.xml"
    xml.write_text(_XML_91_EP12, encoding="utf-8")
    df = pd.DataFrame(columns=["type", "date", "id", "party", "top_key", "text"])

    process_bundestag_xml(str(xml), df)

    assert not df.empty, "Einzelplan speeches must not be dropped"
    assert set(df["top_key"]) == {"91_Einzelplan 12"}


# --- Haushaltswoche day 2+ (sessions 92/93): top-id becomes unreliable -----------------
# From session 92 onward, top-id on Einzelplan blocks is no longer trustworthy: it can be
# missing its number entirely, or (session 93) the exact same top-id gets reused for
# unrelated blocks on the same day. The <inhaltsverzeichnis> (ToC) always carries the
# correct "Einzelplan NN" and links each <rede> to it via <xref rid="...">, independent of
# top-id — see _ivz_einzelplan_rede_map / project memory project_haushaltswoche_structure_rethink.

# Session 92: Einzelplan 05 (Auswärtiges Amt) has top-id="Einzelplan" — no number at all.
# Without the ToC-based override, this whole block fails _valid_top and is silently
# dropped (never even becomes an entry).
_XML_92_EP05_NO_NUMBER = """<?xml version="1.0" encoding="UTF-8"?>
<dbtplenarprotokoll sitzung-nr="92" sitzung-datum="09.09.2026">
  <inhaltsverzeichnis>
    <ivz-block>
      <ivz-block-titel>Einzelplan 05</ivz-block-titel>
      <ivz-eintrag>
        <ivz-eintrag-inhalt>Jemand</ivz-eintrag-inhalt>
        <xref rid="ID2192100"/>
      </ivz-eintrag>
    </ivz-block>
  </inhaltsverzeichnis>
  <sitzungsverlauf>
    <tagesordnungspunkt top-id="Einzelplan">
      <p klasse="J">Wir kommen damit zum Geschäftsbereich des Auswärtigen Amtes, Einzelplan 05.</p>
      <rede id="ID2192100"><p klasse="redner"><redner><name><fraktion>SPD</fraktion></name></redner></p><p klasse="J_1">Rede.</p></rede>
    </tagesordnungspunkt>
  </sitzungsverlauf>
</dbtplenarprotokoll>
"""


def test_einzelplan_without_a_number_in_top_id_uses_ivz_for_the_number(tmp_path):
    xml = tmp_path / "21092.xml"
    xml.write_text(_XML_92_EP05_NO_NUMBER, encoding="utf-8")
    tops = build_tops_lookup(str(xml))

    assert "92_Einzelplan 05" in tops, "bare top-id='Einzelplan' must not drop the block"
    assert tops["92_Einzelplan 05"]["subtitle"] == "Geschäftsbereich des Auswärtigen Amtes"


# Session 93: top-id="Tagesordnungspunkt 3" is reused for the day's empty continuation
# announcement AND (separately, later in the file) for a genuinely unrelated Einzelplan 10
# debate. Without the ToC override these collide into one "93_Tagesordnungspunkt 3" bucket
# (last-wins) instead of becoming their own, distinct entries.
_XML_93_TOP_ID_COLLISION = """<?xml version="1.0" encoding="UTF-8"?>
<dbtplenarprotokoll sitzung-nr="93" sitzung-datum="10.09.2026">
  <inhaltsverzeichnis>
    <ivz-block>
      <ivz-block-titel>Tagesordnungspunkt 3 (Fortsetzung):</ivz-block-titel>
      <ivz-block>
        <ivz-block-titel>Einzelplan 10</ivz-block-titel>
        <ivz-eintrag>
          <ivz-eintrag-inhalt>Jemand</ivz-eintrag-inhalt>
          <xref rid="ID2193100"/>
        </ivz-eintrag>
      </ivz-block>
    </ivz-block>
  </inhaltsverzeichnis>
  <sitzungsverlauf>
    <tagesordnungspunkt top-id="Tagesordnungspunkt 3">
      <p klasse="J">Wir setzen jetzt unsere Haushaltsberatungen fort.</p>
    </tagesordnungspunkt>
    <tagesordnungspunkt top-id="Tagesordnungspunkt 3">
      <p klasse="J">Wir setzen jetzt unsere Haushaltsberatungen fort und kommen zum Geschäftsbereich des Bundesministeriums für Landwirtschaft, Ernährung und Heimat, Einzelplan 10.</p>
      <rede id="ID2193100"><p klasse="redner"><redner><name><fraktion>AfD</fraktion></name></redner></p><p klasse="J_1">Rede.</p></rede>
    </tagesordnungspunkt>
  </sitzungsverlauf>
</dbtplenarprotokoll>
"""


def test_reused_top_id_does_not_collide_thanks_to_ivz(tmp_path):
    xml = tmp_path / "21093.xml"
    xml.write_text(_XML_93_TOP_ID_COLLISION, encoding="utf-8")
    tops = build_tops_lookup(str(xml))

    assert "93_Einzelplan 10" in tops
    assert tops["93_Einzelplan 10"]["subtitle"] == \
        "Geschäftsbereich des Bundesministeriums für Landwirtschaft, Ernährung und Heimat"
    # the empty continuation stub has nothing to show and is dropped, not merged in
    assert "93_Tagesordnungspunkt 3" not in tops


def test_process_bundestag_xml_keeps_reused_top_id_speeches_separate(tmp_path):
    xml = tmp_path / "21093.xml"
    xml.write_text(_XML_93_TOP_ID_COLLISION, encoding="utf-8")
    df = pd.DataFrame(columns=["type", "date", "id", "party", "top_key", "text"])

    process_bundestag_xml(str(xml), df)

    assert set(df["top_key"]) == {"93_Einzelplan 10"}


# Regression against a trimmed copy of the real session-91 protocol (Haushaltswoche,
# first such session in the data set). Speech bodies are shortened, everything else is
# verbatim. Locks the whole session's shape, not just one block in isolation.
_FIXTURE_91 = Path(__file__).parent / "fixtures" / "21091_haushaltswoche.xml"


def test_session_91_haushaltswoche_full_shape():
    tops = build_tops_lookup(str(_FIXTURE_91))

    # the five ressort debates the old parser dropped entirely
    assert {"91_Einzelplan 08", "91_Einzelplan 09", "91_Einzelplan 12",
            "91_Einzelplan 16", "91_Einzelplan 24"} <= set(tops)
    # no bare agenda number folded out of an Einzelplan block
    assert "91_Tagesordnungspunkt 4" not in tops

    assert tops["91_Einzelplan 09"]["subtitle"] == \
        "Geschäftsbereich des Bundesministeriums für Wirtschaft und Energie"
    assert tops["91_Einzelplan 08"]["subtitle"] == "Allgemeine Finanzdebatte"
    assert tops["91_Einzelplan 08"]["drucksache"] == "21/7860"

    # the Einbringung still parses as a normal bundled TOP with a/b subtopics
    assert [s["key"] for s in tops["91_Tagesordnungspunkt 3"]["subtopics"]] == ["a", "b"]

    df = pd.DataFrame(columns=["type", "date", "id", "party", "top_key", "text"])
    process_bundestag_xml(str(_FIXTURE_91), df)
    assert set(df["top_key"]) == {
        "91_Einzelplan 08", "91_Einzelplan 09", "91_Einzelplan 12",
        "91_Einzelplan 16", "91_Einzelplan 24",
    }


def test_haushaltswoche_hub_entry_groups_the_einzelplaene():
    tops = build_tops_lookup(str(_FIXTURE_91))
    hubs = haushaltswoche_hub_entries(tops)

    assert set(hubs) == {"91_Haushaltswoche"}
    hub = hubs["91_Haushaltswoche"]
    assert hub["top_key"] == "91_Haushaltswoche"
    assert hub["session"] == "91"
    assert hub["date"] == "08.09.2026"
    assert hub["title"] == "Bundeshaushalt 2027 – 1. Lesung"
    assert hub["einzelplaene"] == [
        "91_Einzelplan 08", "91_Einzelplan 09", "91_Einzelplan 12",
        "91_Einzelplan 16", "91_Einzelplan 24",
    ]
    assert hub["einbringung"] == "91_Tagesordnungspunkt 3"
    # shaped like every other tops.json entry so the frontend route/search index just work
    assert hub["subtopics"] == [] and hub["drucksachen"] == []


def test_no_hub_when_session_has_no_einzelplaene():
    tops = {
        "83_Tagesordnungspunkt 15": {"session": "83", "date": "11.06.2026", "top_id": "Tagesordnungspunkt 15"},
    }
    assert haushaltswoche_hub_entries(tops) == {}
