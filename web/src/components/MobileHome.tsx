"use client";

// Mobile-only homepage layout (below the md breakpoint — desktop keeps the
// original two-column calendar+list layout in HomeClient). Intro text peeks
// its first two paragraphs with a fade + "Mehr anzeigen", the full month
// calendar is replaced by a horizontal strip of recent session dates, with
// the full month grid available on demand in a bottom sheet. Chosen after
// comparing three variants — see the prototype/mobile-homepage-variants
// branch for the other two and why this one won.

import { useMemo, useState, type ReactNode } from "react";
import { Top } from "@/lib/api";
import Calendar from "@/components/Calendar";
import TopList from "@/components/TopList";

function parseDate(str: string): Date {
  const [day, month, year] = str.split(".");
  return new Date(+year, +month - 1, +day);
}

export type MobileHomeProps = {
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

function SearchBar({ search, onChange, onClear }: { search: string; onChange: (v: string) => void; onClear: () => void }) {
  return (
    <div className="relative mb-4">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400">🔍</span>
      <input
        type="text"
        value={search}
        onChange={(e) => onChange(e.target.value)}
        placeholder="z.B. Gesundheit, Kinder, Mobilität…"
        className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-transparent text-base focus:outline-none focus:ring-2 focus:ring-[#219EBC]"
      />
      {search && (
        <button
          onClick={onClear}
          aria-label="Suche zurücksetzen"
          className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
        >
          ✕
        </button>
      )}
    </div>
  );
}

function ResultCount({ search, count }: { search: string; count: number }) {
  if (!search.trim()) return null;
  return (
    <p className="text-xs text-zinc-400 mb-3">
      {count} Ergebnis{count !== 1 ? "se" : ""} in allen Sitzungen
    </p>
  );
}

// Intro text is height-clamped so the "Direkte Zitate" bullet is the last
// (partially faded) visible line — same pattern as YouTube's "Mehr
// anzeigen" under video descriptions. "Namentliche Abstimmung" and
// everything after only appears once expanded.
function InfoPeek() {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-4 text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed text-left">
      <div className="relative space-y-2">
        <p>Der Deutsche <a href="https://www.bundestag.de/" target="_blank" rel="noopener noreferrer" className="underline hover:text-zinc-700 dark:hover:text-zinc-300">Bundestag</a> veröffentlicht nach jeder Sitzung ein offizielles <a href="https://www.bundestag.de/dokumente/protokolle" target="_blank" rel="noopener noreferrer" className="underline hover:text-zinc-700 dark:hover:text-zinc-300">Wortprotokoll</a>.</p>
        <div>
          <p>Diese App nutzt KI für neutrale Zusammenfassungen und Parteipositionen zu jedem Tagesordnungspunkt (TOP) und Zusatzpunkt (ZP):</p>
          <ul role="list" className="mt-2 space-y-1">
            <li role="listitem" className="flex gap-2">
              <span aria-hidden="true" className="shrink-0">💬</span>
              <span>Direkte Zitate als Beleg, mit Link zur Quelle.</span>
            </li>
            {open && (
              <li role="listitem" className="flex gap-2">
                <span aria-hidden="true" className="shrink-0">🗳️</span>
                <span>Namentliche Abstimmung, Ergebnis hier einsehbar.</span>
              </li>
            )}
          </ul>
        </div>
        {open && (
          <>
            <p>Noch Fragen? Schau ins <a href="/faq" className="underline hover:text-zinc-700 dark:hover:text-zinc-300">FAQ</a> oder schreib mir eine Nachricht über den Feedbackbutton unten rechts.</p>
            <div className="border border-zinc-200 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-500 dark:text-zinc-400">
              Der Bundestag befindet sich derzeit in der Sommerpause. Daten sind seit Dezember 2025 verfügbar – die Abdeckung wird bald erweitert.
            </div>
          </>
        )}
        {!open && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 bottom-0 h-6 bg-gradient-to-b from-transparent to-white dark:to-zinc-950"
          />
        )}
      </div>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="mt-2 text-[#219EBC] font-medium hover:underline"
      >
        {open ? "Weniger anzeigen" : "Mehr anzeigen"}
      </button>
    </div>
  );
}

function MobileSheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[75]">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="absolute bottom-0 left-0 right-0 max-h-[80vh] overflow-y-auto rounded-t-2xl bg-white dark:bg-zinc-900 p-4 pb-8 shadow-2xl">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-[#023047] dark:text-white">{title}</h2>
          <button onClick={onClose} aria-label="Schließen" className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function DateChipRow({
  sessionDates,
  selectedDate,
  onSelect,
  onOpenCalendar,
}: {
  sessionDates: Set<string>;
  selectedDate: string;
  onSelect: (date: string) => void;
  onOpenCalendar: () => void;
}) {
  const recentDates = useMemo(
    () => [...sessionDates].sort((a, b) => parseDate(b).getTime() - parseDate(a).getTime()).slice(0, 14),
    [sessionDates]
  );
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="flex gap-2 overflow-x-auto py-1 -mx-1 px-1" style={{ scrollbarWidth: "none" }}>
        {recentDates.map((d) => {
          const isSelected = d === selectedDate;
          return (
            <button
              key={d}
              onClick={() => onSelect(d)}
              className={[
                "shrink-0 rounded-full px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-colors",
                isSelected
                  ? "bg-[#219EBC] text-white"
                  : "bg-[#BEE3F2] text-[#023047] hover:bg-[#219EBC] hover:text-white dark:bg-[#219EBC]/30 dark:text-white",
              ].join(" ")}
            >
              {d.slice(0, 5)}
            </button>
          );
        })}
      </div>
      <button
        onClick={onOpenCalendar}
        aria-label="Alle Termine im Kalender öffnen"
        className="shrink-0 w-9 h-9 flex items-center justify-center rounded-full border border-zinc-200 dark:border-zinc-700 text-base"
      >
        📅
      </button>
    </div>
  );
}

export default function MobileHome(p: MobileHomeProps) {
  const [calendarOpen, setCalendarOpen] = useState(false);
  return (
    <div>
      <InfoPeek />
      <SearchBar search={p.search} onChange={p.onSearchChange} onClear={p.onSearchClear} />
      <DateChipRow
        sessionDates={p.sessionDates}
        selectedDate={p.selectedDate}
        onSelect={p.onSelect}
        onOpenCalendar={() => setCalendarOpen(true)}
      />
      <ResultCount search={p.search} count={p.searchMatches.length} />
      <TopList
        key={p.search.trim() ? "search" : "browse"}
        grouped={p.grouped}
        onTopFocus={p.onTopFocus}
        defaultOpen={!p.search.trim()}
        focusDate={p.search.trim() ? p.selectedDate : undefined}
      />
      <MobileSheet open={calendarOpen} onClose={() => setCalendarOpen(false)} title="Termin wählen">
        <Calendar
          sessionDates={p.sessionDates}
          highlightedDates={p.search.trim() ? p.searchMatchDates : undefined}
          selectedDate={p.selectedDate}
          year={p.calYear}
          month={p.calMonth}
          onSelect={(d) => {
            p.onSelect(d);
            setCalendarOpen(false);
          }}
          onMonthChange={p.onMonthChange}
        />
      </MobileSheet>
    </div>
  );
}
