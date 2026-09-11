import { describe, expect, test } from "vitest";
import type { Top } from "./api";
import { expandHaushaltswoche } from "./haushaltswoche";

function top(partial: Partial<Top> & { top_key: string }): Top {
  return {
    top_id: "Tagesordnungspunkt 1",
    title: "",
    subtitle: "",
    session: "93",
    date: "10.09.2026",
    drucksache: "",
    drucksache_url: "",
    drucksachen: [],
    subtopics: [],
    topic: "",
    active: true,
    pdf_url: "",
    has_abstimmung: false,
    ...partial,
  };
}

const SUBTOPICS = [
  { key: "a", title: "Haushaltsgesetz", nas: "", drucksache: "21/7300", drucksache_url: "https://.../7300.pdf", drucksachen: ["21/7300"] },
  { key: "b", title: "Finanzplan", nas: "", drucksache: "21/7301", drucksache_url: "https://.../7301.pdf", drucksachen: ["21/7301"] },
];

// Day 1 (S91, 08.09.2026): the real Einbringung — Klingbeil's speech, but he's a
// minister (no <fraktion>), so this is not a "Parteirede" either — active: false.
const EINBRINGUNG_91 = top({
  top_key: "91_Tagesordnungspunkt 3",
  session: "91",
  date: "08.09.2026",
  active: false,
  subtopics: SUBTOPICS,
});
const HUB_91 = top({
  top_key: "91_Haushaltswoche",
  top_id: "Haushaltswoche",
  session: "91",
  date: "08.09.2026",
  einbringung: "91_Tagesordnungspunkt 3",
});

// Day 2 (S92, 09.09.2026): the continuation announcement repeats the exact same a)/b)
// recap (same Drucksachen), no new content — must not get its own homepage row.
const EINBRINGUNG_92 = top({
  top_key: "92_Tagesordnungspunkt 3",
  session: "92",
  date: "09.09.2026",
  active: false,
  subtopics: SUBTOPICS,
});
const HUB_92 = top({
  top_key: "92_Haushaltswoche",
  top_id: "Haushaltswoche",
  session: "92",
  date: "09.09.2026",
  einbringung: "92_Tagesordnungspunkt 3",
});

// Day 3 (S93, 10.09.2026): the continuation announcement carries no content at all and
// is dropped from tops.json entirely by the backend — the hub has no real TOP to point at.
const HUB_93 = top({
  top_key: "93_Haushaltswoche",
  top_id: "Haushaltswoche",
  session: "93",
  date: "10.09.2026",
  einbringung: "",
});

describe("expandHaushaltswoche", () => {
  test("skips the TOP-3 homepage row when the day has no real Einbringung TOP", () => {
    const result = expandHaushaltswoche([HUB_93]);

    // no dead-end row pointing at an empty or synthetic top_key
    expect(result.some((t) => t.top_key === "")).toBe(false);
    expect(result.some((t) => t.top_key.includes("::top3"))).toBe(false);
    // the hub itself is still hidden from the plain list
    expect(result.some((t) => t.top_id === "Haushaltswoche")).toBe(false);
  });

  test("creates a non-clickable TOP-3 row for the earliest day's real Einbringung", () => {
    const result = expandHaushaltswoche([HUB_91, EINBRINGUNG_91]);

    const row = result.find((t) => t.top_key === "91_Tagesordnungspunkt 3");
    expect(row).toBeDefined();
    expect(row?.subtopics).toEqual(SUBTOPICS);
    // no debate happened here (minister's speech carries no <fraktion>) — same
    // "keine Parteireden" treatment as any other document-only TOP, no CTA button
    expect(row?.active).toBe(false);
    // the real underlying TOP entry is folded into the synthetic row, not duplicated
    expect(result.filter((t) => t.top_key === "91_Tagesordnungspunkt 3")).toHaveLength(1);
  });

  test("hides a later day's repeated TOP-3 recap entirely, not just non-clickable", () => {
    const result = expandHaushaltswoche([HUB_91, EINBRINGUNG_91, HUB_92, EINBRINGUNG_92]);

    // exactly one TOP-3 row (day 1's) — day 2's identical recap does not duplicate it
    expect(result.filter((t) => t.top_id === "Tagesordnungspunkt 3")).toHaveLength(1);
    expect(result.some((t) => t.top_key === "91_Tagesordnungspunkt 3")).toBe(true);
    // day 2's underlying TOP entry is hidden outright, not shown as an ordinary row either
    expect(result.some((t) => t.top_key === "92_Tagesordnungspunkt 3")).toBe(false);
  });
});
