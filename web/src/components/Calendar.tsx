"use client";

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

  const atMin = year < minDate.getFullYear() || (year === minDate.getFullYear() && month <= minDate.getMonth());
  const atMax = year > maxDate.getFullYear() || (year === maxDate.getFullYear() && month >= maxDate.getMonth());

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
        <button onClick={prev} disabled={atMin} className="w-8 h-8 flex items-center justify-center rounded-lg text-[#023047] dark:text-white disabled:opacity-25 hover:bg-zinc-100 dark:hover:bg-zinc-800">‹</button>
        <span className="text-sm font-semibold text-[#023047] dark:text-white">{MONTHS_DE[month]} {year}</span>
        <button onClick={next} disabled={atMax} className="w-8 h-8 flex items-center justify-center rounded-lg text-[#023047] dark:text-white disabled:opacity-25 hover:bg-zinc-100 dark:hover:bg-zinc-800">›</button>
      </div>

      <div className="grid grid-cols-7 mb-1">
        {DAYS_DE.map((d) => (
          <div key={d} className="text-center text-[10px] font-semibold text-zinc-400">{d}</div>
        ))}
      </div>

      {weeks.map((week, wi) => (
        <div key={wi} className="grid grid-cols-7">
          {week.map((day, di) => {
            if (!day) return <div key={di} />;
            const dateStr = formatDate(new Date(year, month, day));
            const isActive = activeDates.has(dateStr);
            const isSession = sessionDates.has(dateStr);
            const isSelected = dateStr === selectedDate;
            return (
              <button
                key={di}
                disabled={!isActive}
                onClick={() => isActive && onSelect(dateStr)}
                className={[
                  "mx-auto my-0.5 w-8 h-8 flex items-center justify-center rounded-lg text-sm transition-colors",
                  isSelected
                    ? "bg-[#219EBC] text-white font-semibold"
                    : isActive
                    ? "bg-[#D6EEF7] text-[#023047] hover:bg-[#219EBC] hover:text-white dark:bg-[#219EBC]/20 dark:text-white"
                    : isSession
                    ? "text-zinc-300 dark:text-zinc-600 cursor-default"
                    : "text-zinc-200 dark:text-zinc-800 cursor-default",
                ].join(" ")}
              >
                {day}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
