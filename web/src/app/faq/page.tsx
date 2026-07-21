"use client";

import { useRouter } from "next/navigation";
import ThemeToggle from "@/components/ThemeToggle";
import { useLocale, Locale } from "@/lib/i18n";

type FaqEntry = { q: string; a: string; items?: string[]; note?: string; link?: { href: string; label: string } };

const FAQ_DE: FaqEntry[] = [
  {
    q: "Warum sind Nummerierungen übersprungen?",
    a: `Das ist normal und kein Fehler. Tagesordnungspunkte können kurzfristig verschoben, abgesetzt oder schriftlich zu Protokoll gegeben werden — die Nummer bleibt dann trotzdem vergeben. Manchmal kommen auch Zusatzpunkte (ZP) hinzu, die außerhalb der regulären Reihenfolge behandelt werden.`,
  },
  {
    q: "Was ist der Zusammenhang zwischen den Zitaten und den Zusammenfassungen?",
    a: `Die Zitate stammen direkt aus dem offiziellen Wortprotokoll und sind unverändert. Sie bilden die Grundlage auf der die KI die Zusammenfassung erstellt — sie sind also sowohl Quelle als auch Beleg. Die Kernposition fasst zusammen was eine Partei inhaltlich vertreten hat; die Zitate zeigen konkret welche Aussagen dieser Einschätzung zugrunde liegen. Der Link neben jedem Zitat öffnet das offizielle PDF des Sitzungsprotokolls. Das Zitat lässt sich darin mit der Suchfunktion (Strg+F bzw. ⌘+F) finden.`,
  },
  {
    q: "Woher stammen diese Daten?",
    a: `Aus den offiziellen Plenarprotokollen des Deutschen Bundestages, die nach jeder Sitzung als XML auf bundestag.de veröffentlicht werden. Sie enthalten das vollständige Wortprotokoll aller gehaltenen Reden.`,
    link: { href: "https://www.bundestag.de/services/opendata", label: "Bundestag Open Data" },
  },
  {
    q: "Welche Elemente sind KI-generiert?",
    a: `KI-generiert sind:`,
    items: [
      `Kurztitel des Themas (z.B. 'Rentenreform 2025')`,
      `Allgemeine Zusammenfassung des Tagesordnungspunkts`,
      `Kernposition jeder Partei (Zusammenfassung der Parteiposition in einem Satz)`,
    ],
    note: `Zitate stammen direkt aus den Protokollen und sind unverändert. Die Untertitel sind ebenfalls wörtlich aus der Quelle übernommen.`,
  },
  {
    q: "Wann werden Bundestagssitzungen abgehalten?",
    a: `Die Sitzungswochen für das aktuelle Jahr können hier eingesehen werden:`,
    link: { href: "https://www.bundestag.de/parlament/plenum/sitzungskalender/bt2026-1084980", label: "Sitzungskalender 2026" },
  },
  {
    q: "Welche Rolle spielt KI? Was muss ich beachten?",
    a: `Die KI (Google Gemini 2.5 Flash) liest die Reden und destilliert daraus eine lesbare Zusammenfassung. Sie erfindet keine Zitate und keine Positionen — sie fasst zusammen was tatsächlich gesagt wurde. Was zu beachten ist: Zusammenfassungen können Fehler oder Vereinfachungen enthalten, besonders bei kurzen oder sehr technischen Debatten. Wenn eine Partei kaum zu Wort gekommen ist, spiegelt die Zusammenfassung das zuverlässig wider — aber die Position ist dann möglicherweise inhaltlich weniger ausgearbeitet als die anderer Parteien. Die Zitate sind der zuverlässigste Teil — im Zweifel immer das verlinkte PDF als Primärquelle prüfen. Die App kennzeichnet wenn keine Reden einer Partei zu einem TOP vorliegen.`,
  },
];

const FAQ_EN: FaqEntry[] = [
  {
    q: "Why are some numbers skipped?",
    a: `That is normal and not an error. Agenda items can be postponed, withdrawn, or submitted to the record in writing at short notice — the number stays assigned regardless. Sometimes supplementary items (ZP) are added, which are handled outside the regular order.`,
  },
  {
    q: "How do the quotes relate to the summaries?",
    a: `The quotes come directly from the official verbatim protocol and are unchanged (they stay in the original German). They are the basis on which the AI writes the summary — so they are both source and evidence. The core position summarizes what a party argued; the quotes show which statements that assessment rests on. The link next to each quote opens the official PDF of the session protocol. You can find the quote in it with the search function (Ctrl+F or ⌘+F).`,
  },
  {
    q: "Where does this data come from?",
    a: `From the official plenary protocols of the German Bundestag, which are published as XML on bundestag.de after every sitting. They contain the complete verbatim record of all speeches given.`,
    link: { href: "https://www.bundestag.de/services/opendata", label: "Bundestag Open Data" },
  },
  {
    q: "Which elements are AI-generated?",
    a: `AI-generated are:`,
    items: [
      `Short title of the topic (e.g. 'Pension reform 2025')`,
      `General summary of the agenda item`,
      `Core position of each party (one-sentence summary of the party's position)`,
    ],
    note: `Quotes come directly from the protocols and are unchanged. The subtitles are also taken verbatim from the source.`,
  },
  {
    q: "When does the Bundestag sit?",
    a: `The sitting weeks for the current year can be viewed here:`,
    link: { href: "https://www.bundestag.de/parlament/plenum/sitzungskalender/bt2026-1084980", label: "Sitting calendar 2026" },
  },
  {
    q: "What role does AI play? What should I keep in mind?",
    a: `The AI (Google Gemini 2.5 Flash) reads the speeches and distills them into a readable summary. It does not invent quotes or positions — it summarizes what was actually said. Keep in mind: summaries can contain errors or simplifications, especially for short or very technical debates. If a party hardly spoke, the summary reliably reflects that — but its position may then be less elaborated than that of other parties. The quotes are the most reliable part — when in doubt, always check the linked PDF as the primary source. The app indicates when no speeches by a party exist for an agenda item.`,
  },
];

const FAQ_BY_LOCALE: Record<Locale, FaqEntry[]> = { de: FAQ_DE, en: FAQ_EN };

export default function FaqPage() {
  const router = useRouter();
  const { locale, t } = useLocale();
  const FAQ = FAQ_BY_LOCALE[locale];

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-8">
          <button onClick={() => router.back()} className="text-sm text-[#219EBC] hover:underline">
            {t("back")}
          </button>
          <ThemeToggle />
        </div>

        <h1 className="text-xl font-bold text-[#023047] dark:text-white mb-8">
          {t("faqTitle")}
        </h1>

        <div className="space-y-8">
          {FAQ.map(({ q, a, items, note, link }) => (
            <div key={q}>
              <h2 className="text-sm font-semibold text-[#023047] dark:text-white mb-2">{q}</h2>
              <p className="text-sm text-zinc-500 leading-relaxed">{a}</p>
              {items && (
                <ul className="mt-2 space-y-1">
                  {items.map((item) => (
                    <li key={item} className="text-sm text-zinc-500 flex gap-2">
                      <span className="shrink-0">–</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
              {note && <p className="text-sm text-zinc-500 leading-relaxed mt-2">{note}</p>}
              {link && (
                <a href={link.href} target="_blank" rel="noopener noreferrer" className="text-sm text-[#219EBC] hover:underline mt-1 inline-block">
                  {link.label} →
                </a>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
