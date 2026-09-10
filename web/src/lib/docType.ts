// Dokumentart-Pille for the TOP list on the home page. The detail page uses the
// real DIP `typ` from /drucksache-summary; the list has no summaries loaded, so it
// classifies the procedural line the XML parser keeps (`subtitle` / subtopic `nas`,
// falling back to `title` when that line doesn't carry it — see classifyTopDocType).
// That measures the *Beratungsart* ("Beratung der Beschlussempfehlung … zu dem
// Antrag …" → Beschlussempfehlung), a subtly different question from the document
// type — good enough for a list hint.

import type { Top } from "@/lib/api";

const RULES: [RegExp, string][] = [
  [/beschlussempfehlung/i, "Beschlussempfehlung"],
  [/entwurf eines|entwurfs eines|gesetzentwurf/i, "Gesetzentwurf"],
  [/entschließungsantrag/i, "Entschließungsantrag"],
  [/\bantrag(s|es)?\b/i, "Antrag"],
  [/gro(ß|ss)e anfrage/i, "Große Anfrage"],
  [/unterrichtung/i, "Unterrichtung"],
  [/wahlvorschl(a|ä)g|^wahl |wahl von|wahl eines/i, "Wahl"],
  [/übersicht.*petition|petition.*übersicht/i, "Petitionen"],
];

function classifyText(text: string): string | null {
  for (const [re, label] of RULES) if (re.test(text)) return label;
  return null;
}

const PLURAL: Record<string, string> = {
  Antrag: "Anträge",
  Gesetzentwurf: "Gesetzentwürfe",
  Beschlussempfehlung: "Beschlussempfehlungen",
  Entschließungsantrag: "Entschließungsanträge",
  "Große Anfrage": "Große Anfragen",
  Unterrichtung: "Unterrichtungen",
  Wahl: "Wahlvorschläge",
  Petitionen: "Petitionen",
};

export interface DocTypeBadge {
  label: string;
  /** true when the TOP bundles several vorlagen (count-prefixed label) */
  bundled?: boolean;
}

function subtopicTypes(top: Top): Set<string> {
  return new Set(
    (top.subtopics ?? [])
      .map((s) => classifyText(s.nas || s.title || ""))
      .filter(Boolean) as string[],
  );
}

/** null → procedural item (Regierungserklärung, Fragestunde, Aktuelle Stunde …) → no pill. */
export function classifyTopDocType(top: Top): DocTypeBadge | null {
  const subs = top.subtopics ?? [];
  if (subs.length > 0) {
    const types = subtopicTypes(top);
    if (types.size === 0) return null;
    if (types.size === 1 && subs.length === 1) return { label: [...types][0] };
    // uniform bundle → "2 Anträge"; mixed → "3 Vorlagen"
    const noun = types.size === 1 ? PLURAL[[...types][0]] ?? [...types][0] : "Vorlagen";
    return { label: `${subs.length} ${noun}`, bundled: true };
  }
  // Falls back to title when subtitle doesn't classify — e.g. an Einzelplan ressort
  // debate (EP 08) has no procedural NaS in subtitle (it's "Allgemeine Finanzdebatte"),
  // but its title is the bill itself ("Entwurf eines Haushaltsbegleitgesetzes 2027").
  const t = classifyText(top.subtitle || "") || classifyText(top.title || "");
  return t ? { label: t } : null;
}
