import { fetchAllTopics, fetchSummaries } from "@/lib/api";
import BackButton from "@/components/BackButton";
import ParliamentChart from "@/components/ParliamentChart";
import ThemeToggle from "@/components/ThemeToggle";
import GeneralSummary from "@/components/GeneralSummary";
import VoteSummaryCard from "@/components/VoteSummaryCard";

function renderSummary(text: string) {
  return text.split("\n").map((line, i) => {
    if (line.startsWith("**Kernposition:**")) {
      const content = line.replace("**Kernposition:**", "").trim();
      return (
        <p key={i} className="font-semibold text-[#023047] dark:text-white mb-3">
          {content}
        </p>
      );
    }
    if (line.startsWith("**Eingebracht von:**")) {
      const content = line.replace("**Eingebracht von:**", "").trim();
      return (
        <p key={i} className="text-sm text-zinc-500 mb-1">
          <span className="font-medium">Eingebracht von:</span> {content}
        </p>
      );
    }
    if (line.startsWith("**Im Kern:**")) {
      const content = line.replace("**Im Kern:**", "").trim();
      return (
        <p key={i} className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
          {content}
        </p>
      );
    }
    if (line.startsWith("- ")) {
      return (
        <li key={i} className="text-sm text-zinc-600 dark:text-zinc-400 ml-4 list-disc">
          {line.slice(2)}
        </li>
      );
    }
    const quoteMatch = line.match(/^\*"(.+)"\*\s*(.*)$/);
    if (quoteMatch) {
      return (
        <blockquote
          key={i}
          className="border-l-2 border-[#219EBC] pl-3 my-2 text-sm text-zinc-600 dark:text-zinc-400 italic"
        >
          „{quoteMatch[1]}"
          {quoteMatch[2] && (
            <span className="not-italic text-xs text-zinc-400 ml-2">{quoteMatch[2]}</span>
          )}
        </blockquote>
      );
    }
    if (!line.trim()) return <div key={i} className="h-2" />;
    return <p key={i} className="text-sm text-zinc-600 dark:text-zinc-400">{line}</p>;
  });
}

export default async function SummaryPage({
  params,
}: {
  params: Promise<{ topKey: string }>;
}) {
  const { topKey } = await params;
  const decoded = decodeURIComponent(topKey);

  const [topics, summaries] = await Promise.all([
    fetchAllTopics(),
    fetchSummaries(decoded),
  ]);

  const top = topics.find((t) => t.top_key === decoded);
  const navLabel = top?.top_id
    .replace("Tagesordnungspunkt ", "TOP ")
    .replace("Zusatzpunkt ", "ZP ") ?? decoded;

  const general = summaries.general as { summary: string } | undefined;
  const abstimmung = summaries.abstimmung;
  // A TOP can technically have more than one recorded vote (one per subtopic), but that
  // hasn't occurred in practice yet — show the first one rather than build UI for a case
  // that doesn't exist in the data.
  const vote = abstimmung ? Object.values(abstimmung)[0] : undefined;
  const partySummaries = Object.fromEntries(
    Object.entries(summaries)
      .filter(([k]) => k !== "general")
      .map(([k, v]) => [k, v as { summary: string; refresh_count?: number }])
  );

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <div className="sticky top-0 z-20 -mx-4 px-4 py-2 bg-white/50 dark:bg-zinc-950/50 backdrop-blur flex items-center justify-between mb-4">
          <BackButton />
          <ThemeToggle />
        </div>

        <div className="mb-6">
          <p className="text-xs text-zinc-400 mb-1">{top?.date} · {navLabel}</p>
          <h1 className="text-xl font-bold text-[#023047] dark:text-white flex flex-wrap items-baseline gap-x-2">
            <span>{top?.topic || top?.title || decoded}</span>
            {vote && (
              <span className="relative group shrink-0 text-base font-normal align-middle">
                <span aria-hidden="true">🗳️</span>
                <span className="sr-only">Namentliche Abstimmung</span>
                <span
                  aria-hidden="true"
                  className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap rounded-lg bg-zinc-800 text-white text-xs px-2 py-1 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-75 z-10 shadow-lg"
                >
                  Namentliche Abstimmung
                </span>
              </span>
            )}
          </h1>
          {top?.title && top.title !== top?.topic && (
            <p className="text-sm text-zinc-600 dark:text-zinc-300 mt-1">{top.title}</p>
          )}
          {top?.subtopics && top.subtopics.length > 0 && (
            <ul className="mt-2 space-y-0.5">
              {top.subtopics.map((s) => (
                <li key={s.key} className="text-sm text-zinc-600 dark:text-zinc-300">
                  <span className="font-medium text-zinc-700 dark:text-zinc-200">{s.key})</span> {s.title}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Two-column layout: general summary left, chart + party card right */}
        <div className="flex flex-col gap-6 md:flex-row md:gap-8">
          {/* Left: vote summary + general summary */}
          {(vote || general?.summary) && (
            <div className="md:w-2/5 shrink-0 flex flex-col gap-4">
              {general?.summary && (
                <GeneralSummary initialSummary={general.summary} topKey={decoded} />
              )}
              {vote && <VoteSummaryCard vote={vote} />}
            </div>
          )}

          {/* Right: chart on top, party card below (handled inside ParliamentChart) */}
          <div className="flex-1 min-w-0">
            <ParliamentChart summaries={partySummaries} topKey={decoded} abstimmung={abstimmung} />
          </div>
        </div>
      </div>
    </div>
  );
}
