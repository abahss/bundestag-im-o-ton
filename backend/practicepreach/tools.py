import re
import requests, os, time, csv, sys
import BundestagsAPy
import pandas as pd
import xmltodict
import xml.etree.ElementTree as ET
import time
from practicepreach.rag import Rag

from practicepreach.params import *
from practicepreach.constants import *

SPEECHES_XML_DIR = os.environ.get("SPEECHES_XML_DIR")

BASE = "https://search.dip.bundestag.de/api/v1"

def process_bundestag_xml(url: str, df: pd.DataFrame):
    """
    Process speeches xml file and store data to pandas DataFrame.
    Stores top_id as metadata; use build_tops_lookup for title resolution.
    """
    tree = ET.parse(url)
    root = tree.getroot()

    a_date = root.attrib['sitzung-datum']
    session_id = root.attrib.get('sitzung-nr', '')

    # path: <dbtplenarprotokoll>/<sitzungsverlauf>/<tagesordnungspunkt>/<rede>
    # "Einzelplan NN" covers the Haushaltswoche ressort debates (session 91+).
    _valid_top = re.compile(r'^(Tagesordnungspunkt|Zusatzpunkte?|Einzelplan)\s+\d+', re.IGNORECASE)
    ivz_einzelplan = _ivz_einzelplan_rede_map(root)

    for punkt in root.findall("./sitzungsverlauf/tagesordnungspunkt"):
        top_id = punkt.get("top-id", "").replace('\xa0', ' ')
        top_id = _ivz_override_top_id(punkt, ivz_einzelplan) or top_id
        if top_id and not re.search(r'\d', top_id):
            for p in punkt.findall("./p[@klasse='J']"):
                text = ''.join(p.itertext()).strip()
                m = re.search(r'(Tagesordnungspunkt|Zusatzpunkt)[\s\xa0]+(\d+)', text)
                if m:
                    top_id = f"{m.group(1)} {m.group(2)}"
                    break
        if not _valid_top.match(top_id):
            continue
        # Unique key per TOP across sessions: e.g. "21063_Tagesordnungspunkt 20"
        top_key = f"{session_id}_{top_id}" if session_id else top_id

        for rede in punkt.findall("./rede"):
            rede_id = rede.get("id")

            fraktion = rede.find(".//p[@klasse='redner']//fraktion")
            if fraktion is not None:
                main_text_nodes = rede.findall(".//p[@klasse='J_1']")
                if not main_text_nodes:
                    continue

                df.loc[len(df)] = {'type': 'speech',
                        'date': a_date,
                        'id': rede_id,
                        'party': fraktion.text,
                        'top_key': top_key,
                        'text': main_text_nodes[0].text}

                for node in rede.findall(".//p[@klasse='J']"):
                    df.loc[len(df)] = {'type': 'speech',
                          'date': a_date,
                          'id': rede_id,
                          'party': fraktion.text,
                          'top_key': top_key,
                          'text': node.text}


def _extract_nas_title(nas: str) -> str:
    """Extract bill/motion title from a procedural NaS string when no T_fett is present."""
    # Match "Entwurf(s) eines [optional ordinal adjective] Gesetzes ..." — ordinals like
    # "Ersten", "Zweiten", "Dritten" etc. are common in German parliamentary bill titles.
    # [\w\.]+ also matches "..." (ellipsis) used in abbreviated XML titles
    # "Gesetzes" may be a standalone word or the tail of a compound ("Haushaltsbegleit-
    # gesetzes"), and may be followed by a year rather than a "zur/über ..." clause.
    m = re.search(
        r'(Entwurfs? eines (?:[\w.]+\s+)*[\wäöüÄÖÜß-]*[Gg]esetzes(?=\s|$)(?:\s.+)?)',
        nas, re.DOTALL,
    )
    if m:
        return re.sub(r'^Entwurfs\b', 'Entwurf', m.group(1)).strip()
    return ''


def _drucksache_pdf_url(nr: str) -> str:
    """Construct dserver.bundestag.de PDF URL from 'WP/NUM' string."""
    try:
        wp, num = nr.split("/")
        num_str = num.zfill(5)
        return f"https://dserver.bundestag.de/btd/{wp}/{num_str[:3]}/{wp}{num_str}.pdf"
    except Exception:
        return ""


# A regular-agenda TOP folded into a neighbouring debate block: its NaS opens with a
# bare agenda number ("22 Beratung des Antrags ...") — no "a)" letter, no "ZP". It must
# become its own top-level entry, otherwise its title/Drucksache bleed onto the host TOP.
# Seen in sessions 53 (15.01.2026) and 56 (29.01.2026).
_FOLDED_TOP = re.compile(
    r'^\s*(\d+)\s+(?:(?:Erste|Zweite|Dritte|Zweite und dritte)\s+)?Beratung\b',
    re.IGNORECASE,
)
# A Drucksachennummer mislabelled as a T_fett title instead of a T_Drs line
# (session 59, 26.02.2026, ZP 6).
_DRS_IN_FETT = re.compile(r'^\s*Drucksachen?\s+\d+/\d+', re.IGNORECASE)
# A Beschlussempfehlung/Bericht sub-line sometimes carries klasse="T_fett" instead of
# "T_NaS" (session 53, 15.01.2026, TOP 13). It is procedural, never the TOP title.
_PROCEDURAL_FETT = re.compile(r'^\s*(?:Beschlussempfehlung|Bericht des)\b', re.IGNORECASE)


_EINZELPLAN = re.compile(r'^Einzelplan\s+\d+', re.IGNORECASE)
_IVZ_EINZELPLAN_TITEL = re.compile(r'^Einzelplan\s+(\d{1,2})\b', re.IGNORECASE)


def _ivz_einzelplan_rede_map(root) -> dict:
    """Map <rede id="..."> -> "Einzelplan NN", read from the session's
    <inhaltsverzeichnis> (table of contents) instead of top-id.

    Necessary during the Haushaltswoche: top-id is unreliable there — formatting
    varies ("Einzelplan 08" / "Einzelplan 4" / bare "Einzelplan" with no number at
    all), and in session 93 the SAME top-id "Tagesordnungspunkt 3" is reused for two
    unrelated real Einzelplan debates plus the day's empty continuation announcement
    (see project memory project_haushaltswoche_structure_rethink). The ToC's
    <ivz-block-titel> is always correctly numbered, and every speaker entry carries an
    <xref rid="..."> pointing at the exact <rede id="..."> it belongs to — independent
    of which <tagesordnungspunkt> tag physically contains that rede.
    """
    ivz = root.find(".//inhaltsverzeichnis")
    if ivz is None:
        return {}

    mapping: dict = {}

    def walk(el):
        for block in el.findall("./ivz-block"):
            titel_el = block.find("./ivz-block-titel")
            titel = (
                (titel_el.text or "").replace('\xa0', ' ').strip()
                if titel_el is not None else ""
            )
            m = _IVZ_EINZELPLAN_TITEL.match(titel)
            if m:
                key = f"Einzelplan {int(m.group(1)):02d}"
                for xref in block.findall(".//xref"):
                    rid = xref.get("rid")
                    if rid:
                        mapping[rid] = key
            else:
                walk(block)  # keep descending for nested non-Einzelplan blocks

    walk(ivz)
    return mapping


def _ivz_override_top_id(punkt, ivz_einzelplan: dict) -> str:
    """If the ToC identifies this block's speeches as an Einzelplan debate, that
    identity wins over whatever top-id the <tagesordnungspunkt> tag itself carries —
    see _ivz_einzelplan_rede_map. Returns "" when the ToC has no opinion (normal
    sessions have no <inhaltsverzeichnis> match at all, so this is a no-op there)."""
    if not ivz_einzelplan:
        return ""
    for rede in punkt.findall("./rede"):
        key = ivz_einzelplan.get(rede.get("id"))
        if key:
            return key
    return ""


def _einzelplan_ressort(punkt) -> str:
    """The Geschäftsbereich a bare Einzelplan debate block belongs to, read from the
    spoken intro ("... zum Geschäftsbereich des Bundesministeriums für Verkehr,
    Einzelplan 12."). Not every Geschäftsbereich is phrased as "Bundesministerium für
    X" — e.g. "des Auswärtigen Amtes" (Einzelplan 05) or "des Bundeskanzlers und des
    Bundeskanzleramtes" (Einzelplan 04) name no ministry at all — so this matches
    whatever follows "Geschäftsbereich des" generically. Returns "" when the intro
    names no Geschäftsbereich (e.g. the Einzelplan 08 block, which opens the
    allgemeine Finanzdebatte without naming one)."""
    for p in punkt.findall("./p[@klasse='J']"):
        text = ''.join(p.itertext())
        m = re.search(
            r'Geschäftsbereich\s+des\s+(.+?)(?:\s*,\s*(?:dem\s+)?Einzelplan\b|\.)',
            text,
        )
        if m:
            return f"Geschäftsbereich des {m.group(1).strip()}"
    return ""


def build_tops_lookup(url: str) -> dict:
    """
    Extract TOP metadata from an XML file.
    Returns dict: {top_key: {top_id, title, session, date}}
    """
    tree = ET.parse(url)
    root = tree.getroot()

    a_date = root.attrib['sitzung-datum']
    session_id = root.attrib.get('sitzung-nr', '')

    _valid_top = re.compile(r'^(Tagesordnungspunkt|Zusatzpunkte?|Einzelplan)\s+\d+', re.IGNORECASE)
    ivz_einzelplan = _ivz_einzelplan_rede_map(root)

    tops = {}
    for punkt in root.findall("./sitzungsverlauf/tagesordnungspunkt"):
        top_id = punkt.get("top-id", "").replace('\xa0', ' ')
        top_id = _ivz_override_top_id(punkt, ivz_einzelplan) or top_id
        if not top_id:
            continue
        if not re.search(r'\d', top_id):
            for p in punkt.findall("./p[@klasse='J']"):
                text = ''.join(p.itertext()).strip()
                m = re.search(r'(Tagesordnungspunkt|Zusatzpunkt)[\s\xa0]+(\d+)', text)
                if m:
                    top_id = f"{m.group(1)} {m.group(2)}"
                    break
        if not _valid_top.match(top_id):
            continue
        top_key = f"{session_id}_{top_id}" if session_id else top_id
        # A Haushaltswoche Einzelplan block ("Einzelplan 08"). Its T_NaS opens with a bare
        # agenda number ("4\tErste Beratung ..."), but that number belongs to this block —
        # never fold it off as its own TOP.
        is_einzelplan = bool(_EINZELPLAN.match(top_id))
        # Agenda numbers this element legitimately owns ("Tagesordnungspunkt 7 und
        # Zusatzpunkt 9" -> {"7", "9"}). A "<n> Beratung ..." NaS whose n is in here is
        # this TOP's own line, not a folded-in neighbour.
        host_numbers = set(re.findall(r'\d+', top_id))
        def _clean(node):
            if node is None or not node.text:
                return ""
            return re.sub(r'^[\s\t–\-]*(?:ZP\s*\d+\s*)?', '', node.text).strip()

        # Collect T_fett / T_NaS only until the first subtopic NaS (a), b), ...) is reached.
        # T_fett/T_NaS that belong to a subtopic must not become the TOP-level title.
        t_fett = None
        t_nas = None
        for child in list(punkt):
            if child.tag != 'p':
                continue
            klasse = child.get('klasse', '')
            text = ''.join(child.itertext()).strip()
            if klasse == 'T_fett' and _DRS_IN_FETT.match(text):
                continue  # Drucksachennummer mislabelled as T_fett — never a title
            if klasse in ('T_NaS', 'T_ZP_NaS'):
                if re.match(r'^\s*(?:\d+\s+)?[a-z]\)', text):
                    break  # Pattern A subtopic — stop
                if re.match(r'^\s*ZP\s*\d+', text, re.IGNORECASE):
                    break  # bundled Zusatzpunkt — stop (its NaS is a subtopic, not the TOP title)
                _fm = None if is_einzelplan else _FOLDED_TOP.match(text)
                if _fm and _fm.group(1) not in host_numbers:
                    break  # folded regular-agenda TOP — its NaS/title belong to that TOP
                if t_nas is None:
                    t_nas = child
            elif klasse == 'T_fett' and not _PROCEDURAL_FETT.match(text):
                t_fett = child
            elif klasse == 'J':
                if re.search(r'Tagesordnungspunkt[\s\xa0]*\d+[a-z]:', text):
                    break  # Pattern B subtopic — stop

        if t_fett is not None and t_fett.text:
            title = t_fett.text.strip()
        else:
            _nas_clean = _clean(t_nas)
            title = _extract_nas_title(_nas_clean) or _nas_clean
        subtitle = _clean(t_nas)
        # Strip procedural-only subtitles that carry no content value
        _procedural = re.compile(
            r'^(Vereinbarte Debatte:?|Aktuelle Stunde|Fragestunde|Befragung der Bundesregierung)$',
            re.IGNORECASE
        )
        if _procedural.match(subtitle):
            subtitle = ""

        # Einzelplan blocks (Haushaltswoche): the subtitle is the Geschäftsbereich, read
        # from the spoken intro. The Einzelplan 08 block names no ministry — it opens the
        # allgemeine Finanzdebatte — so label it that. Either way the block's own T_NaS
        # (the "4\tErste Beratung ..." Haushaltsbegleitgesetz line) is not the subtitle.
        if is_einzelplan:
            subtitle = _einzelplan_ressort(punkt)
            if not subtitle:
                intro = " ".join(
                    "".join(p.itertext()) for p in punkt.findall("./p[@klasse='J']")
                )
                if re.search(r'allgemeine Finanzdebatte', intro, re.IGNORECASE):
                    subtitle = "Allgemeine Finanzdebatte"

        # Parse subtopics (a, b, c...) with Drucksache references.
        # Pattern A: T_NaS starts with "a)" / "18 a)" (shared debate, e.g. TOP 18)
        # Pattern B: J element announces "Tagesordnungspunkt 19a:" (sequential items, e.g. TOP 19)
        # Pattern ZP: T_ZP_NaS starts with "ZP 8" — a Zusatzpunkt folded into the joint
        #   debate. It MUST open its own subtopic, otherwise its T_Drs bleeds onto the
        #   preceding a)/b)/c) entry (e.g. session 83 TOP 15c wrongly got ZP 8's Drucksache).
        def _new_sub(key, nas=''):
            return {'key': key, 'nas': nas, 'title': '',
                    'drucksache': '', 'drucksache_url': '', 'drucksachen': []}

        subtopics = []
        pending = None
        top_drucksache = ''
        top_drucksache_url = ''
        top_drucksachen = []
        detached_tops = []   # regular-agenda TOPs folded into this block (see _FOLDED_TOP)
        detached_cur = None
        for child in list(punkt):
            if child.tag == 'rede':
                break
            if child.tag != 'p':
                continue
            klasse = child.get('klasse', '')
            text = ''.join(child.itertext()).strip()
            if klasse == 'T_fett' and _DRS_IN_FETT.match(text):
                klasse = 'T_Drs'  # Drucksachennummer mislabelled as T_fett
            if klasse in ('T_NaS', 'T_ZP_NaS'):
                m = re.match(r'^\s*(?:\d+\s+)?([a-z])\)', text)
                zp_m = re.match(r'^\s*ZP\s*(\d+)\s*(?:([a-z])\))?', text, re.IGNORECASE)
                folded_m = None if (m or zp_m or is_einzelplan) else _FOLDED_TOP.match(text)
                if folded_m and folded_m.group(1) in host_numbers:
                    folded_m = None  # this TOP's own "<n> Beratung ..." line, not folded
                if m:
                    letter = m.group(1)
                    if pending is not None and pending['key'] == letter and not pending['nas']:
                        # Pattern B already opened this subtopic — fill in the NaS instead of duplicating
                        pending['nas'] = text
                    else:
                        # Pattern A: new subtopic
                        if pending is not None:
                            subtopics.append(pending)
                        if detached_cur is not None:
                            detached_tops.append(detached_cur)
                            detached_cur = None
                        pending = _new_sub(letter, text)
                elif zp_m:
                    key = f"ZP {zp_m.group(1)}" + (zp_m.group(2) or '')
                    if pending is not None and pending['key'] == key and not pending['nas']:
                        pending['nas'] = text
                    else:
                        if pending is not None:
                            subtopics.append(pending)
                        if detached_cur is not None:
                            detached_tops.append(detached_cur)
                            detached_cur = None
                        pending = _new_sub(key, text)
                elif folded_m:
                    # A regular-agenda TOP folded into this block — split it off so its
                    # title/Drucksache never bleed onto the host TOP or a sibling subtopic.
                    if pending is not None:
                        subtopics.append(pending)
                        pending = None
                    if detached_cur is not None:
                        detached_tops.append(detached_cur)
                    detached_cur = {'top_id': f"Tagesordnungspunkt {folded_m.group(1)}",
                                    'nas': text, 'title': '', 'drucksachen': []}
                elif pending is not None and not pending['nas']:
                    pending['nas'] = text
            elif klasse == 'J':
                # Pattern B: "Tagesordnungspunkt 19a:" announces a subtopic
                m = re.search(r'Tagesordnungspunkt[\s\xa0]*\d+([a-z]):', text)
                if m:
                    if pending is not None:
                        subtopics.append(pending)
                    if detached_cur is not None:
                        detached_tops.append(detached_cur)
                        detached_cur = None
                    pending = _new_sub(m.group(1))
            elif klasse == 'T_fett' and not _PROCEDURAL_FETT.match(text):
                if detached_cur is not None and not detached_cur['title']:
                    detached_cur['title'] = text
                elif pending is not None and not pending['title']:
                    pending['title'] = text
            elif klasse == 'T_Drs':
                # A subtopic accumulates several Drucksachen (Entwurf, Beschlussempfehlung,
                # Entschließungsantrag, ...). Keep them all; the FIRST is the originating
                # document — never let a later line overwrite it (was: last-wins).
                for nr in re.findall(r'\d+/\d+', text):
                    if detached_cur is not None:
                        if nr not in detached_cur['drucksachen']:
                            detached_cur['drucksachen'].append(nr)
                    elif pending is not None:
                        if nr not in pending['drucksachen']:
                            pending['drucksachen'].append(nr)
                        if not pending['drucksache']:
                            pending['drucksache'] = nr
                            pending['drucksache_url'] = _drucksache_pdf_url(nr)
                    else:
                        if nr not in top_drucksachen:
                            top_drucksachen.append(nr)
                        if not top_drucksache:
                            top_drucksache = nr
                            top_drucksache_url = _drucksache_pdf_url(nr)
        if pending is not None:
            subtopics.append(pending)
        if detached_cur is not None:
            detached_tops.append(detached_cur)

        for s in subtopics:
            if not s['title'] and s['nas']:
                s['title'] = _extract_nas_title(s['nas'])

        tops[top_key] = {
            "top_key": top_key,
            "top_id": top_id,
            "title": title,
            "subtitle": subtitle,
            "session": session_id,
            "date": a_date,
            "drucksache": top_drucksache,
            "drucksache_url": top_drucksache_url,
            "drucksachen": top_drucksachen,
            "subtopics": subtopics,
        }

        for d in detached_tops:
            d_key = f"{session_id}_{d['top_id']}" if session_id else d['top_id']
            if d_key in tops:
                continue  # a standalone <tagesordnungspunkt> for this TOP wins
            d_sub = re.sub(r'^\s*\d+\s+', '', d['nas']).strip()
            d_title = d['title'] or _extract_nas_title(d_sub) or d_sub
            d_subtitle = '' if (d_sub == d_title or _procedural.match(d_sub)) else d_sub
            first = d['drucksachen'][0] if d['drucksachen'] else ''
            tops[d_key] = {
                "top_key": d_key,
                "top_id": d['top_id'],
                "title": d_title,
                "subtitle": d_subtitle,
                "session": session_id,
                "date": a_date,
                "drucksache": first,
                "drucksache_url": _drucksache_pdf_url(first) if first else '',
                "drucksachen": d['drucksachen'],
                "subtopics": [],
            }

    # Drop entries that end up with nothing to show. Usually caused by the top_id
    # fallback above picking up a stray "Tagesordnungspunkt Na" mention from an
    # unrelated Geschäftsordnungsdebatte (e.g. a motion to withdraw/postpone that TOP —
    # "... beantragt, Tagesordnungspunkt 22a abzusetzen" — session 88, 08.07.2026) whose
    # body has no T_NaS/T_fett/T_Drs at all. Such an entry can never render anything
    # useful regardless of cause, so filter defensively rather than chase every source.
    tops = {k: v for k, v in tops.items()
            if v['title'] or v['subtitle'] or v['drucksache'] or v['subtopics']}

    return tops


def _haushaltswoche_title(members: list[dict]) -> str:
    """'Bundeshaushalt 2027 – 1. Lesung' from the Einbringung / Einzelplan texts."""
    haystack = " ".join(
        " ".join([m.get("title", ""), m.get("subtitle", "")]
                 + [s.get("nas", "") + " " + s.get("title", "")
                    for s in m.get("subtopics", [])])
        for m in members
    )
    ym = re.search(r'(?:Haushaltsjahr|Haushalts(?:begleit)?gesetzes?)\s+(20\d\d)', haystack)
    year = ym.group(1) if ym else ""
    if re.search(r'\bErste Beratung\b', haystack):
        lesung = "1. Lesung"
    elif re.search(r'\bZweite (?:und dritte )?Beratung\b', haystack):
        lesung = "2./3. Lesung"
    else:
        lesung = ""
    return " – ".join(p for p in (f"Bundeshaushalt {year}".strip(), lesung) if p)


def haushaltswoche_hub_entries(tops: dict) -> dict:
    """Synthetic '{session}_Haushaltswoche' entry for every session whose tops contain
    Einzelplan debate blocks (Haushaltswoche). Shaped like a normal tops.json entry so
    the frontend route and search index need no special case; the extra `einzelplaene`
    / `einbringung` keys tell the page which real TOPs to pull together."""
    by_session: dict[str, list[str]] = {}
    for key in tops:
        if "_Einzelplan " in key:
            by_session.setdefault(key.split("_", 1)[0], []).append(key)

    hubs = {}
    for session, ep_keys in by_session.items():
        ep_keys = sorted(ep_keys)
        members = [tops[k] for k in ep_keys]
        einbringung = f"{session}_Tagesordnungspunkt 3"
        if einbringung in tops:
            members = [tops[einbringung]] + members
        hub_key = f"{session}_Haushaltswoche"
        hubs[hub_key] = {
            "top_key": hub_key,
            "top_id": "Haushaltswoche",
            "title": _haushaltswoche_title(members),
            "subtitle": "",
            "session": session,
            "date": members[0].get("date", ""),
            "drucksache": "",
            "drucksache_url": "",
            "drucksachen": [],
            "subtopics": [],
            "einzelplaene": ep_keys,
            "einbringung": einbringung if einbringung in tops else "",
        }
    return hubs


def fetch_and_parse_xml(url: str, store_it_to: str = None) -> dict:
    """
    Fetch XML from URL and parse it into a dictionary using xmltodict.
    Args:
        url: URL of the XML file
    Returns:
        Dictionary representation of the XML
    """
    print(f"Fetching XML from {url}...")
    response = requests.get(url)
    response.raise_for_status()

    print("Parsing XML with xmltodict...")
    xml_dict = xmltodict.parse(response.content)
    if store_it_to is not None:
        os.makedirs(store_it_to, exist_ok=True)
        filename = url.split("/")[-1]
        filepath = os.path.join(store_it_to, filename)
        print(f"Storing XML to {filepath}...")
        with open(filepath, "wb") as f:
            f.write(response.content)
    return xml_dict

def get_speeches_by_fraktion(xml_data: dict, fraktion: str) -> list:
    """
    Retrieve all speeches by speakers from a specific party (fraktion).
    Args:
        xml_data: The parsed XML dictionary
        fraktion: The party name (e.g., "AfD", "SPD", "CDU/CSU", "BÜNDNIS 90/DIE GRÜNEN", "Die Linke")
    Returns:
        List of speech dictionaries from speakers of the specified party
    """
    speeches = []

    def find_speeches_recursive(obj):
        """Recursively find all rede (speech) elements."""
        if isinstance(obj, dict):
            # Check if this is a rede element
            if '@id' in obj and obj.get('@id', '').startswith('ID'):
                # This looks like a speech element
                # Check if it has a speaker with the matching fraktion
                if 'p' in obj:
                    paragraphs = obj['p'] if isinstance(obj['p'], list) else [obj['p']]
                    for para in paragraphs:
                        if isinstance(para, dict) and 'redner' in para:
                            redner = para['redner']
                            if isinstance(redner, dict) and 'name' in redner:
                                name_info = redner['name']
                                if isinstance(name_info, dict) and name_info.get('fraktion') == fraktion:
                                    speeches.append(obj)
                                    break

            # Recursively search all values
            for value in obj.values():
                find_speeches_recursive(value)

        elif isinstance(obj, list):
            for item in obj:
                find_speeches_recursive(item)

    find_speeches_recursive(xml_data)
    return speeches


def extract_speech_text(speech_dict: dict) -> str:
    """
    Extract ONLY the actual speech text content (#text fields) from paragraphs.
    Excludes speaker info, XML structure markers, and metadata.
    This is what gets embedded - metadata is stored separately for filtering.
    Args:
        speech_dict: Dictionary containing speech data
    Returns:
        String containing only the speech text content (no metadata)
    """
    # Only extract #text from paragraphs, excluding speaker introductions
    text_parts = []

    if 'p' in speech_dict:
        paragraphs = speech_dict['p'] if isinstance(speech_dict['p'], list) else [speech_dict['p']]

        for para in paragraphs:
            if isinstance(para, dict):
                # Skip paragraphs that contain speaker info (redner key)
                if 'redner' in para:
                    continue

                # Only extract #text content
                if '#text' in para:
                    text = para['#text'].strip()
                    # Filter out empty text and XML class markers
                    if text and len(text) > 0:
                        text_parts.append(text)

    # Join all text parts with spaces
    return ' '.join(text_parts)


def get_speaker_info(speech_dict: dict) -> dict:
    """
    Extract speaker information from a speech.

    Args:
        speech_dict: Dictionary containing speech data

    Returns:
        Dictionary with speaker information (name, fraktion, etc.)
    """
    if 'p' in speech_dict:
        paragraphs = speech_dict['p'] if isinstance(speech_dict['p'], list) else [speech_dict['p']]
        for para in paragraphs:
            if isinstance(para, dict) and 'redner' in para:
                redner = para['redner']
                if isinstance(redner, dict) and 'name' in redner:
                    name_info = redner['name']
                    return {
                        'titel': name_info.get('titel', ''),
                        'vorname': name_info.get('vorname', ''),
                        'nachname': name_info.get('nachname', ''),
                        'fraktion': name_info.get('fraktion', '')
                    }
    return {}

def get_speeches(speeches_urls: str, speeches_csv: str):
    require_env("SPEECHES_XML_DIR")

    df = pd.DataFrame({
        'type': pd.Series(dtype='object'),
        'date': pd.Series(dtype='object'),
        'id': pd.Series(dtype='object'),
        'party': pd.Series(dtype='object'),
        'text': pd.Series(dtype='object')
    })

    all_urls = pd.read_csv(urls).iloc[:,0]

    for url in all_urls:
        xml_data = fetch_and_parse_xml(speeches_urls, SPEECHES_XML_DIR)
        data = xml_data["dbtplenarprotokoll"]["@sitzung-datum"]

        for party in PARTIES_LIST:
            sp_list = get_speeches_by_fraktion(xml_data, party)

            for speech in sp_list:
                text = extract_speech_text(speech)
                speaker_info = get_speaker_info(speech)
                df = pd.concat([df, pd.DataFrame([{
                    'type':'speech',
                    'date': data,
                    'id': speech.get('@id', ''),
                    'party': speaker_info.get('fraktion', ''),
                    'text': text
                }])], ignore_index=True)

    df.to_csv(speeches_csv)

if __name__ == "__main__":
    if len(sys.argv) > 2 and (os.path.isfile(sys.argv[2]) or os.path.isdir(sys.argv[2])):
        if sys.argv[1] == "speeches":
            print("Getting speeches...")
            get_speeches(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "vectorize":
            file_to_process = sys.argv[2]
            print(f"Vectorizing {file_to_process}...")
            time.sleep(2)
            rag = Rag()
            print(f'{rag.get_num_of_vectors()} vectors currently in the vector store.')
            time.sleep(2)
            num_of_chunks = rag.add_to_vector_store(data_source=file_to_process)
            print(f"Embedded {num_of_chunks} chunks into the vector store.")
            print(f'{rag.get_num_of_vectors()} vectors currently in the vector store.')
        elif sys.argv[1] == "xml":
            dir_to_process = sys.argv[2]
            save_to_cvs = sys.argv[3]

            entries = os.listdir(dir_to_process)
            files = [os.path.join(dir_to_process, f) \
                    for f in entries if os.path.isfile(os.path.join(dir_to_process, f))]
            df = pd.DataFrame(columns = ['date','id','party','text'])
            for file in files:
                print(f'Processing {file}')
                process_bundestag_xml(file, df)
            df.to_csv(save_to_cvs)
