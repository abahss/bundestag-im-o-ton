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

// A day whose TOP-3 continuation announcement carried no content at all (S93, 10.09.2026)
// is dropped from tops.json by the backend — the hub has no real TOP to point at.
const HUB_WITHOUT_EINBRINGUNG = top({
  top_key: "93_Haushaltswoche",
  top_id: "Haushaltswoche",
  einbringung: "",
});

// A day whose TOP-3 continuation announcement repeats the a)/b) recap (S92, 09.09.2026)
// does survive as a real entry.
const EINBRINGUNG_92 = top({
  top_key: "92_Tagesordnungspunkt 3",
  subtopics: [{ key: "a", title: "Haushaltsgesetz", nas: "", drucksache: "21/7300", drucksache_url: "", drucksachen: ["21/7300"] }],
});
const HUB_WITH_EINBRINGUNG = top({
  top_key: "92_Haushaltswoche",
  top_id: "Haushaltswoche",
  einbringung: "92_Tagesordnungspunkt 3",
});

describe("expandHaushaltswoche", () => {
  test("skips the TOP-3 homepage row when the day has no real Einbringung TOP", () => {
    const result = expandHaushaltswoche([HUB_WITHOUT_EINBRINGUNG]);

    // no dead-end row pointing at an empty or synthetic top_key
    expect(result.some((t) => t.top_key === "")).toBe(false);
    expect(result.some((t) => t.top_key.includes("::top3"))).toBe(false);
    // the hub itself is still hidden from the plain list
    expect(result.some((t) => t.top_id === "Haushaltswoche")).toBe(false);
  });

  test("still creates a real TOP-3 row when the day has an Einbringung TOP", () => {
    const result = expandHaushaltswoche([HUB_WITH_EINBRINGUNG, EINBRINGUNG_92]);

    const row = result.find((t) => t.top_key === "92_Tagesordnungspunkt 3");
    expect(row).toBeDefined();
    expect(row?.subtopics).toEqual(EINBRINGUNG_92.subtopics);
    // the real underlying TOP entry is folded into the synthetic row, not duplicated
    expect(result.filter((t) => t.top_key === "92_Tagesordnungspunkt 3")).toHaveLength(1);
  });
});
