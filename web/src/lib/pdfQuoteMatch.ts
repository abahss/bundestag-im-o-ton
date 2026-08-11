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
  const q = normalizeQuote(quoteText);
  if (!q) return null;

  for (let p = 1; p <= doc.numPages; p++) {
    const page = await doc.getPage(p);
    const content = await page.getTextContent();
    const items = content.items.filter((it): it is TextItem => "str" in it);
    const { raw, charItemIndex, charOffsetInItem } = buildPageIndex(items);
    const { normalized, map } = normalizeForSearch(raw);
    const idx = normalized.indexOf(q);
    if (idx === -1) continue;

    const rawStart = map[idx];
    const rawEnd = map[idx + q.length - 1] + 1;

    const perItem = new Map<number, { min: number; max: number }>();
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

    const boxes: PdfBox[] = [];
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

    return { pageNumber: p, boxes };
  }
  return null;
}
