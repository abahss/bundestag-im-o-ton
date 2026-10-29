"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import Fuse from "fuse.js";
import { Top, fetchSearchIndex } from "@/lib/api";
import { expandHaushaltswoche } from "@/lib/haushaltswoche";
import { FUSE_OPTIONS, searchTops } from "@/lib/search";
import Landing from "./Landing";

function sortKey(t: Top): [number, number] {
  // The Haushaltswoche overview row has no TOP number of its own — sort it
  // just ahead of its own TOP 3 (Einbringung) row.
  if (t.top_id === "Haushaltswoche") return [0, 2.5];
  // Einzelplan ressort debates follow the Einbringung (TOP 3) chronologically —
  // sort them right after it, in Einzelplan order.
  if (t.top_id.startsWith("Einzelplan")) {
    return [0, 3 + (parseInt(t.top_id.match(/\d+/)?.[0] ?? "", 10) || 0) / 100];
  }
  const isTOP = t.top_id.startsWith("Tagesordnungspunkt");
  // The *first* TOP number, not every digit run together — "Tagesordnungspunkt 1, 2"
  // must sort as 1, not as 12.
  return [isTOP ? 0 : 1, parseInt(t.top_id.match(/\d+/)?.[0] ?? "", 10) || 0];
}

function sortTops(tops: Top[]): Top[] {
  return [...tops].sort((a, b) => {
    const [ga, na] = sortKey(a);
    const [gb, nb] = sortKey(b);
    return ga - gb || na - nb;
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


export default function HomeClient({ topics: rawTopics }: { topics: Top[] }) {
  const topics = useMemo(() => expandHaushaltswoche(rawTopics), [rawTopics]);
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

  const fuse = useMemo(() => new Fuse(topics, FUSE_OPTIONS), [topics]);

  // Full-text search index ({ top_key: blob }). Fetched after mount so the
  // ~750 KB (gzipped) never blocks first paint; until it lands, search stays on
  // the title-level fields.
  const [searchIndex, setSearchIndex] = useState<Record<string, string> | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetchSearchIndex().then((idx) => {
      if (!cancelled) setSearchIndex(idx);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // During search: all matching TOPs; optionally filtered by selectedDate if user clicked calendar
  const searchMatches = useMemo(
    () => searchTops(topics, search, fuse, searchIndex),
    [fuse, topics, search, searchIndex],
  );

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

  function handleSearchChange(val: string) {
    setSearch(val);
    if (!val) {
      setSelectedDate(latestDate ? formatDate(latestDate) : "");
      setCalYear(latestDate?.getFullYear() ?? new Date().getFullYear());
      setCalMonth(latestDate?.getMonth() ?? new Date().getMonth());
    } else {
      setSelectedDate("");
    }
  }

  function handleSearchClear() {
    setSearch("");
    setSelectedDate(latestDate ? formatDate(latestDate) : "");
    setCalYear(latestDate?.getFullYear() ?? new Date().getFullYear());
    setCalMonth(latestDate?.getMonth() ?? new Date().getMonth());
  }

  return (
    <div className="bg-white dark:bg-zinc-950">
      <Landing
        sessionDates={sessionDates}
        search={search}
        onSearchChange={handleSearchChange}
        onSearchClear={handleSearchClear}
        searchMatches={searchMatches}
        searchMatchDates={searchMatchDates}
        selectedDate={selectedDate}
        calYear={calYear}
        calMonth={calMonth}
        onSelect={handleSelect}
        onMonthChange={handleMonthChange}
        onTopFocus={handleTopFocus}
        grouped={grouped}
      />
    </div>
  );
}
