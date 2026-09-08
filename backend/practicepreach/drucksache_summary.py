"""Generate a neutral "was schlägt die Vorlage vor"-summary for a single Drucksache.

Phase 2 of the Drucksachen-Zusammenfassung plan (memory project_drucksache_summary_plan).
No ChromaDB / embeddings: DIP full text -> Gemini 2.5 Flash -> {im_kern, punkte}.
Metadata (typ / urheber / datum / titel / pdf_url) comes straight from DIP, never guessed.

The batch runner `bin/batch_drucksache_summaries.py` calls `summarize_drucksache()` over
a whole session so the wording can be reviewed; the later `/drucksache-summary` endpoint
will call the same function on a cache miss.
"""
import re
from datetime import datetime, timezone

import requests
from langchain.chat_models import init_chat_model

from practicepreach.constants import LESBARKEITS_REGELN
from practicepreach.drucksache_verify import BASE, fetch_dip
from practicepreach.params import BUNDESTAG_API_KEY, GOOGLE_API_KEY
from practicepreach.tools import _drucksache_pdf_url

# Characters of prepared text handed to the LLM. Anträge are 2-3 pages; long
# Gesetzentwürfe run to hundreds of pages (21/6279 had 641k chars). Before capping,
# `_prepare_text` throws away the parts that carry no proposal content (see below);
# a Gesetzentwurf whose operative part still exceeds this gets `truncated=True` and the
# frontend shows the approved "nur der Anfang wurde ausgewertet"-warning. Map-Reduce for
# the ones that overflow even after preparation is Phase 2b.
TEXT_CAP = 60_000

GEN_DRUCKSACHE = (
    "Du bist ein neutraler Analyst. Fasse zusammen, WAS die folgende Bundestags-Drucksache "
    "vorschlägt – nicht, wie sie zu bewerten ist, und nicht, wie im Plenum darüber debattiert wurde.\n\n"
    "Dokumenttyp: {typ}\n"
    "Urheber: {urheber}\n"
    "Titel: {titel}\n\n"
    "WICHTIG bei Gesetzentwürfen: Das Vorblatt (Abschnitt A \"Problem und Ziel\", B \"Lösung\") "
    "beschreibt nur die Absicht. Die konkreten Regelungen stehen im Artikelteil (Artikel 1, "
    "Artikel 2 usw.) und in der Inhaltsübersicht davor. Prüfe diesen Teil und wähle mindestens "
    "die Hälfte der Punkte aus konkreten Einzelregelungen dort, nicht nur aus dem Vorblatt. "
    "Falls der Artikelteil im vorliegenden Text fehlt oder abgeschnitten ist, sag das nicht "
    "extra, sondern fasse einfach nur zusammen, was tatsächlich vorliegt.\n\n"
    "Antworte AUSSCHLIESSLICH in diesem Format:\n\n"
    "**Im Kern:** [ein bis zwei Sätze: wer will was erreichen – das übergeordnete Ziel der Vorlage]\n\n"
    "- [eine konkrete Forderung bzw. Regelung der Vorlage, ein Satz, höchstens 15 Wörter]\n"
    "- [eine konkrete Forderung bzw. Regelung der Vorlage, ein Satz, höchstens 15 Wörter]\n"
    "- [weitere Punkte, je ein Satz mit höchstens 15 Wörtern – HÖCHSTENS SECHS Punkte, auch bei "
    "sehr umfangreichen Vorlagen; bündle dann verwandte Einzelregelungen zu einem Punkt und wähle "
    "die mit der größten praktischen Tragweite. Nach praktischer Tragweite für Betroffene geordnet.]\n\n"
    + LESBARKEITS_REGELN + "\n\n"
    "Regeln:\n"
    "- Nur der Inhalt der Vorlage. Keine Einordnung, kein Für und Wider, keine Reaktionen, "
    "kein Vorwissen von außen.\n"
    "- Bei einem Antrag: die Forderungen an die Bundesregierung, nicht die Feststellungen "
    "oder Begründungen, mit denen der Antrag sie stützt.\n"
    "- Bei einem Gesetzentwurf: was geregelt oder geändert wird und ab wann es gelten soll, "
    "mit Schwerpunkt auf den Artikeln, nicht nur dem Vorblatt.\n"
    "- So konkret wie die Vorlage selbst: übernimm Zahlen, Fristen, Beträge, Alters- und "
    "Schwellenwerte wörtlich, wenn sie im Text stehen.\n"
    "- Lass Kosten- und Aufwandsangaben weg (Erfüllungsaufwand für Bürger, Wirtschaft und "
    "Verwaltung, Bürokratiekosten, Planstellen, Haushaltsausgaben) – es sei denn, ein "
    "Betrag ist selbst Gegenstand der Regelung (z. B. eine Fördersumme, ein Zuschuss, eine "
    "Abgabenhöhe).\n"
    "- Lass reine Verfahrens- und Begründungsformeln weg (\"Der Bundestag wolle beschließen\", "
    "Verweise auf Anlagen, Federführung, Zuleitung an den Bundesrat).\n"
    "- Sachlich und parteiunabhängig. KEIN einziges Anführungszeichen – gib alles in eigenen "
    "Worten wieder, übernimm keine Wortgruppen aus dem Dokument.\n"
    "- Im Zweifel lieber ein Detail weglassen als einen Punkt aufblähen.\n"
    "- Falls der Text sichtbar abgeschnitten endet: fasse nur zusammen, was vorliegt, und "
    "erfinde nichts.\n\n"
    "Drucksachentext:\n\n{text}"
)


class DrucksacheNotAvailable(Exception):
    """DIP has no metadata or no machine-readable full text for this number."""


# --- Text preparation ------------------------------------------------------------------
#
# DIP's /drucksache-text is already free of the repeating page headers you see in the PDF
# ("Deutscher Bundestag - 21. Wahlperiode - 14 - Drucksache ...") — measured: "Wahlperiode"
# appears once in a 407k-char Gesetzentwurf. What is still dead weight for a "was schlägt
# die Vorlage vor"-summary, and roughly how big (measured on session-90 Gesetzentwürfen):
#
#   trailing Impressum ("Gesamtherstellung: H. Heenemann ...")          ~300 chars
#   the cover letter to the Bundestagspräsidentin (+ chancellor/        ~1-2k chars,
#     ministry names, which must not leak into the summary)               and misleading
#   Vorblatt sections C-F (Alternativen / Haushaltsausgaben /            6-13k chars,
#     Erfüllungsaufwand / Weitere Kosten) — extremely boilerplate-heavy    near-zero value
#   the Begründung / Besonderer Teil (article-by-article rationale)      often > half the
#                                                                          document
#
# `_prepare_text` drops all of that for a Gesetzentwurf and hands the model
# [Titel + Vorblatt A/B + Inhaltsübersicht + Artikeltext], so the cap is spent on the
# actual new provisions. Anträge have none of this structure and are short — they only get
# the Impressum strip. If the structure markers are missing the whole restructuring is
# skipped and the raw text is capped as before.

_RE_VORBLATT_A = re.compile(r"(?m)^[ \t]*A\.[ \t]+Problem\b")
_RE_VORBLATT_C = re.compile(r"(?m)^[ \t]*C\.[ \t]+Alternativen\b")
_RE_VORBLATT_D = re.compile(r"(?m)^[ \t]*D\.[ \t]+Haushaltsausgaben\b")
# "Der Bundestag hat [mit der Mehrheit ... und mit Zustimmung des Bundesrates] das
# folgende Gesetz beschlossen:" — the middle clause varies, and "folgende\nGesetz" can
# wrap, so keep the pattern loose but single-line for the variable part.
_RE_BESCHLOSSEN = re.compile(r"Der Bundestag hat[^\n]{0,90}?das folgende\s+Gesetz beschlossen\s*:")
_RE_BEGRUENDUNG = re.compile(r"(?m)^[ \t]*Begründung[ \t]*$")
_RE_IMPRESSUM = re.compile(r"(?m)^[ \t]*(?:Gesamtherstellung|Vertrieb)[ \t]*:")
# The cover letter to the Bundestagspräsidentin: procedural, and it names the chancellor
# and lead ministries, which must not bleed into the summary. Bounded so it can never eat
# real content; Fraktion drafts have no such block and the sub() is a no-op.
_RE_ANSCHREIBEN = re.compile(
    r"\n?(?:BUNDESREPUBLIK DEUTSCHLAND|An die\s*\n\s*Präsident(?:in)? des)"
    r".{0,4000}?Mit freundlichen Grüßen[ \t]*\n[^\n]*\n",
    re.DOTALL,
)

# A restructured text this much smaller than a plain cap is almost certainly a mis-parse
# (a heading matched in the wrong place) — fall back rather than starve the model.
_MIN_RESTRUCTURED = 20_000


def _strip_impressum(t: str) -> str:
    m = _RE_IMPRESSUM.search(t, max(0, len(t) - 3000))
    return t[: m.start()].rstrip() if m else t


def _strip_anschreiben(t: str) -> str:
    return _RE_ANSCHREIBEN.sub("\n", t, count=1)


def _restructure_gesetzentwurf(t: str) -> str | None:
    """[Titel + Vorblatt A/B + Artikeltext], cover letter / C-F / Begründung removed.

    Returns None when neither the "... das folgende Gesetz beschlossen:" marker nor a
    "Begründung" heading is found, or when the result looks implausibly short.
    """
    m_beg = _RE_BEGRUENDUNG.search(t)
    m_besch = _RE_BESCHLOSSEN.search(t)
    if not (m_beg or m_besch):
        return None

    operative_end = m_beg.start() if m_beg else len(t)

    m_a = _RE_VORBLATT_A.search(t, 0, operative_end)
    m_cd = None
    if m_a:
        m_cd = (_RE_VORBLATT_C.search(t, m_a.end(), operative_end)
                or _RE_VORBLATT_D.search(t, m_a.end(), operative_end))
    head = t[: (m_cd.start() if m_cd else m_a.end())].rstrip() if m_a \
        else t[: min(400, operative_end)].rstrip()

    if m_besch and m_besch.start() < operative_end:
        body_start = m_besch.start()          # clean: straight to the Artikeltext
    elif m_cd:
        body_start = m_cd.start()             # no marker: at least skip Vorblatt A/B dup
    elif m_a:
        body_start = m_a.end()
    else:
        body_start = len(head)
    body = t[body_start:operative_end].strip()

    assembled = f"{head}\n\n{body}".strip()
    if len(assembled) < _MIN_RESTRUCTURED and len(assembled) < 0.5 * min(len(t), TEXT_CAP):
        return None
    return assembled


def _prepare_text(text: str, typ: str) -> tuple[str, dict]:
    """Trim dead weight, then cap. Second return value is instrumentation for the batch
    review (not shown to users): how long the document was and how much the model saw."""
    original = len(text)
    t = _strip_anschreiben(_strip_impressum(text))
    restructured = False
    if "gesetz" in typ.lower():
        r = _restructure_gesetzentwurf(t)
        if r is not None:
            t, restructured = r, True
    info = {
        "text_chars_original": original,
        "text_chars_prepared": len(t),
        "text_chars_sent": min(len(t), TEXT_CAP),
        "restructured": restructured,
    }
    return t[:TEXT_CAP], info


_model = None


def _get_model():
    global _model
    if _model is None:
        _model = init_chat_model(
            "google_genai:gemini-2.5-flash",
            google_api_key=GOOGLE_API_KEY,
            thinking_budget=0,
            temperature=0,
        )
    return _model


def fetch_drucksache_text(nr: str) -> str:
    """Plain-text body of the Drucksache from DIP, or '' if DIP has none."""
    url = f"{BASE}/drucksache-text?f.dokumentnummer={nr}&apikey={BUNDESTAG_API_KEY}"
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    docs = r.json().get("documents", [])
    return docs[0].get("text", "") if docs else ""


def _fmt_datum(iso: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else (iso or "")


def _parse_summary(raw: str) -> tuple[str, list[str]]:
    im_kern = ""
    punkte: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("**Im Kern:**"):
            im_kern = line[len("**Im Kern:**"):].strip()
        elif line.startswith("- "):
            punkte.append(line[2:].strip())
        elif line.startswith("* "):
            punkte.append(line[2:].strip())
    return im_kern, punkte


def summarize_drucksache(nr: str) -> dict:
    """Fetch DIP text + metadata for one Drucksachennummer and summarise the proposal.

    Returns a dict ready for `data/drucksache_summaries.json` (key = nr). Raises
    `DrucksacheNotAvailable` when DIP has no metadata or no full text (PDF fallback is
    not implemented yet — the batch run tells us how often that actually happens).
    """
    meta = fetch_dip(nr)
    if not meta:
        raise DrucksacheNotAvailable(f"DIP hat keine Metadaten zu {nr}")

    typ = meta.get("drucksachetyp") or "Drucksache"
    urheber = ", ".join(
        u.get("titel", "") for u in meta.get("urheber", []) if u.get("titel")
    ) or "—"
    titel = meta.get("titel", "")
    datum = _fmt_datum(meta.get("datum", ""))
    pdf_url = (meta.get("fundstelle") or {}).get("pdf_url") or _drucksache_pdf_url(nr)

    raw_text = fetch_drucksache_text(nr)
    if not raw_text.strip():
        raise DrucksacheNotAvailable(f"DIP hat keinen Volltext zu {nr}")
    text, prep = _prepare_text(raw_text, typ)
    truncated = prep["text_chars_prepared"] > TEXT_CAP

    prompt = (
        GEN_DRUCKSACHE
        .replace("{typ}", typ)
        .replace("{urheber}", urheber)
        .replace("{titel}", titel)
        .replace("{text}", text)
    )
    raw = _get_model().invoke(prompt).content
    im_kern, punkte = _parse_summary(raw)

    return {
        "nummer": nr,
        "typ": typ,
        "urheber": urheber,
        "datum": datum,
        "titel": titel,
        "pdf_url": pdf_url,
        "im_kern": im_kern,
        "punkte": punkte,
        "truncated": truncated,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prep": prep,  # instrumentation for batch review; the endpoint can drop it later
        "raw": raw,  # kept for prompt iteration; the endpoint can drop it later
    }


# Fields sent to the frontend — everything else (raw model output, prep instrumentation,
# an `error` marker) stays server-side.
PUBLIC_FIELDS = (
    "nummer", "typ", "urheber", "datum", "titel", "pdf_url",
    "im_kern", "punkte", "truncated", "generated_at",
)


def public_view(entry: dict) -> dict:
    """Cache entry -> API response shape."""
    return {k: entry[k] for k in PUBLIC_FIELDS if k in entry}


def top_verified_drucksache_numbers(top: dict) -> list[str]:
    """This one TOP's verified canonical Drucksachennummern (top-level + subtopics),
    in reading order, de-duplicated."""
    nrs: list[str] = []
    if top.get("drucksache") and top.get("drucksache_verified"):
        nrs.append(top["drucksache"])
    for sub in top.get("subtopics", []):
        if sub.get("drucksache") and sub.get("drucksache_verified"):
            nrs.append(sub["drucksache"])
    return list(dict.fromkeys(nrs))


def drucksache_context_for_top(top: dict, cache: dict) -> str:
    """The TOP's Drucksachen-Zusammenfassung(en) as a plain-text block, to hand the
    general summary as "do not repeat this" context. Empty string when none of the TOP's
    verified Drucksachen has a usable summary in the cache yet — the caller then falls
    back to the pre-Variante-D general-summary prompt."""
    blocks: list[str] = []
    for nr in top_verified_drucksache_numbers(top):
        entry = cache.get(nr)
        if not entry or entry.get("error") or not entry.get("im_kern"):
            continue
        lines = [f"Drucksache {nr}: {entry['im_kern']}"]
        lines += [f"- {p}" for p in entry.get("punkte", [])]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def verified_drucksache_numbers(tops: dict, active_keys: set[str] | None = None) -> set[str]:
    """Every canonical Drucksachennummer in tops.json whose DIP match was confirmed
    (`drucksache_verified` is True, written by bin/verify_tops_drucksachen.py). Only
    these get a generated summary — unverified ones show a PDF link only.

    Pass `active_keys` (TOP keys with speeches in the vector store) to restrict to
    Drucksachen tied to a currently reachable TOP — used by the prewarm so it does not
    backfill summaries for pruned old sessions. The endpoint omits it: if something is
    requested, generate it."""
    nrs: set[str] = set()
    for top_key, top in tops.items():
        if active_keys is not None and top_key not in active_keys:
            continue
        if top.get("drucksache") and top.get("drucksache_verified"):
            nrs.add(top["drucksache"])
        for sub in top.get("subtopics", []):
            if sub.get("drucksache") and sub.get("drucksache_verified"):
                nrs.add(sub["drucksache"])
    return nrs
