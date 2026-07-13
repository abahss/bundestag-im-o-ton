"use client";

import { useRouter } from "next/navigation";
import ThemeToggle from "@/components/ThemeToggle";

const FAQ: { q: string; a: string; items?: string[]; note?: string; link?: { href: string; label: string } }[] = [
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

export default function FaqPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-8">
          <button onClick={() => router.back()} className="text-sm text-[#219EBC] hover:underline">
            ← Zurück
          </button>
          <ThemeToggle />
        </div>

        <h1 className="text-xl font-bold text-[#023047] dark:text-white mb-8">
          Häufige Fragen
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
