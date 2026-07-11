"""
Build data/tops.json from already-downloaded XMLs in data/xml_updates/.
Classifies each TOP into a synthesized topic using Gemini (no predefined categories).
Usage: uv run python bin/build_tops_json.py
"""
import json
import re
from pathlib import Path
from langchain.chat_models import init_chat_model
from practicepreach.tools import build_tops_lookup

XML_DIR = Path("data/xml_updates")
TOPS_JSON = Path("data/tops.json")

model = init_chat_model("google_genai:gemini-2.5-flash-lite")

_generic = re.compile(r'^(Tagesordnungspunkt|Zusatzpunkt|TOP|ZP)\s*\d+', re.IGNORECASE)


def classify_tops(tops: dict) -> dict:
    """Send TOP titles to Gemini. Re-classifies entries where Gemini previously echoed the key."""
    to_classify = {
        k: v for k, v in tops.items()
        if not v.get("topic") or _generic.match(v.get("topic", "")) or len(v.get("topic", "")) > 60
    }
    if not to_classify:
        return {}

    def _label(v):
        if v.get('title'):
            return v['title']
        if v.get('subtitle'):
            return v['subtitle']
        subs = v.get('subtopics') or []
        titles = [s['title'] for s in subs if s.get('title')]
        return '; '.join(titles[:3]) if titles else '(kein Titel)'

    lines = "\n".join(
        f"{k}: {_label(v).strip()}"
        for k, v in to_classify.items()
    )

    response = model.invoke(
        "Du bekommst eine Liste von Bundestagstagesordnungspunkten mit ihren Titeln.\n"
        "Weise jedem Punkt ein kurzes, konsistentes Thema zu (2–4 Wörter auf Deutsch).\n"
        "Verwende gleiche Themen für inhaltlich verwandte Punkte.\n"
        "Antworte im Format: top_key: Thema — eine Zeile pro Punkt, keine Erklärungen.\n\n"
        + lines
    )

    result = {}
    for line in response.content.strip().splitlines():
        if ": " in line:
            key, _, topic = line.partition(": ")
            key = key.strip()
            if key in to_classify:
                result[key] = topic.strip()
    return result


tops = {}
for xml_file in sorted(XML_DIR.glob("*.xml")):
    tops.update(build_tops_lookup(str(xml_file)))

topics = classify_tops(tops)
for key, topic in topics.items():
    tops[key]["topic"] = topic
    print(f"  {key}: {topic}")

# Fallback: if Gemini still returned a generic label, use the real title instead
for key, v in tops.items():
    current = v.get("topic", "")
    if not current or _generic.match(current):
        fallback = (v.get("title") or v.get("subtitle") or "").strip()
        if fallback and not _generic.match(fallback):
            tops[key]["topic"] = fallback[:80]
            print(f"  [fallback] {key}: {fallback[:80]}")

TOPS_JSON.write_text(json.dumps(tops, ensure_ascii=False, indent=2))
print(f"Saved {TOPS_JSON} ({len(tops)} TOPs)")
