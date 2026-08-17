import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { describe, expect, test } from "vitest";
import { findQuoteInPdf, quoteNeedles } from "./pdfQuoteMatch";
import type { PDFDocumentProxy } from "pdfjs-dist";
import type { TextItem } from "pdfjs-dist/types/src/display/api";

// Shared with backend/practicepreach/test_quote_matching.py, which pins the
// Python port of quoteNeedles (quote_needles) against the same cases.
interface QuoteMatchingCase {
  name: string;
  quote: string;
  needles: string[];
  knownGap?: boolean;
  reason?: string;
}
const fixturesDir = path.dirname(fileURLToPath(import.meta.url));
const fixturesPath = path.resolve(fixturesDir, "../../../fixtures/quote-matching.json");
const quoteMatchingCases: QuoteMatchingCase[] = JSON.parse(readFileSync(fixturesPath, "utf-8"));

// Builds a fake pdf.js document from pages of raw lines, mirroring how a real
// PDF's text layer arrives as one TextItem per line with `hasEOL` marking a
// line break after it (not embedded `\n` characters in `str`).
function fakeDoc(pages: string[][]): PDFDocumentProxy {
  const fakePages = pages.map((lines) => {
    const items: TextItem[] = lines.map((line, i) => ({
      str: line,
      dir: "ltr",
      width: line.length * 6,
      height: 10,
      transform: [1, 0, 0, 1, 50, 700 - i * 14],
      fontName: "f1",
      hasEOL: i < lines.length - 1,
    })) as TextItem[];
    return { getTextContent: async () => ({ items, styles: {}, lang: null }) };
  });
  return {
    numPages: fakePages.length,
    getPage: async (p: number) => fakePages[p - 1],
  } as unknown as PDFDocumentProxy;
}

describe("quoteNeedles (shared fixture)", () => {
  for (const c of quoteMatchingCases) {
    const runner = c.knownGap ? test.fails : test;
    runner(c.name, () => {
      expect(quoteNeedles(c.quote)).toEqual(c.needles);
    });
  }
});

describe("findQuoteInPdf", () => {
  test("finds a quote that sits entirely on one line", async () => {
    const doc = fakeDoc([
      [
        "Wir müssen die Axt an die",
        "Wurzel legen und endlich",
        "entschlossen handeln, wenn",
        "es um den Klimaschutz geht.",
      ],
    ]);
    const match = await findQuoteInPdf(doc, "entschlossen handeln, wenn");
    expect(match?.pageNumber).toBe(1);
  });

  test("finds a quote that wraps across a line break at a word boundary", async () => {
    const doc = fakeDoc([
      [
        "Die Bundesregierung trägt eine besondere",
        "Verantwortung dafür, dass die Axt endlich",
        "an die Wurzel des Problems gelegt wird und",
        "wir nicht länger tatenlos zusehen.",
      ],
    ]);
    const match = await findQuoteInPdf(doc, "besondere Verantwortung dafür");
    expect(match?.pageNumber).toBe(1);
  });

  test("finds a quote whose word is split by line-wrap hyphenation", async () => {
    const doc = fakeDoc([
      [
        "Wir tragen gemeinsam die Verant-",
        "wortung für kommende Generationen",
        "und dürfen diese Aufgabe nicht",
        "auf die lange Bank schieben.",
      ],
    ]);
    const match = await findQuoteInPdf(doc, "gemeinsam die Verantwortung für kommende");
    expect(match?.pageNumber).toBe(1);
  });

  test("keeps a real mid-line hyphen intact instead of treating it as a wrap artifact", async () => {
    const doc = fakeDoc([
      [
        "Die Rot-Grün-Koalition hat hier",
        "klar Stellung bezogen und den",
        "Vorschlag der AfD-Fraktion abgelehnt.",
      ],
    ]);
    const match = await findQuoteInPdf(doc, "Die Rot-Grün-Koalition hat hier klar Stellung bezogen");
    expect(match?.pageNumber).toBe(1);
  });

  test("returns null for a paraphrase that isn't a literal match", async () => {
    const doc = fakeDoc([
      [
        "Wir müssen die Axt an die",
        "Wurzel legen und endlich",
        "entschlossen handeln, wenn",
        "es um den Klimaschutz geht.",
      ],
    ]);
    const match = await findQuoteInPdf(doc, "wir handeln entschlossen beim Klimaschutz");
    expect(match).toBeNull();
  });

  test("matches regardless of capitalisation, which the LLM does not preserve", async () => {
    // Real case ID214614300: the summary opens the quote with a capitalised
    // "Als" where the protocol reads "als" mid-sentence.
    const doc = fakeDoc([
      [
        "Wir stehen zu unserer Verantwortung, und",
        "als Bundesrepublik Deutschland stellen wir",
        "uns diesem Teil unserer Vergangenheit.",
      ],
    ]);
    const match = await findQuoteInPdf(doc, "Als Bundesrepublik Deutschland stellen wir uns diesem Teil");
    expect(match?.pageNumber).toBe(1);
  });

  test("matches a quote whose parts are stitched together with a [...] elision", async () => {
    const doc = fakeDoc([
      [
        "Wir wollen ein Denkmal errichten, und zwar",
        "ohne jede Einschränkung, für die Opfer der",
        "deutschen Besatzung in Polen.",
      ],
    ]);
    const match = await findQuoteInPdf(doc, "Wir wollen ein Denkmal errichten [...] für die Opfer der deutschen Besatzung");
    expect(match?.pageNumber).toBe(1);
  });

  test("accepts the ellipsis character as an elision marker too", async () => {
    const doc = fakeDoc([
      ["Das ist ein wichtiges Signal an unsere", "Nachbarn und ein Zeichen der Aussöhnung."],
    ]);
    const match = await findQuoteInPdf(doc, "Das ist ein wichtiges Signal … ein Zeichen der Aussöhnung");
    expect(match?.pageNumber).toBe(1);
  });

  test("accepts a bracketed ellipsis character, the form real summaries use", async () => {
    // Real case ID216710700 quotes the coalition treaty as: Wir „wollen […]
    // Alleinerziehende und deren Kinder besser unterstützen…"
    const doc = fakeDoc([
      ["Wir wollen in dieser Wahlperiode endlich", "Alleinerziehende und deren Kinder besser unterstützen."],
    ]);
    const match = await findQuoteInPdf(doc, "Wir wollen […] Alleinerziehende und deren Kinder besser unterstützen");
    expect(match?.pageNumber).toBe(1);
  });

  test("rejects elision segments that appear in the wrong order", async () => {
    const doc = fakeDoc([
      ["Zuerst kommt die Aussöhnung und danach", "folgt die gemeinsame Verantwortung."],
    ]);
    const match = await findQuoteInPdf(doc, "die gemeinsame Verantwortung [...] Zuerst kommt die Aussöhnung");
    expect(match).toBeNull();
  });

  test("does not highlight the elided material between two matched segments", async () => {
    const doc = fakeDoc([["Wir wollen ein Denkmal errichten, und zwar sofort, für die Opfer."]]);
    const match = await findQuoteInPdf(doc, "Wir wollen ein Denkmal errichten [...] für die Opfer");
    expect(match?.pageNumber).toBe(1);
    // Two disjoint segments on one line produce two separate highlight boxes,
    // not one box spanning the skipped "und zwar sofort".
    expect(match!.boxes.length).toBe(2);
  });

  test("normalises typographic quote marks on both sides", async () => {
    const doc = fakeDoc([["Er nannte es ein „historisches Versäumnis“ unserer Zeit."]]);
    const match = await findQuoteInPdf(doc, 'Er nannte es ein "historisches Versäumnis" unserer Zeit');
    expect(match?.pageNumber).toBe(1);
  });

  test("finds a quote on a later page without matching earlier pages", async () => {
    const doc = fakeDoc([
      ["Zu Beginn der heutigen Sitzung begrüße ich", "alle Kolleginnen und Kollegen recht herzlich."],
      ["Wir kommen nun zum nächsten Tagesordnungspunkt", "und ich erteile das Wort dem Herrn Abgeordneten."],
      [
        "An dieser Stelle möchte ich betonen, dass wir",
        "als Fraktion geschlossen hinter diesem Vorschlag",
        "stehen und ihn entschlossen mittragen werden.",
      ],
      ["Damit kommen wir zur Abstimmung über den", "vorliegenden Antrag der Fraktionen."],
    ]);
    const match = await findQuoteInPdf(doc, "geschlossen hinter diesem Vorschlag");
    expect(match?.pageNumber).toBe(3);
  });
});
