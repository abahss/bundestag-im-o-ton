"""Matches an LLM-generated quote against the speech chunks it was drawn from,
so the citation ID attached to a quote is always the one it actually came from
— never trust the model to copy an ID correctly. Mirrors quote_needles /
fold_for_match / findQuoteInPdf's needle search in web/src/lib/pdfQuoteMatch.ts;
fold_for_match and quote_needles are pinned against the same cases in both
languages via /fixtures/quote-matching.json.
"""

import re

TYPOGRAPHIC = {
    "„": '"',
    "“": '"',  # "
    "”": '"',  # "
    "‘": "'",  # '
    "’": "'",  # '
}

ELISION = re.compile(r"\[\s*(?:\.\.\.|…)\s*\]|…")
TRIMMABLE = " .,!?;:…\"'-–—"


def fold_for_match(text: str) -> str:
    """Folds typographic quote marks and case, leaving whitespace untouched."""
    for typo, plain in TYPOGRAPHIC.items():
        text = text.replace(typo, plain)
    return text.lower()


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def quote_needles(quote_text: str) -> list[str]:
    """Splits a quote at its elision markers into the segments that must each
    appear, in order, in the source text. The model marks a stitch between two
    non-adjacent parts of a speech with "[...]", "[…]" or a bare "…", and
    cleans up punctuation at the cut points, so each segment is
    punctuation-trimmed before matching."""
    normalized = _collapse_whitespace(quote_text)
    segments = ELISION.split(normalized)
    needles = [fold_for_match(seg).strip(TRIMMABLE) for seg in segments]
    return [needle for needle in needles if needle]


def attach_citation_ids(text: str, chunks: list[tuple[str, str]]) -> str:
    """Replace whatever ID the LLM echoed after each quote with the real ID of
    the chunk that quote actually came from, found by substring match. Drops
    the whole quote line if no chunk matches (e.g. the quote was paraphrased
    rather than exact) — an unverifiable quote is worse than no quote, since it
    looks sourced but isn't."""
    normalized_chunks = [
        (fold_for_match(_collapse_whitespace(doc)), cid) for doc, cid in chunks
    ]
    out_lines = []
    for line in text.splitlines():
        m = re.match(r'^(\*"(.+)"\*)\s*(?:\[[^\]]*\])?\s*$', line.strip())
        if not m:
            out_lines.append(line)
            continue
        quote_part, quote_text = m.group(1), m.group(2)
        needles = quote_needles(quote_text)
        found_id = None
        for norm_doc, cid in normalized_chunks:
            pos = 0
            for needle in needles:
                idx = norm_doc.find(needle, pos)
                if idx == -1:
                    break
                pos = idx + len(needle)
            else:
                found_id = cid
                break
        if found_id:
            out_lines.append(f"{quote_part} [{found_id}]")
    return "\n".join(out_lines)
