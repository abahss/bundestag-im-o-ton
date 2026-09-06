import type { DrucksacheSummary } from "@/lib/api";

export interface DrucksacheListItem {
  nummer: string;
  pdfUrl: string;
  /** Subtopic-Titel bei gebündelten TOPs (a/b/c) — Fallback für die Zeile,
   *  wenn keine Zusammenfassung geladen werden konnte. */
  subtopicTitle?: string;
  summary: DrucksacheSummary | null;
}

function TypBadge({ typ }: { typ?: string }) {
  if (!typ || typ === "Drucksache") return null;
  return (
    <span className="ml-2 align-[0.15em] inline-block text-[10px] font-medium uppercase tracking-wide rounded-full bg-[#219EBC]/10 text-[#219EBC] px-2 py-0.5">
      {typ}
    </span>
  );
}

function PdfLink({ nummer, url }: { nummer: string; url: string }) {
  if (!url) return null;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-xs font-medium text-[#219EBC] hover:underline"
    >
      Drucksache {nummer} (PDF ↗)
    </a>
  );
}

function Row({ item }: { item: DrucksacheListItem }) {
  const { summary, nummer, pdfUrl, subtopicTitle } = item;
  const heading = summary?.titel || subtopicTitle || `Drucksache ${nummer}`;

  // No summary (unverified match or no machine-readable DIP text): a plain,
  // non-expandable line with the PDF link.
  if (!summary || !summary.im_kern) {
    return (
      <div className="py-2 flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-sm font-medium text-[#023047] dark:text-white">{heading}</span>
        <TypBadge typ={summary?.typ} />
        <span className="basis-full" />
        <PdfLink nummer={nummer} url={pdfUrl || summary?.pdf_url || ""} />
      </div>
    );
  }

  return (
    <details className="group">
      <summary className="cursor-pointer list-none py-2 flex items-baseline gap-2">
        <span className="shrink-0 text-zinc-400 text-xs transition-transform group-open:rotate-90">
          ▸
        </span>
        <span className="text-sm font-medium text-[#023047] dark:text-white">
          {heading}
          <TypBadge typ={summary.typ} />
        </span>
      </summary>
      <div className="pb-3 pl-5">
        {summary.urheber && summary.urheber !== "—" && (
          <p className="text-sm text-zinc-500 mb-1">
            <span className="font-medium">Eingebracht von:</span> {summary.urheber}
          </p>
        )}
        <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
          {summary.im_kern}
        </p>
        {summary.punkte.length > 0 && (
          <ul className="space-y-1 mb-3">
            {summary.punkte.map((p, i) => (
              <li
                key={i}
                className="text-sm text-zinc-600 dark:text-zinc-400 ml-4 list-disc"
              >
                {p}
              </li>
            ))}
          </ul>
        )}
        {summary.truncated && (
          <p className="text-xs text-amber-600 dark:text-amber-500 mb-2">
            ⚠ Nur der Anfang dieses langen Gesetzentwurfs wurde ausgewertet –
            Detailregelungen weiter hinten im Text können in der Zusammenfassung
            fehlen. Der vollständige Wortlaut steht in der Drucksache.
          </p>
        )}
        <PdfLink nummer={nummer} url={pdfUrl || summary.pdf_url} />
      </div>
    </details>
  );
}

/** Variante D — die Drucksachen des TOP als aufklappbare Zeilen direkt unter dem
 *  Titel, keine eigene Box. */
export default function DrucksacheList({ items }: { items: DrucksacheListItem[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-2 border-t border-zinc-100 dark:border-zinc-800/70 divide-y divide-zinc-100 dark:divide-zinc-800/70">
      {items.map((it, i) => (
        <Row key={`${it.nummer}-${i}`} item={it} />
      ))}
    </div>
  );
}
