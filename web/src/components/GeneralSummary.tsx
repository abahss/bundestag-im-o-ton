"use client";

import { useState, useEffect } from "react";
import { refreshGeneralSummary } from "@/lib/api";
import { loadSummaryCache, saveSummaryCache } from "@/lib/summaryCache";

function renderLine(line: string, i: number) {
  if (line.startsWith("**Kernposition:**")) {
    return <p key={i} className="font-semibold text-[#023047] dark:text-white mb-3">{line.replace("**Kernposition:**", "").trim()}</p>;
  }
  if (line.startsWith("**Eingebracht von:**")) {
    const content = line.replace("**Eingebracht von:**", "").trim();
    return <p key={i} className="text-sm text-zinc-500 mb-1"><span className="font-medium">Eingebracht von:</span> {content}</p>;
  }
  if (line.startsWith("**Im Kern:**")) {
    return <p key={i} className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">{line.replace("**Im Kern:**", "").trim()}</p>;
  }
  if (line.startsWith("- ")) {
    return <p key={i} className="text-sm text-zinc-600 dark:text-zinc-400 ml-4">• {line.slice(2)}</p>;
  }
  const qm = line.match(/^\*"(.+)"\*\s*(.*)$/);
  if (qm) {
    return (
      <blockquote key={i} className="border-l-2 border-[#219EBC] pl-3 my-2 text-sm text-zinc-600 dark:text-zinc-400 italic">
        „{qm[1]}"
        {qm[2] && <span className="not-italic text-xs text-zinc-400 ml-2">{qm[2]}</span>}
      </blockquote>
    );
  }
  if (!line.trim()) return <div key={i} className="h-2" />;
  return <p key={i} className="text-sm text-zinc-600 dark:text-zinc-400">{line}</p>;
}

export default function GeneralSummary({
  initialSummary,
  topKey,
}: {
  initialSummary: string;
  topKey: string;
}) {
  const MAX_REFRESH = 5;
  const [summary, setSummary] = useState(initialSummary);
  const [loading, setLoading] = useState(false);
  const [refreshCount, setRefreshCount] = useState(0);
  const [open, setOpen] = useState(false);
  const contentId = `general-summary-content-${topKey.replace(/\s+/g, "-")}`;

  useEffect(() => {
    const cached = loadSummaryCache(topKey);
    if (cached.general) {
      setSummary(cached.general);
    } else {
      saveSummaryCache(topKey, { general: initialSummary });
    }
  }, []);

  async function handleRefresh() {
    if (refreshCount >= MAX_REFRESH) return;
    setLoading(true);
    try {
      const data = await refreshGeneralSummary(topKey);
      setSummary(data.summary);
      saveSummaryCache(topKey, { general: data.summary });
      setRefreshCount((c) => c + 1);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-zinc-50 dark:bg-zinc-900 rounded-xl p-4 self-start">
      <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-3">
        Allgemeine Zusammenfassung
      </h2>
      <div className="relative mb-1">
        <div
          id={contentId}
          className={`space-y-2 ${open ? "" : "max-h-24 overflow-hidden"} md:max-h-none md:overflow-visible`}
        >
          {summary.split("\n").map((line, i) => renderLine(line, i))}
        </div>
        {!open && (
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-6 bg-linear-to-t from-zinc-50 dark:from-zinc-900 to-transparent md:hidden" />
        )}
      </div>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={contentId}
        className="mb-3 md:hidden text-xs font-medium text-[#219EBC] hover:underline"
      >
        {open ? "Weniger anzeigen" : "Mehr anzeigen"}
      </button>
      <div className={`${open ? "flex" : "hidden"} md:flex items-center gap-2`}>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={loading || refreshCount >= MAX_REFRESH}
            className="text-xs border border-zinc-200 dark:border-zinc-700 rounded px-2 py-1 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "Wird generiert…" : "↻ Neu generieren"}
          </button>
          <span className="text-xs text-zinc-400">
            {refreshCount >= MAX_REFRESH ? "Limit erreicht" : `${MAX_REFRESH - refreshCount} übrig`}
          </span>
        </div>
      </div>
    </div>
  );
}
