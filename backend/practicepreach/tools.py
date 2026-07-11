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
    for punkt in root.findall("./sitzungsverlauf/tagesordnungspunkt"):
        top_id = punkt.get("top-id", "").replace('\xa0', ' ')
        if top_id and not re.search(r'\d', top_id):
            for p in punkt.findall("./p[@klasse='J']"):
                text = ''.join(p.itertext()).strip()
                m = re.search(r'(Tagesordnungspunkt|Zusatzpunkt)[\s\xa0]+(\d+)', text)
                if m:
                    top_id = f"{m.group(1)} {m.group(2)}"
                    break
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
    m = re.search(r'(Entwurfs? eines (?:[\w\.]+\s+)*Gesetzes\s.+)', nas, re.DOTALL)
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


def build_tops_lookup(url: str) -> dict:
    """
    Extract TOP metadata from an XML file.
    Returns dict: {top_key: {top_id, title, session, date}}
    """
    tree = ET.parse(url)
    root = tree.getroot()

    a_date = root.attrib['sitzung-datum']
    session_id = root.attrib.get('sitzung-nr', '')

    tops = {}
    for punkt in root.findall("./sitzungsverlauf/tagesordnungspunkt"):
        top_id = punkt.get("top-id", "").replace('\xa0', ' ')
        if not top_id:
            continue
        if not re.search(r'\d', top_id):
            for p in punkt.findall("./p[@klasse='J']"):
                text = ''.join(p.itertext()).strip()
                m = re.search(r'(Tagesordnungspunkt|Zusatzpunkt)[\s\xa0]+(\d+)', text)
                if m:
                    top_id = f"{m.group(1)} {m.group(2)}"
                    break
        top_key = f"{session_id}_{top_id}" if session_id else top_id
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
            if klasse in ('T_NaS', 'T_ZP_NaS'):
                if re.match(r'^\s*(?:\d+\s+)?[a-z]\)', text):
                    break  # Pattern A subtopic — stop
                if t_nas is None:
                    t_nas = child
            elif klasse == 'T_fett':
                t_fett = child
            elif klasse == 'J':
                if re.search(r'Tagesordnungspunkt[\s\xa0]*\d+[a-z]:', text):
                    break  # Pattern B subtopic — stop

        title = t_fett.text.strip() if t_fett is not None and t_fett.text else _clean(t_nas)
        subtitle = _clean(t_nas)
        # Strip procedural-only subtitles that carry no content value
        _procedural = re.compile(
            r'^(Vereinbarte Debatte:?|Aktuelle Stunde|Fragestunde|Befragung der Bundesregierung)$',
            re.IGNORECASE
        )
        if _procedural.match(subtitle):
            subtitle = ""

        # Parse subtopics (a, b, c...) with Drucksache references.
        # Pattern A: T_NaS starts with "a)" / "18 a)" (shared debate, e.g. TOP 18)
        # Pattern B: J element announces "Tagesordnungspunkt 19a:" (sequential items, e.g. TOP 19)
        subtopics = []
        pending = None
        top_drucksache = ''
        top_drucksache_url = ''
        for child in list(punkt):
            if child.tag == 'rede':
                break
            if child.tag != 'p':
                continue
            klasse = child.get('klasse', '')
            text = ''.join(child.itertext()).strip()
            if klasse in ('T_NaS', 'T_ZP_NaS'):
                m = re.match(r'^\s*(?:\d+\s+)?([a-z])\)', text)
                if m:
                    letter = m.group(1)
                    if pending is not None and pending['key'] == letter and not pending['nas']:
                        # Pattern B already opened this subtopic — fill in the NaS instead of duplicating
                        pending['nas'] = text
                    else:
                        # Pattern A: new subtopic
                        if pending is not None:
                            subtopics.append(pending)
                        pending = {'key': letter, 'nas': text, 'title': '', 'drucksache': '', 'drucksache_url': ''}
                elif pending is not None and not pending['nas']:
                    pending['nas'] = text
            elif klasse == 'J':
                # Pattern B: "Tagesordnungspunkt 19a:" announces a subtopic
                m = re.search(r'Tagesordnungspunkt[\s\xa0]*\d+([a-z]):', text)
                if m:
                    if pending is not None:
                        subtopics.append(pending)
                    pending = {'key': m.group(1), 'nas': '', 'title': '', 'drucksache': '', 'drucksache_url': ''}
            elif klasse == 'T_fett' and pending is not None:
                if not pending['title']:
                    pending['title'] = text
            elif klasse == 'T_Drs':
                dr_m = re.search(r'(\d+/\d+)', text)
                if dr_m:
                    nr = dr_m.group(1)
                    if pending is not None:
                        pending['drucksache'] = nr
                        pending['drucksache_url'] = _drucksache_pdf_url(nr)
                    elif not top_drucksache:
                        top_drucksache = nr
                        top_drucksache_url = _drucksache_pdf_url(nr)
        if pending is not None:
            subtopics.append(pending)

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
            "subtopics": subtopics,
        }

    return tops

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
