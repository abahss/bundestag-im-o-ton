"use client";

import { useRouter } from "next/navigation";
import ThemeToggle from "@/components/ThemeToggle";

const FAQ: { id?: string; q: string; a: string; items?: string[]; note?: string; link?: { href: string; label: string }; sub?: { q: string; a: string; link?: { href: string; label: string } }[] }[] = [
  {
    q: "Warum sind Nummerierungen übersprungen?",
    a: `Das ist normal und kein Fehler. Tagesordnungspunkte können kurzfristig verschoben, abgesetzt oder schriftlich zu Protokoll gegeben werden. Die Nummer bleibt dann trotzdem vergeben. Manchmal kommen auch Zusatzpunkte (ZP) hinzu, die außerhalb der regulären Reihenfolge behandelt werden.`,
  },
  {
    q: "Was ist der Zusammenhang zwischen den Zitaten und den Zusammenfassungen?",
    a: `Die Zitate stammen direkt aus dem offiziellen Wortprotokoll und sind unverändert. Sie bilden die Grundlage auf der die KI die Zusammenfassung erstellt. Sie sind also sowohl Quelle als auch Beleg. Die Kernposition fasst zusammen was eine Partei inhaltlich vertreten hat; die Zitate zeigen konkret welche Aussagen dieser Einschätzung zugrunde liegen. Der Link neben jedem Zitat öffnet das offizielle PDF des Sitzungsprotokolls. Das Zitat lässt sich darin mit der Suchfunktion (Strg+F bzw. ⌘+F) finden: Text kopieren (Strg+C bzw. ⌘+C) und im Suchfeld mit Strg+V (bzw. ⌘+V) einfügen.`,
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
    q: "Was bedeutet das 🗳️-Symbol?",
    a: `Es zeigt an, dass zu diesem Tagesordnungspunkt eine namentliche Abstimmung im Bundestag stattgefunden hat und das Ergebnis (Ja/Nein/Enthaltung, auch aufgeschlüsselt nach Fraktion) hier verfügbar ist. Nur ein kleiner Teil der Tagesordnungspunkte wird überhaupt namentlich abgestimmt. Die meisten Abstimmungen laufen per Handzeichen ohne Einzelergebnis. Fehlt das Symbol, heißt das nicht, dass gar nicht abgestimmt wurde, sondern dass kein Einzelergebnis vorliegt.`,
    sub: [
      {
        q: "Warum ergeben die Parteiergebnisse in Summe nicht das Gesamtergebnis?",
        a: `Weil neben den Fraktionen auch fraktionslose Abgeordnete mitabstimmen. Ihre Stimmen fließen ins Gesamtergebnis (Ja/Nein/Enthaltung) ein, werden aber in der Aufschlüsselung nach Fraktion nicht separat ausgewiesen. Die Summe der Fraktionsergebnisse kann daher etwas kleiner ausfallen als das Gesamtergebnis. Wer genau als fraktionslos abgestimmt hat, lässt sich hier nachschlagen:`,
        link: { href: "https://www.abgeordnetenwatch.de/bundestag/abstimmungen", label: "Abstimmungen auf abgeordnetenwatch.de" },
      },
    ],
  },
  {
    id: "kernposition-gleich",
    q: "Warum bleibt die Kernposition nach 'Neu generieren' manchmal unverändert?",
    a: `Der Button erzeugt die Kernposition neu aus denselben Redebeiträgen dieser Partei zu diesem Tagesordnungspunkt — die Zitate bleiben dabei immer gleich, nur der Ein-Satz-Kernposition wird neu formuliert. Hat eine Partei zu einem Thema nur wenig gesagt, gibt es kaum Spielraum für eine andere Formulierung, und die neue Version kann mit der vorherigen identisch sein. Das ist kein Fehler, sondern zeigt eher, dass zu diesem Thema wirklich wenig Redetext dieser Partei vorliegt.`,
  },
  {
    q: "Welche Rolle spielt KI? Was muss ich beachten?",
    a: `Die KI (Google Gemini 2.5 Flash) liest die Reden und destilliert daraus eine lesbare Zusammenfassung. Sie erfindet keine Zitate und keine Positionen. Sie fasst zusammen was tatsächlich gesagt wurde. Was zu beachten ist: Zusammenfassungen können Fehler oder Vereinfachungen enthalten, besonders bei kurzen oder sehr technischen Debatten. Wenn eine Partei kaum zu Wort gekommen ist, spiegelt die Zusammenfassung das zuverlässig wider, aber die Position ist dann möglicherweise inhaltlich weniger ausgearbeitet als die anderer Parteien. Die Zitate sind der zuverlässigste Teil. Im Zweifel immer das verlinkte PDF als Primärquelle prüfen. Die App kennzeichnet wenn keine Reden einer Partei zu einem TOP vorliegen.`,
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
          {FAQ.map(({ id, q, a, items, note, link, sub }) => (
            <div key={q} id={id} className={id ? "scroll-mt-6" : undefined}>
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
              {sub && (
                <div className="mt-3 ml-4 pl-3 border-l-2 border-zinc-200 dark:border-zinc-800 space-y-3">
                  {sub.map((s) => (
                    <div key={s.q}>
                      <h3 className="text-xs font-semibold text-[#023047] dark:text-white mb-1">{s.q}</h3>
                      <p className="text-sm text-zinc-500 leading-relaxed">{s.a}</p>
                      {s.link && (
                        <a href={s.link.href} target="_blank" rel="noopener noreferrer" className="text-sm text-[#219EBC] hover:underline mt-1 inline-block">
                          {s.link.label} →
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
