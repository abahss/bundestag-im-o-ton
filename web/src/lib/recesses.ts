// Sitzungsfreie Zeiträume des Bundestags ("Sommerpause" usw.).
//
// Einmal im Jahr aus dem offiziellen Sitzungskalender abschreiben:
// https://www.bundestag.de/parlament/plenum/sitzungskalender
//
// Bewusst kuratiert und NICHT aus Kalenderlücken abgeleitet: eine Lücke kann
// auch bedeuten, dass die Protokolle noch nicht eingelesen sind (die
// Update-Pipeline hängt gelegentlich). Nur ein eingetragener Zeitraum wird als
// "planmäßig sitzungsfrei" ausgewiesen.
//
// start/end sind ISO-Daten (yyyy-mm-dd), inklusive, und umfassen die
// sitzungsfreien Tage — also vom Tag nach der letzten Sitzung bis zum Tag vor
// der Wiederaufnahme.

export type Recess = { start: string; end: string; label: string };

export const RECESSES: Recess[] = [
  { start: "2026-07-11", end: "2026-09-06", label: "Sommerpause" },
];

const pad = (n: number) => String(n).padStart(2, "0");
const isoOf = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const parseIso = (s: string) => new Date(`${s}T00:00:00`);
const ymOf = (d: Date) => d.getFullYear() * 12 + d.getMonth();

/** True if the given day falls inside a curated recess. */
export function isRecessDay(d: Date): boolean {
  const s = isoOf(d);
  return RECESSES.some((r) => r.start <= s && s <= r.end);
}

/** The recess that overlaps the given (0-based) month, if any. */
export function recessForMonth(year: number, month: number): Recess | null {
  const first = `${year}-${pad(month + 1)}-01`;
  const last = `${year}-${pad(month + 1)}-${pad(new Date(year, month + 1, 0).getDate())}`;
  return RECESSES.find((r) => r.start <= last && r.end >= first) ?? null;
}

/**
 * Explanatory caption for a calendar month that shows no sessions, so an empty
 * month reads as "planmäßig sitzungsfrei" or "Protokolle noch nicht da" rather
 * than "hier fehlen Daten". Returns null when the month has sessions or lies in
 * the future (not reachable in the calendar).
 */
export function emptyMonthNote(
  year: number,
  month: number,
  opts: { monthHasSession: boolean; latestSession: Date | null; today?: Date },
): string | null {
  if (opts.monthHasSession) return null;

  const today = opts.today ?? new Date();
  const ym = year * 12 + month;
  if (ym > ymOf(today)) return null; // future month — calendar can't navigate here

  const recess = recessForMonth(year, month);
  const recessEndYm = recess ? ymOf(parseIso(recess.end)) : null;

  if (recess && recessEndYm !== null && recessEndYm > ym) {
    return `${recess.label} — in dieser Zeit tagt der Bundestag planmäßig nicht. Es fehlen keine Sitzungen.`;
  }

  if (recess && recessEndYm === ym) {
    const end = parseIso(recess.end);
    const resume = new Date(end);
    resume.setDate(resume.getDate() + 1);
    return `${recess.label} bis ${pad(end.getDate())}.${pad(end.getMonth() + 1)}. Die Sitzungen ab dem ${pad(resume.getDate())}.${pad(resume.getMonth() + 1)}. werden noch ergänzt — die Protokolle erscheinen am Sitzungsabend.`;
  }

  const latestYm = opts.latestSession ? ymOf(opts.latestSession) : null;
  if (latestYm !== null && ym > latestYm) {
    return "Für diesen Monat liegen noch keine Protokolle vor. Neue Protokolle erscheinen am Sitzungsabend.";
  }

  return "In diesem Monat tagte der Bundestag nicht.";
}

/**
 * One-line notice for the homepage: recess in progress, or "just resumed and
 * data is catching up". Returns null once the newest data is past the most
 * recent recess (nothing worth saying).
 */
export function homeRecessNotice(
  latestSession: Date | null,
  today: Date = new Date(),
): string | null {
  const t = isoOf(today);

  const current = RECESSES.find((r) => r.start <= t && t <= r.end);
  if (current) {
    const end = parseIso(current.end);
    return `Der Bundestag ist noch bis zum ${pad(end.getDate())}.${pad(end.getMonth() + 1)}.${end.getFullYear()} in der ${current.label}. Zusammenfassungen sind ab Dezember 2025 verfügbar.`;
  }

  const lastEnded = RECESSES
    .filter((r) => r.end < t)
    .sort((a, b) => (a.end < b.end ? 1 : -1))[0];
  if (lastEnded && latestSession && isoOf(latestSession) <= lastEnded.start) {
    const resume = parseIso(lastEnded.end);
    resume.setDate(resume.getDate() + 1);
    return `Der Bundestag tagt seit dem ${pad(resume.getDate())}.${pad(resume.getMonth() + 1)}. wieder. Die Sitzungen nach der ${lastEnded.label} werden gerade ergänzt — die Protokolle erscheinen am Sitzungsabend.`;
  }

  return null;
}
