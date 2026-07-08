"use client";

import { useState, useMemo } from "react";
import { Top } from "@/lib/api";
import TopList from "./TopList";
import Calendar from "./Calendar";

function fuzzyMatch(top: Top, query: string): boolean {
  const q = query.toLowerCase();
  const fields = [top.title, top.subtitle, top.topic].join(" ").toLowerCase();
  return fields.includes(q);
}

function sortTops(tops: Top[]): Top[] {
  return [...tops].sort((a, b) => {
    const isTOP_a = a.top_id.startsWith("Tagesordnungspunkt");
    const isTOP_b = b.top_id.startsWith("Tagesordnungspunkt");
    if (isTOP_a !== isTOP_b) return isTOP_a ? -1 : 1;
    const numA = parseInt(a.top_id.replace(/\D/g, ""), 10) || 0;
    const numB = parseInt(b.top_id.replace(/\D/g, ""), 10) || 0;
    return numA - numB;
  });
}

function groupByDate(tops: Top[]): Map<string, Top[]> {
  const map = new Map<string, Top[]>();
  for (const t of sortTops(tops)) {
    if (!map.has(t.date)) map.set(t.date, []);
    map.get(t.date)!.push(t);
  }
  return map;
}

export default function HomeClient({ topics }: { topics: Top[] }) {
  const sessionDates = useMemo(
    () => new Set(topics.map((t) => t.date)),
    [topics]
  );

  const latestDate = useMemo(() => {
    const dates = [...sessionDates].map((d) => {
      const [day, month, year] = d.split(".");
      return new Date(+year, +month - 1, +day);
    });
    return dates.sort((a, b) => b.getTime() - a.getTime())[0];
  }, [sessionDates]);

  const formatDate = (d: Date) =>
    `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;

  const [selectedDate, setSelectedDate] = useState<string>(
    latestDate ? formatDate(latestDate) : ""
  );
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (search.trim()) {
      return topics.filter((t) => fuzzyMatch(t, search.trim()));
    }
    return topics.filter((t) => t.date === selectedDate);
  }, [topics, search, selectedDate]);

  const grouped = useMemo(() => groupByDate(filtered), [filtered]);

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <h1 className="text-2xl font-bold text-center text-[#023047] dark:text-white mb-2">
          Was im Bundestag wirklich gesagt wird.
        </h1>
        <p className="text-sm text-zinc-500 text-center mb-6">
          Neutrale Zusammenfassungen jeder Debatte – mit direkten Zitaten aus dem Protokoll.
        </p>

        {/* Search */}
        <div className="relative mb-6">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400">🔍</span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Sitzungen durchsuchen…"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[#219EBC]"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
            >
              ✕
            </button>
          )}
        </div>

        {search ? (
          /* Search results */
          <div>
            <p className="text-xs text-zinc-400 mb-4">
              {filtered.length} Ergebnis{filtered.length !== 1 ? "se" : ""} in allen Sitzungen
            </p>
            <TopList grouped={grouped} />
          </div>
        ) : (
          /* Calendar + list */
          <div className="flex flex-col gap-6 md:flex-row md:gap-8">
            <div className="md:w-72 shrink-0">
              <Calendar
                sessionDates={sessionDates}
                selectedDate={selectedDate}
                onSelect={setSelectedDate}
              />
            </div>
            <div className="flex-1 min-w-0">
              <TopList grouped={grouped} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
