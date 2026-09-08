import { describe, expect, test } from "vitest";
import { isRecessDay, recessNote } from "./recesses";

// Pinned against the 2026 Sommerpause entry (2026-07-11 – 2026-09-07) in RECESSES.

describe("isRecessDay", () => {
  test("inside the Sommerpause", () => {
    expect(isRecessDay(new Date(2026, 7, 15))).toBe(true); // 15 Aug
    expect(isRecessDay(new Date(2026, 8, 7))).toBe(true); // 7 Sep (last recess day)
  });
  test("last session before / first day after", () => {
    expect(isRecessDay(new Date(2026, 6, 10))).toBe(false); // 10 Jul (session)
    expect(isRecessDay(new Date(2026, 8, 8))).toBe(false); // 8 Sep (resumed)
  });
});

describe("recessNote", () => {
  const preRecess = new Date(2026, 6, 10); // data ends 10 Jul 2026

  test("during the recess", () => {
    expect(recessNote(preRecess, new Date(2026, 7, 20))).toBe(
      "Sommerpause vom 10.07 bis zum 8.09. Neue Sitzungen erscheinen, sobald die Protokolle vorliegen.",
    );
  });

  test("recess over but post-recess sessions not in the data yet", () => {
    expect(recessNote(preRecess, new Date(2026, 8, 9))).toContain("Sommerpause vom 10.07 bis zum 8.09");
  });

  test("null once the data has caught up past the recess", () => {
    expect(recessNote(new Date(2026, 8, 10), new Date(2026, 8, 20))).toBeNull();
  });

  test("null well before the recess", () => {
    expect(recessNote(new Date(2026, 5, 1), new Date(2026, 5, 15))).toBeNull();
  });
});
