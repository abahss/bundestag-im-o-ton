import { describe, expect, test } from "vitest";
import { emptyMonthNote, isRecessDay, recessForMonth } from "./recesses";

// These tests pin the behaviour against the 2026 Sommerpause entry
// (2026-07-11 – 2026-09-07) currently in RECESSES.

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

describe("recessForMonth", () => {
  test("August 2026 is fully covered", () => {
    expect(recessForMonth(2026, 7)?.label).toBe("Sommerpause");
  });
  test("July and September 2026 partly overlap", () => {
    expect(recessForMonth(2026, 6)?.label).toBe("Sommerpause");
    expect(recessForMonth(2026, 8)?.label).toBe("Sommerpause");
  });
  test("October 2026 does not", () => {
    expect(recessForMonth(2026, 9)).toBeNull();
  });
});

describe("emptyMonthNote", () => {
  const latestSession = new Date(2026, 6, 10); // data ends 10 Jul 2026

  test("month with sessions -> no note", () => {
    expect(
      emptyMonthNote(2026, 6, { monthHasSession: true, latestSession, today: new Date(2026, 8, 8) }),
    ).toBeNull();
  });

  test("August 2026 -> planmäßig sitzungsfrei", () => {
    const note = emptyMonthNote(2026, 7, {
      monthHasSession: false,
      latestSession,
      today: new Date(2026, 8, 8),
    });
    expect(note).toContain("Sommerpause");
    expect(note).toContain("Es fehlen keine Sitzungen");
  });

  test("September 2026 before protocols land -> recess ends + wird ergänzt", () => {
    const note = emptyMonthNote(2026, 8, {
      monthHasSession: false,
      latestSession,
      today: new Date(2026, 8, 8),
    });
    expect(note).toContain("Sommerpause bis 07.09.");
    expect(note).toContain("08.09.");
  });

  test("future month -> no note (not navigable)", () => {
    expect(
      emptyMonthNote(2026, 10, {
        monthHasSession: false,
        latestSession,
        today: new Date(2026, 8, 8),
      }),
    ).toBeNull();
  });

  test("current month, no recess, data behind -> Protokolle-Hinweis", () => {
    const note = emptyMonthNote(2026, 9, {
      monthHasSession: false,
      latestSession: new Date(2026, 8, 25),
      today: new Date(2026, 9, 5),
    });
    expect(note).toContain("noch keine Protokolle");
  });
});
