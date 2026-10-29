"use client";

// Landing page: search tools + chips + calendar on top of the TOP list, with the
// Reichstag-dome pattern faintly behind. Two layouts swapped with CSS at md:
// a sticky tool column next to a wide list on desktop, a single column with a
// "Thema suchen / Nach Datum" switch on mobile.

import { useState, type ReactNode } from "react";
import { Top } from "@/lib/api";
import Calendar from "./Calendar";
import TopList from "./TopList";
import ThemeToggle from "./ThemeToggle";
import DomeBackdrop from "./DomeBackdrop";

export type LandingProps = {
  sessionDates: Set<string>;
  search: string;
  onSearchChange: (value: string) => void;
  onSearchClear: () => void;
  searchMatches: Top[];
  searchMatchDates: Set<string>;
  selectedDate: string;
  calYear: number;
  calMonth: number;
  onSelect: (date: string) => void;
  onMonthChange: (year: number, month: number) => void;
  onTopFocus: (date: string) => void;
  grouped: Map<string, Top[]>;
};

const TOPIC_CHIPS = [
  "Klima",
  "Rente",
  "Bürgergeld",
  "Wehrpflicht",
  "Social Media",
  "Bildung",
  "Gesundheit",
  "Mobilität",
];

function SearchBox({ search, onChange, onClear }: { search: string; onChange: (v: string) => void; onClear: () => void }) {
  return (
    <div className="relative">
      <svg aria-hidden="true" viewBox="0 0 20 20" className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-zinc-400" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="9" cy="9" r="6" />
        <path d="m14 14 4 4" />
      </svg>
      <input
        type="text"
        value={search}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Welches Thema interessiert dich?"
        className={`w-full pl-11 pr-10 rounded-md border-2 border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 text-base focus:outline-none focus:border-[#3e3ac6] py-3 placeholder:text-sm`}
      />
      {search && (
        <button onClick={onClear} aria-label="Suche zurücksetzen" className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600">
          ✕
        </button>
      )}
    </div>
  );
}

function Chips({ onPick, twoRows }: { onPick: (v: string) => void; twoRows?: boolean }) {
  const chip = (label: string) => (
    <button
      key={label}
      onClick={() => onPick(label)}
      className={`rounded-md bg-[#e2e1f6] hover:bg-[#3e3ac6] hover:text-white text-[#3e3ac6] dark:text-white dark:bg-zinc-800 dark:hover:bg-zinc-700 font-semibold transition-colors whitespace-nowrap ${
        twoRows ? "px-2.5 sm:px-3.5 py-2 text-xs sm:text-sm" : "px-3.5 py-2 text-sm"
      }`}
    >
      {label}
    </button>
  );
  // twoRows: fixed 4 + 4 split, pills keep their natural width
  if (twoRows) {
    const half = Math.ceil(TOPIC_CHIPS.length / 2);
    return (
      <div className="flex flex-col gap-2">
        {[TOPIC_CHIPS.slice(0, half), TOPIC_CHIPS.slice(half)].map((row, i) => (
          <div key={i} className="flex justify-center gap-2">{row.map(chip)}</div>
        ))}
      </div>
    );
  }
  return <div className="flex flex-wrap gap-2 justify-center">{TOPIC_CHIPS.map(chip)}</div>;
}

function Header({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="flex-1">{children}</div>
      <ThemeToggle />
    </div>
  );
}

function newestDate(dates: Set<string>): string | undefined {
  const toTime = (d: string) => {
    const [day, month, year] = d.split(".");
    return new Date(+year, +month - 1, +day).getTime();
  };
  return [...dates].sort((a, b) => toTime(b) - toTime(a))[0];
}

// Separates the search tools from the list below and names what the list shows:
// the newest session by default, switching to "Suchergebnisse" while searching.
function Divider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 mb-3 text-[#3e3ac6] dark:text-[#ceec97]">
      <span className="h-0.5 w-6 bg-current" aria-hidden="true" />
      <h2 className="text-sm font-bold uppercase tracking-wider whitespace-nowrap">{label}</h2>
      <span className="h-0.5 flex-1 bg-current opacity-40" aria-hidden="true" />
    </div>
  );
}

function Results({ p }: { p: LandingProps }) {
  return (
    <>
      <Divider
        label={
          p.search.trim()
            ? "Suchergebnisse"
            : p.selectedDate === newestDate(p.sessionDates)
              ? "Neueste Sitzung"
              : "Frühere Sitzung"
        }
      />
      {p.search.trim() && (
        <p className="text-xs text-zinc-400 mb-4">
          {p.searchMatches.length} Ergebnis{p.searchMatches.length !== 1 ? "se" : ""} in allen Sitzungen
        </p>
      )}
      <TopList key={p.search.trim() ? "search" : "browse"} grouped={p.grouped} onTopFocus={p.onTopFocus} />
    </>
  );
}

function FaqHint({ className = "" }: { className?: string }) {
  return (
    <p className={`text-sm text-zinc-600 dark:text-zinc-300 ${className}`}>
      Noch Fragen? Schau ins{" "}
      <a href="/faq" className="font-semibold text-[#3e3ac6] dark:text-[#ceec97] underline">FAQ</a>{" "}
      oder schreib mir über den Feedback-Button unten rechts.
    </p>
  );
}

function CalendarBlock({ p }: { p: LandingProps }) {
  // Solid backing with a light border and a faint shadow: lifts off the dome pattern, but gently.
  return (
    <div className="rounded-md border border-zinc-200 bg-white p-3 shadow-sm dark:border-zinc-700 dark:bg-zinc-950">
      <Calendar
        sessionDates={p.sessionDates}
        highlightedDates={p.search.trim() ? p.searchMatchDates : undefined}
        selectedDate={p.selectedDate}
        year={p.calYear}
        month={p.calMonth}
        onSelect={p.onSelect}
        onMonthChange={p.onMonthChange}
      />
    </div>
  );
}

// Desktop: sticky tool column (search, chips, calendar, FAQ hint) left, wide list right.
function LandingDesktop(p: LandingProps) {
  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <Header>
        <h1 className="text-4xl font-extrabold text-center text-[#3e3ac6] dark:text-white">
          Politik auf einen <span className="bg-[#ceec97] text-[#3e3ac6] px-2 rounded-sm">Blick.</span>
        </h1>
        <p className="text-center mt-2 text-zinc-500">Knappe Zusammenfassungen der Bundestagssitzungen</p>
      </Header>
      <div className="grid gap-10 grid-cols-[20rem_minmax(0,1fr)]">
        <aside className="space-y-4 sticky top-4 self-start">
          <SearchBox search={p.search} onChange={p.onSearchChange} onClear={p.onSearchClear} />
          <Chips onPick={p.onSearchChange} />
          <div className="pt-2"><CalendarBlock p={p} /></div>
          <FaqHint className="pt-1" />
        </aside>
        <section className="min-w-0"><Results p={p} /></section>
      </div>
    </div>
  );
}

// Mobile layout: one navigation tool at a time ("Thema suchen" / "Nach Datum").
function LandingMobile(p: LandingProps) {
  const [mode, setMode] = useState<"thema" | "datum">("thema");
  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">
      <Header>
        <h1 className="text-3xl font-extrabold text-center text-[#3e3ac6] dark:text-white">
          Politik auf einen <span className="bg-[#ceec97] text-[#3e3ac6] px-2 rounded-sm">Blick.</span>
        </h1>
        <p className="text-center mt-2 text-zinc-500">Knappe Zusammenfassungen der Bundestagssitzungen</p>
      </Header>
      <div role="tablist" aria-label="Wie willst du stöbern?" className="grid grid-cols-2 p-1 rounded-md border border-zinc-300 dark:border-zinc-600 bg-zinc-100 dark:bg-zinc-900 font-semibold text-sm">
        {([["thema", "Thema suchen"], ["datum", "Nach Datum"]] as const).map(([k, label]) => (
          <button
            key={k}
            role="tab"
            aria-selected={mode === k}
            onClick={() => {
              // The two searches are separate on mobile: switching resets the other one
              // (clears the keyword and goes back to the newest session).
              if (k === mode) return;
              p.onSearchClear();
              setMode(k);
            }}
            className={`py-2.5 rounded-sm transition-colors ${mode === k ? "bg-[#3e3ac6] text-white" : "text-zinc-500"}`}
          >
            {label}
          </button>
        ))}
      </div>
      {mode === "thema" ? (
        <div className="space-y-4">
          <SearchBox search={p.search} onChange={p.onSearchChange} onClear={p.onSearchClear} />
          <Chips onPick={p.onSearchChange} twoRows />
        </div>
      ) : (
        <div className="max-w-xs mx-auto"><CalendarBlock p={p} /></div>
      )}
      <Results p={p} />
      <FaqHint />
    </div>
  );
}

export default function Landing(p: LandingProps) {
  return (
    <div className="relative isolate overflow-x-clip">
      <DomeBackdrop />
      <div className="hidden md:block"><LandingDesktop {...p} /></div>
      <div className="md:hidden"><LandingMobile {...p} /></div>
    </div>
  );
}
