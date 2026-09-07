"use client";

import { emptyMonthNote, isRecessDay } from "@/lib/recesses";

const MONTHS_DE = [
  "Januar","Februar","März","April","Mai","Juni",
  "Juli","August","September","Oktober","November","Dezember",
];
const DAYS_DE = ["Mo","Di","Mi","Do","Fr","Sa","So"];

function parseDate(str: string): Date {
  const [day, month, year] = str.split(".");
  return new Date(+year, +month - 1, +day);
}

function formatDate(d: Date): string {
  return `${String(d.getDate()).padStart(2,"0")}.${String(d.getMonth()+1).padStart(2,"0")}.${d.getFullYear()}`;
}

function getMonthGrid(year: number, month: number): (number | null)[][] {
  const firstDay = new Date(year, month, 1).getDay();
  const offset = firstDay === 0 ? 6 : firstDay - 1;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = Array(offset).fill(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks: (number | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}

export default function Calendar({
  sessionDates,
  highlightedDates,
  selectedDate,
  year,
  month,
  onSelect,
  onMonthChange,
}: {
  sessionDates: Set<string>;
  highlightedDates?: Set<string>;
  selectedDate: string;
  year: number;
  month: number;
  onSelect: (date: string) => void;
  onMonthChange: (year: number, month: number) => void;
}) {
  const activeDates = highlightedDates ?? sessionDates;

  const dates = [...sessionDates].map(parseDate);
  const minDate = dates.reduce((a, b) => (a < b ? a : b), dates[0]);
  const maxDate = dates.reduce((a, b) => (a > b ? a : b), dates[0]);

  // Let navigation reach the current month even when the newest protocols
  // aren't in yet — otherwise an ongoing recess (or a resumed session whose
  // protocols land in the evening) can't be shown at all.
  const now = new Date();
  const ym = (y: number, m: number) => y * 12 + m;
  const curYm = ym(year, month);
  const navMaxYm = Math.max(ym(maxDate.getFullYear(), maxDate.getMonth()), ym(now.getFullYear(), now.getMonth()));

  const atMin = curYm <= ym(minDate.getFullYear(), minDate.getMonth());
  const atMax = curYm >= navMaxYm;

  const daysInVisibleMonth = new Date(year, month + 1, 0).getDate();
  const monthHasSession = Array.from({ length: daysInVisibleMonth }, (_, i) => i + 1).some(
    (d) => sessionDates.has(formatDate(new Date(year, month, d))),
  );
  const monthNote = emptyMonthNote(year, month, {
    monthHasSession,
    latestSession: dates.length ? maxDate : null,
  });

  function prev() {
    if (month === 0) onMonthChange(year - 1, 11);
    else onMonthChange(year, month - 1);
  }
  function next() {
    if (month === 11) onMonthChange(year + 1, 0);
    else onMonthChange(year, month + 1);
  }

  const weeks = getMonthGrid(year, month);

  return (
    <div className="select-none">
      <div className="flex items-center justify-between mb-3">
        <button onClick={prev} disabled={atMin} aria-label="Vorheriger Monat" className="w-8 h-8 flex items-center justify-center rounded-lg text-lg font-bold text-[#023047] dark:text-white disabled:opacity-25 hover:bg-zinc-100 dark:hover:bg-zinc-800">‹</button>
        <span aria-live="polite" className="text-sm font-semibold text-[#023047] dark:text-white">{MONTHS_DE[month]} {year}</span>
        <button onClick={next} disabled={atMax} aria-label="Nächster Monat" className="w-8 h-8 flex items-center justify-center rounded-lg text-lg font-bold text-[#023047] dark:text-white disabled:opacity-25 hover:bg-zinc-100 dark:hover:bg-zinc-800">›</button>
      </div>

      <div className="grid grid-cols-7 mb-1">
        {DAYS_DE.map((d) => (
          <div key={d} className="text-center text-[10px] font-semibold text-zinc-500 dark:text-zinc-400">{d}</div>
        ))}
      </div>

      {weeks.map((week, wi) => (
        <div key={wi} className="grid grid-cols-7">
          {week.map((day, di) => {
            if (!day) return <div key={di} />;
            const cellDate = new Date(year, month, day);
            const dateStr = formatDate(cellDate);
            const isActive = activeDates.has(dateStr);
            const isSelected = dateStr === selectedDate;
            const isRecess = !isActive && isRecessDay(cellDate);
            return (
              <button
                key={di}
                disabled={!isActive}
                onClick={() => isActive && onSelect(dateStr)}
                aria-label={`${day}. ${MONTHS_DE[month]} ${year}`}
                aria-current={isSelected ? "date" : undefined}
                className={[
                  "mx-auto my-0.5 w-8 h-8 flex items-center justify-center rounded-lg text-sm transition-colors",
                  isSelected
                    ? "bg-[#219EBC] text-white font-semibold"
                    : isActive
                    ? "bg-[#BEE3F2] text-[#023047] font-medium hover:bg-[#219EBC] hover:text-white dark:bg-[#219EBC]/30 dark:text-white"
                    : isRecess
                    ? "text-zinc-300 dark:text-zinc-700 cursor-default"
                    : "text-zinc-600 dark:text-zinc-400 cursor-default",
                ].join(" ")}
              >
                {day}
              </button>
            );
          })}
        </div>
      ))}

      {/* Persistent live region so paging into an empty (recess) month
          announces the explanation, not just a grid of disabled days. */}
      <p
        role="status"
        className={`text-xs leading-snug text-zinc-500 dark:text-zinc-400 ${monthNote ? "mt-3" : ""}`}
      >
        {monthNote}
      </p>
    </div>
  );
}
