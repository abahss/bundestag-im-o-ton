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
  { start: "2026-07-11", end: "2026-09-07", label: "Sommerpause" },
];

const pad = (n: number) => String(n).padStart(2, "0");
const isoOf = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const parseIso = (s: string) => new Date(`${s}T00:00:00`);

/** True if the given day falls inside a curated recess. */
export function isRecessDay(d: Date): boolean {
  const s = isoOf(d);
  return RECESSES.some((r) => r.start <= s && s <= r.end);
}

/**
 * Note shown under the calendar while the Bundestag is in — or just back from —
 * a recess whose sessions aren't in the data yet. Not tied to the displayed
 * month. Returns null once the newest session in the data is past the recess.
 */
export function recessNote(latestSession: Date | null, today: Date = new Date()): string | null {
  const t = isoOf(today);
  const relevant = RECESSES.find((r) => {
    const ongoing = r.start <= t && t <= r.end;
    const aftermathPending = r.end < t && (!latestSession || isoOf(latestSession) < r.start);
    return ongoing || aftermathPending;
  });
  if (!relevant) return null;

  const from = parseIso(relevant.start);
  from.setDate(from.getDate() - 1); // last session day before the recess
  const to = parseIso(relevant.end);
  to.setDate(to.getDate() + 1); // first session day after
  const fmt = (d: Date) => `${d.getDate()}.${pad(d.getMonth() + 1)}`;

  return `${relevant.label} vom ${fmt(from)} bis zum ${fmt(to)}. Neue Sitzungen erscheinen, sobald die Protokolle vorliegen.`;
}
