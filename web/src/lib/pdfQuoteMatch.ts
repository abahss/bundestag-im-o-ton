import type { PDFDocumentProxy } from "pdfjs-dist";
import type { TextItem } from "pdfjs-dist/types/src/display/api";

// Finds a quote (an LLM-generated, single-spaced sentence) inside a real
// PDF's text layer, even when it wraps across lines or a word is split by
// line-wrap hyphenation. See pdfQuoteMatch.test.ts for the validated edge
// cases (word-wrap, hyphenation removal vs. real hyphens, multi-page search).

interface PageIndex {
  raw: string;
  charItemIndex: (number | null)[]; // per raw char: index into `items`, or null for an injected line break
  charOffsetInItem: (number | null)[]; // per raw char: offset within that item's str
}

function buildPageIndex(items: TextItem[]): PageIndex {
  let raw = "";
  const charItemIndex: (number | null)[] = [];
  const charOffsetInItem: (number | null)[] = [];
  items.forEach((item, itemIdx) => {
    for (let i = 0; i < item.str.length; i++) {
      raw += item.str[i];
      charItemIndex.push(itemIdx);
      charOffsetInItem.push(i);
    }
    if (item.hasEOL) {
      raw += "\n";
      charItemIndex.push(null);
      charOffsetInItem.push(null);
    }
  });
  return { raw, charItemIndex, charOffsetInItem };
}

function isLineBreakAt(raw: string, i: number) {
  return raw[i] === "\n" || (raw[i] === "\r" && raw[i + 1] === "\n");
}
function skipLineBreak(raw: string, i: number) {
  return raw[i] === "\r" ? i + 2 : i + 1;
}

/** Collapses whitespace to single spaces and drops line-wrap hyphenation (a
 * hyphen immediately before a line break), while leaving mid-line hyphens
 * (e.g. "Rot-Grün-Koalition") untouched. Returns a map from normalized-string
 * index back to the raw-string index it came from. */
function normalizeForSearch(raw: string) {
  let normalized = "";
  const map: number[] = [];
  let i = 0;
  while (i < raw.length) {
    const ch = raw[i];
    if (ch === "-" && isLineBreakAt(raw, i + 1)) {
      i = skipLineBreak(raw, i + 1);
      while (raw[i] === " " || raw[i] === "\t") i++;
      continue;
    }
    if (/\s/.test(ch)) {
      if (normalized[normalized.length - 1] !== " ") {
        normalized += " ";
        map.push(i);
      }
      i++;
      while (i < raw.length && /\s/.test(raw[i])) i++;
      continue;
    }
    normalized += ch;
    map.push(i);
    i++;
  }
  return { normalized, map };
}

function normalizeQuote(quote: string) {
  return quote.replace(/\s+/g, " ").trim();
}

const TYPOGRAPHIC: Record<string, string> = {
  "„": '"',
  "“": '"',
  "”": '"',
  "‘": "'",
  "’": "'",
};

/** Folds case and typographic quote marks *without changing string length*, so
 * an index into the folded string still points at the same character in the
 * original — the raw-index map depends on that. A handful of Unicode chars
 * (e.g. "İ") grow when lowercased; those are left unfolded rather than break
 * the mapping. Mirrors `_normalize_for_match` in backend/practicepreach/rag.py:
 * the LLM does not reliably reproduce the original's capitalisation. */
function foldForMatch(s: string) {
  let out = "";
  for (const ch of s) {
    const canon = TYPOGRAPHIC[ch] ?? ch;
    const lower = canon.toLowerCase();
    out += lower.length === canon.length ? lower : canon;
  }
  return out;
}

// Real summaries use all three spellings of the marker: "[...]", "[…]" and a
// bare "…". The bracketed forms must be matched before the bare one, or the
// brackets survive as stray characters inside the segments and nothing matches.
// A bare "..." is deliberately not a marker — it occurs as ordinary punctuation.
const ELISION = /\[\s*(?:\.\.\.|…)\s*\]|…/;
const TRIMMABLE = new Set([" ", ".", ",", "!", "?", ";", ":", "…", '"', "'", "-", "–", "—"]);

function trimPunctuation(s: string) {
  let start = 0;
  let end = s.length;
  while (start < end && TRIMMABLE.has(s[start])) start++;
  while (end > start && TRIMMABLE.has(s[end - 1])) end--;
  return s.slice(start, end);
}

/** Splits a quote at its elision markers into the segments that must each
 * appear, in order, in the PDF. The LLM marks a stitch between two
 * non-adjacent parts of a speech with "[...]" or "…", and cleans up punctuation
 * at the cut points, so each segment is punctuation-trimmed before matching —
 * same contract as `_attach_citation_ids` in rag.py. */
function quoteNeedles(quoteText: string) {
  return normalizeQuote(quoteText)
    .split(ELISION)
    .map((segment) => trimPunctuation(foldForMatch(segment).trim()))
    .filter((segment) => segment.length > 0);
}

export interface PdfBox {
  /** PDF user-space coordinates (origin bottom-left), not screen pixels. */
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PdfQuoteMatch {
  pageNumber: number; // 1-based
  boxes: PdfBox[];
}

/** Searches every page of `doc` for `quoteText`, returning the first match's
 * page number and the bounding box(es) of the matched text (one box per
 * text item touched, clipped to the matched character range within each
 * item so a partially-matched item doesn't over-highlight). */
export async function findQuoteInPdf(
  doc: PDFDocumentProxy,
  quoteText: string
): Promise<PdfQuoteMatch | null> {
  const needles = quoteNeedles(quoteText);
  if (!needles.length) return null;

  for (let p = 1; p <= doc.numPages; p++) {
    const page = await doc.getPage(p);
    const content = await page.getTextContent();
    const items = content.items.filter((it): it is TextItem => "str" in it);
    const { raw, charItemIndex, charOffsetInItem } = buildPageIndex(items);
    const { normalized, map } = normalizeForSearch(raw);
    const haystack = foldForMatch(normalized);

    // Every segment must appear, in order and without overlapping, on this
    // page. Their ranges are collected separately so the elided material
    // between them isn't highlighted as if it were part of the quote.
    const ranges: { start: number; end: number }[] = [];
    let searchFrom = 0;
    for (const needle of needles) {
      const idx = haystack.indexOf(needle, searchFrom);
      if (idx === -1) {
        ranges.length = 0;
        break;
      }
      ranges.push({ start: idx, end: idx + needle.length });
      searchFrom = idx + needle.length;
    }
    if (!ranges.length) continue;

    // Boxes are built per segment, not per page: two segments sharing one text
    // item (an elision skipping words mid-line) must stay two boxes, otherwise
    // a single min/max span would highlight the skipped words as if quoted.
    const boxes: PdfBox[] = [];
    for (const { start, end } of ranges) {
      const perItem = new Map<number, { min: number; max: number }>();
      const rawStart = map[start];
      const rawEnd = map[end - 1] + 1;
      for (let i = rawStart; i < rawEnd; i++) {
        const itemIdx = charItemIndex[i];
        if (itemIdx === null) continue;
        const off = charOffsetInItem[i]!;
        const cur = perItem.get(itemIdx);
        if (!cur) perItem.set(itemIdx, { min: off, max: off });
        else {
          cur.min = Math.min(cur.min, off);
          cur.max = Math.max(cur.max, off);
        }
      }

      for (const [itemIdx, { min, max }] of perItem) {
        const item = items[itemIdx];
        const len = item.str.length;
        const startFrac = len > 0 ? min / len : 0;
        const endFrac = len > 0 ? (max + 1) / len : 1;
        const x0 = item.transform[4];
        const y0 = item.transform[5];
        const totalWidth = item.width;
        const height = item.height || Math.abs(item.transform[3]) || 10;
        boxes.push({
          x: x0 + totalWidth * startFrac,
          y: y0,
          width: totalWidth * (endFrac - startFrac),
          height,
        });
      }
    }

    return { pageNumber: p, boxes };
  }
  return null;
}
