"use client";

import { useState, useEffect } from "react";
import { refreshSummary, VoteResult } from "@/lib/api";
import { loadSummaryCache, saveSummaryCache } from "@/lib/summaryCache";
import { VoteBar } from "@/components/VoteBar";
import { usePdfSplitScreen } from "@/components/PdfSplitScreenProvider";

const PARTY_META = [
  { key: "LINKE",  seats: 64,  color: "#BE3075", short: "Linke",   full: "Die Linke" },
  { key: "GRÜNEN", seats: 85,  color: "#46962B", short: "Grüne",   full: "Bündnis 90/Die Grünen" },
  { key: "SPD",    seats: 120, color: "#E3000F", short: "SPD",     full: "SPD" },
  { key: "CDUCSU", seats: 208, color: "#1a1a1a", short: "CDU/CSU", full: "CDU/CSU" },
  { key: "AFD",    seats: 152, color: "#009EE0", short: "AfD",     full: "AfD" },
];

const MAX_REFRESH = 5;
const CX = 260, CY = 265, R = 250, IR = 155;
const GAP = 0.025;
const TOTAL = PARTY_META.reduce((s, p) => s + p.seats, 0);
const AVAIL = Math.PI - GAP * (PARTY_META.length - 1);

function pt(a: number, rad: number) {
  return `${(CX + rad * Math.cos(a)).toFixed(2)},${(CY - rad * Math.sin(a)).toFixed(2)}`;
}
function sectorPath(a1: number, a2: number) {
  const la = a1 - a2 > Math.PI ? 1 : 0;
  return `M ${pt(a1,R)} A ${R},${R} 0 ${la},1 ${pt(a2,R)} L ${pt(a2,IR)} A ${IR},${IR} 0 ${la},0 ${pt(a1,IR)} Z`;
}

function idToPdfUrl(id: string): string {
  // ID format: "IDwwss..." where ww = Wahlperiode (chars 2-3), ss = Sitzung (chars 4-5)
  const wp = id.slice(2, 4);
  const session = id.slice(4, 6).padStart(3, "0");
  return `https://dserver.bundestag.de/btp/${wp}/${wp}${session}.pdf`;
}

interface Quote {
  text: string;
  url: string;
}

function parseSummary(text: string): { kernposition: string; quotes: Quote[] } {
  let kernposition = "";
  const quotes: Quote[] = [];
  for (const line of text.split("\n")) {
    if (line.startsWith("**Kernposition:**")) {
      kernposition = line.replace("**Kernposition:**", "").trim();
    }
    const qm = line.match(/^\*"(.+?)"\*/);
    if (qm) {
      const idMatch = line.match(/\[(ID\d{9})\]/);
      const url = idMatch ? idToPdfUrl(idMatch[1]) : "";
      quotes.push({ text: qm[1], url });
    }
  }
  return { kernposition, quotes };
}

export default function ParliamentChart({
  summaries,
  topKey,
  abstimmung,
}: {
  summaries: Record<string, { summary: string; refresh_count?: number }>;
  topKey?: string;
  abstimmung?: Record<string, VoteResult>;
}) {
  const { show: showPdfSource } = usePdfSplitScreen();
  // A TOP can technically have more than one recorded vote (one per subtopic), but that
  // hasn't occurred in practice yet — take the first one rather than build UI for a case
  // that doesn't exist in the data.
  const vote = abstimmung ? Object.values(abstimmung)[0] : undefined;
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [introPlayed, setIntroPlayed] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setIntroPlayed(true), 1400);
    return () => clearTimeout(t);
  }, []);
  const [quoteIdx, setQuoteIdx] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [unchangedHint, setUnchangedHint] = useState(false);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
    const obs = new MutationObserver(() =>
      setIsDark(document.documentElement.classList.contains("dark"))
    );
    obs.observe(document.documentElement, { attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  const [localSummaries, setLocalSummaries] = useState(summaries);
  const [refreshCounts, setRefreshCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!topKey) return;
    // Only ever restores a party's own past "Neu generieren" result — the
    // server already sends the current summary fresh on every page load, so
    // there is nothing to seed here. Blindly caching that fresh response used
    // to make it permanent, silently diverging from the server the moment the
    // underlying data changed (see summaryCache.ts).
    const cached = loadSummaryCache(topKey);
    if (cached.parties && Object.keys(cached.parties).length > 0) {
      setLocalSummaries((prev) => {
        const updated = { ...prev };
        for (const [k, s] of Object.entries(cached.parties!)) {
          if (updated[k]) updated[k] = { ...updated[k], summary: s };
        }
        return updated;
      });
    }
  }, []);

  const parties = PARTY_META.map((p) => {
    const entry = localSummaries[p.key];
    const { kernposition, quotes } = entry ? parseSummary(entry.summary) : { kernposition: "", quotes: [] };
    return { ...p, kernposition, quotes, refresh_count: refreshCounts[p.key] ?? 0 };
  });

  // Build arcs
  const arcs: { key: string; a1: number; a2: number; mx: number; my: number }[] = [];
  let angle = Math.PI;
  for (const p of parties) {
    const span = (p.seats / TOTAL) * AVAIL;
    const a1 = angle, a2 = angle - span;
    const mid = (a1 + a2) / 2, mr = (R + IR) / 2;
    arcs.push({ key: p.key, a1, a2, mx: CX + mr * Math.cos(mid), my: CY - mr * Math.sin(mid) });
    angle = a2 - GAP;
  }

  const active = parties.find((p) => p.key === activeKey);
  const cardColor = active
    ? (isDark && active.key === "CDUCSU" ? "#71717a" : active.color)
    : undefined;
  const quote = active?.quotes[quoteIdx];
  const remaining = active ? MAX_REFRESH - active.refresh_count : 0;
  const partyVote = active && vote ? vote.parteien[active.key] : undefined;
  const hasPartyVote = !!partyVote && partyVote.ja + partyVote.nein + partyVote.enthalten > 0;

  function selectParty(key: string) {
    setActiveKey((prev) => (prev === key ? null : key));
    setQuoteIdx(0);
    setUnchangedHint(false);
  }

  function goToPrevQuote() {
    if (!active) return;
    setQuoteIdx((i) => Math.max(0, i - 1));
  }

  function goToNextQuote() {
    if (!active || active.quotes.length <= 1) return;
    setQuoteIdx((i) => (i + 1) % active.quotes.length);
  }

  async function handleRefresh() {
    if (!active || !topKey || refreshing || remaining <= 0) return;
    setRefreshing(true);
    setUnchangedHint(false);
    const previousKernposition = active.kernposition;
    try {
      const data = await refreshSummary(topKey, active.key);
      setLocalSummaries((prev) => ({
        ...prev,
        [active.key]: { summary: data.summary },
      }));
      saveSummaryCache(topKey, { parties: { [active.key]: data.summary } });
      setRefreshCounts((prev) => ({ ...prev, [active.key]: (prev[active.key] ?? 0) + 1 }));
      setQuoteIdx(0);
      const { kernposition: newKernposition } = parseSummary(data.summary);
      if (newKernposition && newKernposition === previousKernposition) {
        setUnchangedHint(true);
      }
    } catch {
      // silently fail — button re-enables
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div>
      {/* SVG chart */}
      <style>{`
        @keyframes segment-pulse {
          0%, 100% { opacity: 1; }
          40% { opacity: 0.45; }
        }
        .segment-intro { animation: segment-pulse 0.5s ease-in-out 1; }
      `}</style>
      <svg viewBox="0 0 520 270" className="w-full max-w-lg mx-auto block">
        {parties.map((p, i) => {
          const arc = arcs[i];
          const isActive = p.key === activeKey;
          const dimmed = activeKey !== null && !isActive;
          return (
            <g
              key={p.key}
              role="button"
              tabIndex={0}
              aria-pressed={isActive}
              aria-label={`${p.full}, ${p.seats} Sitze`}
              onClick={() => selectParty(p.key)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  selectParty(p.key);
                }
              }}
              className="group cursor-pointer outline-none"
              style={!introPlayed && activeKey === null ? { animation: `segment-pulse 0.5s ease-in-out ${0.2 + i * 0.18}s 1` } : undefined}
            >
              <path d={sectorPath(arc.a1, arc.a2)} fill={p.color} stroke="white" strokeWidth="1.5" opacity={dimmed ? 0.35 : 1} className="transition-opacity" />
              <path
                d={sectorPath(arc.a1, arc.a2)}
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                className="pointer-events-none text-[#023047] dark:text-white opacity-0 group-focus-visible:opacity-100"
              />
              <text x={arc.mx.toFixed(2)} y={(arc.my - 9).toFixed(2)} textAnchor="middle" dominantBaseline="central" fill="white" fontSize="14" fontWeight="500" className="pointer-events-none select-none">{p.short}</text>
              <text x={arc.mx.toFixed(2)} y={(arc.my + 9).toFixed(2)} textAnchor="middle" dominantBaseline="central" fill="white" fillOpacity="0.7" fontSize="11" className="pointer-events-none select-none">{p.seats} Sitze</text>
            </g>
          );
        })}
      </svg>

      {/* Party card */}
      {active ? (
        <div className="mt-4 rounded-xl border p-4" style={{ borderColor: cardColor }}>
          {/* Header */}
          <div className="flex items-center gap-2 mb-3">
            <span className="w-3 h-3 rounded-full shrink-0" style={{ background: cardColor }} />
            <span className="font-bold text-sm" style={{ color: cardColor }}>{active.full}</span>
            {hasPartyVote && partyVote ? (
              <div className="ml-auto bg-zinc-50 dark:bg-zinc-800/60 rounded-lg px-2.5 py-1.5">
                <VoteBar ja={partyVote.ja} nein={partyVote.nein} enthalten={partyVote.enthalten} compact />
              </div>
            ) : (
              <span className="text-xs text-zinc-400 ml-1">{active.seats} Sitze · {Math.round(active.seats / TOTAL * 100)}%</span>
            )}
          </div>

          {/* Kernposition */}
          {active.kernposition ? (
            <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200 mb-3 leading-relaxed">
              {active.kernposition}
            </p>
          ) : (
            <p className="text-sm text-zinc-400 italic mb-3">Keine Zusammenfassung verfügbar.</p>
          )}

          {/* Quote */}
          {quote && (
            <div className="flex items-start gap-2 mb-3">
              <div
                className={`border-l-2 pl-3 py-1 flex-1 min-w-0 ${active.quotes.length > 1 ? "cursor-pointer" : ""}`}
                style={{ borderColor: cardColor }}
                onClick={goToNextQuote}
              >
                <p className="text-sm text-zinc-600 dark:text-zinc-400 italic leading-relaxed">„{quote.text}"</p>
                {quote.url && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      showPdfSource({
                        quoteText: quote.text,
                        pdfUrl: quote.url,
                        sessionLabel: topKey ? `Sitzung · ${topKey}` : "Quelle",
                      });
                    }}
                    className="text-xs text-[#FB8500] hover:underline mt-1 inline-block"
                  >
                    📋 Quelle
                  </button>
                )}
              </div>
              {active.quotes.length > 1 && (
                <div className="flex flex-col items-center shrink-0">
                  <button onClick={goToPrevQuote} disabled={quoteIdx === 0} aria-label="Vorheriges Zitat" className="text-zinc-400 hover:text-zinc-600 disabled:opacity-30 text-lg leading-none px-1">
                    <span className="inline-block rotate-90">‹</span>
                  </button>
                  <span className="text-xs text-zinc-400">{quoteIdx + 1}/{active.quotes.length}</span>
                  <button onClick={goToNextQuote} aria-label="Nächstes Zitat" className="text-zinc-400 hover:text-zinc-600 text-lg leading-none px-1">
                    <span className="inline-block rotate-90">›</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Footer: refresh */}
          <div className="flex items-center gap-2 flex-wrap">
            {unchangedHint && (
              <a
                href="/faq#kernposition-gleich"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#219EBC] hover:underline"
              >
                Zusammenfassung blieb gleich? Erfahre hier wieso →
              </a>
            )}
            {topKey && (
              <div className="ml-auto flex items-center gap-2">
                <button
                  onClick={handleRefresh}
                  disabled={refreshing || remaining <= 0}
                  className="text-xs border border-zinc-200 dark:border-zinc-700 rounded px-2 py-1 text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {refreshing ? "Wird generiert…" : "↻ Neu generieren"}
                </button>
                <span className="text-xs text-zinc-400">
                  {remaining <= 0 ? "Limit erreicht" : `${remaining} übrig`}
                </span>
              </div>
            )}
          </div>
        </div>
      ) : (
        <p className="text-center text-sm text-zinc-400 mt-4">Klicke auf eine Partei, um ihre Position zu lesen</p>
      )}
    </div>
  );
}
