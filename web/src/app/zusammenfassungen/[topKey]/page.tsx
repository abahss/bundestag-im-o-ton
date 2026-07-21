import { fetchAllTopics, fetchSummaries } from "@/lib/api";
import BackButton from "@/components/BackButton";
import ParliamentChart from "@/components/ParliamentChart";
import ThemeToggle from "@/components/ThemeToggle";
import LanguageToggle from "@/components/LanguageToggle";
import GeneralSummary from "@/components/GeneralSummary";
import { getServerLocale } from "@/lib/locale-server";

function renderSummary(text: string, introducedByLabel: string) {
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
          <span className="font-medium">{introducedByLabel}</span> {content}
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
  const locale = await getServerLocale();

  const [topics, summaries] = await Promise.all([
    fetchAllTopics(),
    fetchSummaries(decoded, locale),
  ]);

  const top = topics.find((t) => t.top_key === decoded);
  const navLabel = top?.top_id
    .replace("Tagesordnungspunkt ", "TOP ")
    .replace("Zusatzpunkt ", "ZP ") ?? decoded;

  const general = summaries.general as { summary: string } | undefined;
  const partySummaries = Object.fromEntries(
    Object.entries(summaries)
      .filter(([k]) => k !== "general")
      .map(([k, v]) => [k, v as { summary: string; refresh_count?: number }])
  );

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <div className="flex items-start justify-between mb-4">
          <BackButton />
          <div className="flex items-center gap-3">
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </div>

        <div className="mb-6">
          <p className="text-xs text-zinc-400 mb-1">{top?.date} · {navLabel}</p>
          <h1 className="text-xl font-bold text-[#023047] dark:text-white">
            {top?.topic || top?.title || decoded}
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
          {/* Left: general summary */}
          {general?.summary && (
            <div className="md:w-2/5 shrink-0">
              <GeneralSummary key={locale} initialSummary={general.summary} topKey={decoded} />
            </div>
          )}

          {/* Right: chart on top, party card below (handled inside ParliamentChart) */}
          <div className="flex-1 min-w-0">
            <ParliamentChart key={locale} summaries={partySummaries} topKey={decoded} />
          </div>
        </div>
      </div>
    </div>
  );
}
