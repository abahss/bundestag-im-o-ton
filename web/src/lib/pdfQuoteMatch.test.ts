import { describe, expect, test } from "vitest";
import { findQuoteInPdf } from "./pdfQuoteMatch";
import type { PDFDocumentProxy } from "pdfjs-dist";
import type { TextItem } from "pdfjs-dist/types/src/display/api";

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
