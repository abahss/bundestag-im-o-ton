"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import { Top } from "@/lib/api";
import TopList from "./TopList";
import Calendar from "./Calendar";
import ThemeToggle from "./ThemeToggle";

function fuzzyMatch(top: Top, query: string): boolean {
  const q = query.toLowerCase();
  const subtopicTitles = top.subtopics.map((s) => s.title);
  const fields = [top.title, top.subtitle, top.topic, ...subtopicTitles].join(" ").toLowerCase();
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
  return new Map([...map.entries()].sort((a, b) => {
    const [da, db] = [a[0], b[0]].map(parseDate);
    return db.getTime() - da.getTime();
  }));
}

function parseDate(str: string): Date {
  const [day, month, year] = str.split(".");
  return new Date(+year, +month - 1, +day);
}

function formatDate(d: Date): string {
  return `${String(d.getDate()).padStart(2,"0")}.${String(d.getMonth()+1).padStart(2,"0")}.${d.getFullYear()}`;
}


export default function HomeClient({ topics }: { topics: Top[] }) {
  const sessionDates = useMemo(() => new Set(topics.map((t) => t.date)), [topics]);

  const latestDate = useMemo(() => {
    const dates = [...sessionDates].map(parseDate);
    return dates.sort((a, b) => b.getTime() - a.getTime())[0];
  }, [sessionDates]);


  const [selectedDate, setSelectedDate] = useState<string>(latestDate ? formatDate(latestDate) : "");
  const [calYear, setCalYear] = useState(latestDate?.getFullYear() ?? new Date().getFullYear());
  const [calMonth, setCalMonth] = useState(latestDate?.getMonth() ?? new Date().getMonth());
  const [search, setSearch] = useState("");


  // Restore sessionStorage state after hydration to avoid SSR mismatch
  useEffect(() => {
    try {
      const s = sessionStorage.getItem("homeState");
      if (!s) return;
      const saved = JSON.parse(s);
      if (saved.date) setSelectedDate(saved.date);
      if (saved.year != null) setCalYear(saved.year);
      if (saved.month != null) setCalMonth(saved.month);
    } catch {}
  }, []);

  // Persist on every change, but skip the very first run. On back-navigation
  // Next.js briefly mounts a throwaway instance of this component before the
  // real one takes over; without this guard, that instance's first pass would
  // save its still-default state (before the restore effect above has landed)
  // and clobber the correct value the real instance is about to read.
  const skippedFirstSave = useRef(false);
  useEffect(() => {
    if (!skippedFirstSave.current) {
      skippedFirstSave.current = true;
      return;
    }
    try { sessionStorage.setItem("homeState", JSON.stringify({ date: selectedDate, year: calYear, month: calMonth })); }
    catch { /* ignore */ }
  }, [selectedDate, calYear, calMonth]);

  // Restore scroll position when returning via the back button. Runs after
  // the date/accordion restorations above so the page has already reached
  // its final height; two rAFs wait out that extra render before jumping.
  useEffect(() => {
    let raf1 = 0;
    let raf2 = 0;
    try {
      const saved = sessionStorage.getItem("homeScrollY");
      if (saved == null) return;
      const y = Number(saved);
      raf1 = requestAnimationFrame(() => {
        raf2 = requestAnimationFrame(() => window.scrollTo(0, y));
      });
    } catch {}
    return () => {
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
    };
  }, []);

  // During search: all matching TOPs; optionally filtered by selectedDate if user clicked calendar
  const searchMatches = useMemo(() => {
    if (!search.trim()) return [];
    return topics.filter((t) => fuzzyMatch(t, search.trim()));
  }, [topics, search]);

  // Dates that have search results — for calendar highlighting
  const searchMatchDates = useMemo(
    () => new Set(searchMatches.map((t) => t.date)),
    [searchMatches]
  );

  // Jump calendar to earliest matching month when search changes
  useEffect(() => {
    if (!search.trim() || searchMatches.length === 0) return;
    const latest = searchMatches
      .map((t) => parseDate(t.date))
      .reduce((a, b) => (a > b ? a : b));
    setCalYear(latest.getFullYear());
    setCalMonth(latest.getMonth());
  }, [search, searchMatches]);

  // What to show in the list
  const filtered = useMemo(() => {
    if (search.trim()) return searchMatches;
    return topics.filter((t) => t.date === selectedDate);
  }, [topics, search, selectedDate, searchMatches]);

  const grouped = useMemo(() => groupByDate(filtered), [filtered]);

  function handleMonthChange(year: number, month: number) {
    setCalYear(year);
    setCalMonth(month);
  }

  function handleSelect(date: string) {
    setSelectedDate(date);
    const d = parseDate(date);
    setCalYear(d.getFullYear());
    setCalMonth(d.getMonth());
  }

  // Called when a TOP accordion is opened — navigate calendar to that month
  function handleTopFocus(date: string) {
    if (!date) return;
    const d = parseDate(date);
    setCalYear(d.getFullYear());
    setCalMonth(d.getMonth());
  }

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-center text-[#023047] dark:text-white">
              Was im Bundestag wirklich gesagt wird.
            </h1>
          </div>
          <ThemeToggle />
        </div>

        <div className="text-sm text-zinc-600 dark:text-zinc-300 mb-6 leading-relaxed max-w-xl mx-auto text-left space-y-2">
          <p>Der Deutsche <a href="https://www.bundestag.de/" target="_blank" rel="noopener noreferrer" className="underline hover:text-zinc-700 dark:hover:text-zinc-300">Bundestag</a> veröffentlicht nach jeder Sitzung ein offizielles <a href="https://www.bundestag.de/dokumente/protokolle" target="_blank" rel="noopener noreferrer" className="underline hover:text-zinc-700 dark:hover:text-zinc-300">Wortprotokoll</a>.</p>
          <p>Diese App nutzt KI, um daraus für jeden Tagesordnungspunkt (TOP) und Zusatzpunkt (ZP) eine neutrale Zusammenfassung und die Position jeder Partei herauszuarbeiten. Zu jeder Partei gibt es mehrere direkte Zitate als Beleg und ein Link zur Quelle.</p>
          <p>Noch Fragen? Schau ins <a href="/faq" className="underline hover:text-zinc-700 dark:hover:text-zinc-300">FAQ</a> oder schreib mir eine Nachricht über den Feedbackbutton unten rechts.</p>
        </div>

        <div className="max-w-xl mx-auto mb-6 border border-zinc-200 dark:border-zinc-700 rounded-xl px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">
          Der Bundestag befindet sich derzeit in der Sommerpause. Daten sind seit März 2026 verfügbar – die Abdeckung wird bald erweitert.
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400">🔍</span>
          <input
            type="text"
            value={search}
            onChange={(e) => {
                const val = e.target.value;
                setSearch(val);
                if (!val) {
                  setSelectedDate(latestDate ? formatDate(latestDate) : "");
                  setCalYear(latestDate?.getFullYear() ?? new Date().getFullYear());
                  setCalMonth(latestDate?.getMonth() ?? new Date().getMonth());
                } else {
                  setSelectedDate("");
                }
              }}
            placeholder="z.B. Gesundheit, Kinder, Mobilität…"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-transparent text-base focus:outline-none focus:ring-2 focus:ring-[#219EBC]"
          />
          {search && (
            <button
              onClick={() => {
                setSearch("");
                setSelectedDate(latestDate ? formatDate(latestDate) : "");
                setCalYear(latestDate?.getFullYear() ?? new Date().getFullYear());
                setCalMonth(latestDate?.getMonth() ?? new Date().getMonth());
              }}
              aria-label="Suche zurücksetzen"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
            >
              ✕
            </button>
          )}
        </div>

        {/* Always two-column: calendar left, list right */}
        <div className="flex flex-col gap-6 md:flex-row md:gap-8">
          <div className="md:w-72 shrink-0">
            <Calendar
              sessionDates={sessionDates}
              highlightedDates={search.trim() ? searchMatchDates : undefined}
              selectedDate={selectedDate}
              year={calYear}
              month={calMonth}
              onSelect={handleSelect}
              onMonthChange={handleMonthChange}
            />
          </div>
          <div className="flex-1 min-w-0">
            {search.trim() && (
              <p className="text-xs text-zinc-400 mb-4">
                {searchMatches.length} Ergebnis{searchMatches.length !== 1 ? "se" : ""} in allen Sitzungen
              </p>
            )}
            <TopList
              key={search.trim() ? "search" : "browse"}
              grouped={grouped}
              onTopFocus={handleTopFocus}
              defaultOpen={!search.trim()}
              focusDate={search.trim() ? selectedDate : undefined}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
