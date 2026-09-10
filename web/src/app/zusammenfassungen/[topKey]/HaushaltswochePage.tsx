import { fetchSummaries } from "@/lib/api";
import type { SummaryResponse, Top } from "@/lib/api";
import { EINBRINGUNG_TITLE, type HaushaltswocheView } from "@/lib/haushaltswoche";
import GeneralSummary from "@/components/GeneralSummary";

const safeSummaries = (key: string): Promise<SummaryResponse> =>
  fetchSummaries(key).catch(() => ({}) as SummaryResponse);

/** Shared page header — date/nav-label line + h1. */
function Header({
  date, navLabel, title,
}: { date: string; navLabel: string; title: string }) {
  return (
    <div className="mb-6">
      <p className="text-xs text-zinc-400 mb-1">{date} · {navLabel}</p>
      <h1 className="text-xl font-bold text-[#023047] dark:text-white">{title}</h1>
    </div>
  );
}

/** The "Haushalt" homepage row: only the cross-cutting overview. The Einzelplan ressort
 *  debates (TOP 4's former "content") are ordinary TOPs and get the ordinary TOP page —
 *  see expandHaushaltswoche() in @/lib/haushaltswoche. */
async function OverviewView({ hub }: { hub: Top }) {
  const summaries = await safeSummaries(hub.top_key);
  const overview = (summaries.general as { summary: string } | undefined)?.summary;
  return (
    <>
      <Header date={hub.date} navLabel={`Sitzung ${hub.session}`} title={hub.title} />
      {overview && (
        <GeneralSummary initialSummary={overview} topKey={hub.top_key} heading="Die Haushaltswoche im Überblick" />
      )}
    </>
  );
}

/** A Drucksache with no separate Zusammenfassung because it's a reines Zahlenwerk (the
 *  Haushaltsgesetz/Finanzplan behind TOP 3, Variante D3 — no drucksache-summary is ever
 *  generated for these). Same collapsible look as DrucksacheList's rows, but the
 *  expanded content is a short explanation instead of a generated summary. */
function ZahlenwerkRow({ heading, nummer, pdfUrl }: { heading: string; nummer: string; pdfUrl: string }) {
  return (
    <details className="group">
      <summary className="cursor-pointer list-none py-2 flex items-baseline gap-2">
        <span className="shrink-0 text-zinc-400 text-xs transition-transform group-open:rotate-90">▸</span>
        <span className="text-sm font-medium text-[#023047] dark:text-white">{heading}</span>
      </summary>
      <div className="pb-3 pl-5">
        <p className="text-xs text-amber-600 dark:text-amber-500 mb-2">
          ⚠ Besteht vor allem aus Tabellen und Zahlenwerk, nicht aus Fließtext —
          keine automatische Zusammenfassung. Der vollständige Wortlaut steht in
          der Drucksache.
        </p>
        {pdfUrl && (
          <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="text-xs font-medium text-[#219EBC] hover:underline">
            Drucksache {nummer} (PDF ↗)
          </a>
        )}
      </div>
    </details>
  );
}

/** The "TOP 3" homepage row: the Einbringung — its general summary plus the Zahlenwerke
 *  (Haushaltsgesetz, Finanzplan) as collapsible rows, same look as every other
 *  Drucksachen list on the site (DrucksacheList), just with an explanatory note instead
 *  of a summary since these carry none (Variante D3). */
async function Top3View({ hub, allTopics }: { hub: Top; allTopics: Top[] }) {
  const einbringung = hub.einbringung ? allTopics.find((t) => t.top_key === hub.einbringung) : undefined;
  const summaries = hub.einbringung ? await safeSummaries(hub.einbringung) : ({} as SummaryResponse);
  const general = (summaries.general as { summary: string } | undefined)?.summary;
  const zahlenwerke = (einbringung?.subtopics ?? []).flatMap((s) =>
    s.drucksache ? [{ key: s.key, heading: `${s.key}) ${s.title}`, nummer: s.drucksache, pdfUrl: s.drucksache_url }] : [],
  );

  return (
    <>
      <Header date={hub.date} navLabel={`TOP 3 · Sitzung ${hub.session}`} title={EINBRINGUNG_TITLE} />
      {zahlenwerke.length > 0 && (
        <div className="mb-4 border-t border-zinc-100 dark:border-zinc-800/70 divide-y divide-zinc-100 dark:divide-zinc-800/70">
          {zahlenwerke.map((d) => (
            <ZahlenwerkRow key={d.key} heading={d.heading} nummer={d.nummer} pdfUrl={d.pdfUrl} />
          ))}
        </div>
      )}
      {general && <GeneralSummary initialSummary={general} topKey={hub.einbringung!} />}
    </>
  );
}

/** The Haushaltswoche hub has two dedicated views — the rest (the Einzelplan ressort
 *  debates) are ordinary TOPs and never reach this component at all. */
export default function HaushaltswochePage({
  hub, view, allTopics,
}: { hub: Top; view: HaushaltswocheView; allTopics: Top[] }) {
  if (view === "overview") return <OverviewView hub={hub} />;
  return <Top3View hub={hub} allTopics={allTopics} />;
}
