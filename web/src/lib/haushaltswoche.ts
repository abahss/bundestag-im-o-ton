// The "Haushaltswoche" hub: the backend emits a synthetic tops.json entry
// ({session}_Haushaltswoche, top_id "Haushaltswoche") that groups a session's
// Einzelplan ressort debates plus the Einbringung TOP onto one page.
import type { Top } from "@/lib/api";

export const HAUSHALTSWOCHE_TOP_ID = "Haushaltswoche";

// Shared with HaushaltswochePage.tsx (section heading) so the homepage row and the
// page it leads to always say the same thing.
export const EINBRINGUNG_TITLE = "Einbringung durch die Bundesregierung";

export function isHaushaltswoche(top: { top_id: string } | undefined | null): boolean {
  return top?.top_id === HAUSHALTSWOCHE_TOP_ID;
}

export type HaushaltswocheView = "overview" | "top3";

/** Any key a Haushaltswoche page can be reached under — the hub itself, or its
 *  Einbringung TOP (a real top_key), but ONLY while that TOP is the inactive,
 *  content-only stub (a minister's speech or a bare a)/b) recap). A later day's
 *  own "Tagesordnungspunkt 3" can instead be a genuinely active debate (e.g. the
 *  closing "Schlussrunde") — same condition expandHaushaltswoche() uses to decide
 *  whether to leave that row alone. An active one is NOT resolved here: the caller
 *  falls through to the ordinary TOP page (general summary + party cards), same as
 *  any Einzelplan debate. The Einzelplan ressort debates are NOT part of this
 *  either: they carry their own real content and render as ordinary TOPs too. */
export function resolveHaushaltswoche(
  topics: Top[], key: string,
): { hub: Top; view: HaushaltswocheView } | undefined {
  const byKey = new Map(topics.map((t) => [t.top_key, t]));
  for (const hub of topics.filter(isHaushaltswoche)) {
    if (hub.top_key === key) return { hub, view: "overview" };
    if (hub.einbringung === key && !byKey.get(key)?.active) return { hub, view: "top3" };
  }
  return undefined;
}

/** Rework the homepage list around a session's Haushaltswoche hub: the hub row
 *  itself ("Bundeshaushalt 2027 – 1. Lesung") is dropped from the list, and the
 *  Einbringung TOP of the EARLIEST day is shown as a dedicated "TOP 3" row. A later
 *  day's own "Tagesordnungspunkt 3" occurrence is either an inactive, content-free
 *  continuation announcement (an empty stub, or one that only repeats the day-1 a)/b)
 *  recap with no new content/speeches) — hidden entirely, not shown as a duplicate —
 *  or a genuinely active debate of its own (e.g. the closing "Schlussrunde" on the
 *  final day, with real party speeches), which is left alone as an ordinary TOP like
 *  any Einzelplan debate, no special-casing. The hub's overview page stays reachable
 *  by URL; nothing links to it. */
export function expandHaushaltswoche(topics: Top[]): Top[] {
  const hubs = topics.filter(isHaushaltswoche);
  if (hubs.length === 0) return topics;
  const byKey = new Map(topics.map((t) => [t.top_key, t]));
  const firstHub = [...hubs].sort((a, b) => Number(a.session) - Number(b.session))[0];

  const hide = new Set<string>();
  const extraRows: Top[] = [];
  for (const hub of hubs) {
    // A day whose TOP-3 continuation announcement carried no content at all (no a)/b)
    // recap, no subtopics) is dropped from tops.json entirely by the backend — there is
    // nothing to link to, so skip the row rather than point it at a dead key.
    if (!hub.einbringung) continue;
    const einbringung = byKey.get(hub.einbringung);

    if (hub !== firstHub) {
      // A later day's own active debate (e.g. the closing "Schlussrunde") is real,
      // new content — leave it in the list untouched, ordinary TOP rendering already
      // handles it. Only an inactive recap/stub gets hidden.
      if (!einbringung?.active) hide.add(hub.einbringung);
      continue;
    }
    hide.add(hub.einbringung);

    extraRows.push({
      session: hub.session, date: hub.date, subtitle: "", drucksache: "",
      drucksache_url: "", drucksachen: [],
      // Klingbeil's Einbringungsrede carries no <fraktion> (he's a minister, not an MP)
      // and is therefore not a "Parteirede" either — same "keine Parteireden" treatment
      // as any other document-only TOP, with the a)/b) PDFs shown inline (TopAccordion).
      active: einbringung?.active ?? false,
      pdf_url: hub.pdf_url, has_abstimmung: false,
      top_key: hub.einbringung,
      top_id: "Tagesordnungspunkt 3", topic: EINBRINGUNG_TITLE, title: EINBRINGUNG_TITLE,
      // a/b-Zahlenwerke as the list preview line — same subtopics the real TOP 3 has.
      subtopics: einbringung?.subtopics ?? [],
    });
  }
  return [
    ...topics.filter((t) => !hide.has(t.top_key) && !isHaushaltswoche(t)),
    ...extraRows,
  ];
}
