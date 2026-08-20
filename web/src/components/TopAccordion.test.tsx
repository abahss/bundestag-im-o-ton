// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import TopList from "./TopList";
import { Top } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

function makeTop(overrides: Partial<Top>): Top {
  return {
    top_key: "default-key",
    top_id: "Tagesordnungspunkt 1",
    title: "",
    subtitle: "",
    session: "1",
    date: "2026-08-18",
    drucksache: "",
    drucksache_url: "",
    subtopics: [],
    topic: "Test topic",
    active: true,
    pdf_url: "",
    has_abstimmung: false,
    ...overrides,
  };
}

describe("TopList open-state restore", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  test("first TOP of a newly selected day opens even with a stale openTops snapshot from a previous day", () => {
    sessionStorage.setItem("openTops", JSON.stringify(["stale-key-from-other-day"]));

    const dayA = new Map([["2026-08-18", [makeTop({ top_key: "day-a-top-1", date: "2026-08-18" })]]]);
    const dayB = new Map([["2026-08-19", [makeTop({ top_key: "day-b-top-1", date: "2026-08-19" })]]]);

    const { rerender } = render(<TopList grouped={dayA} defaultOpen={true} />);
    rerender(<TopList grouped={dayB} defaultOpen={true} />);

    const dayBAccordion = document.querySelector('[data-top-key="day-b-top-1"]');
    expect(dayBAccordion).toHaveAttribute("data-open", "true");
  });

  test("a fresh mount (e.g. back-navigation) restores every previously open accordion from the snapshot", () => {
    sessionStorage.setItem("openTops", JSON.stringify(["top-2", "top-3"]));

    const day = new Map([
      [
        "2026-08-18",
        [
          makeTop({ top_key: "top-1", date: "2026-08-18" }),
          makeTop({ top_key: "top-2", date: "2026-08-18" }),
          makeTop({ top_key: "top-3", date: "2026-08-18" }),
        ],
      ],
    ]);

    render(<TopList grouped={day} defaultOpen={false} />);

    expect(document.querySelector('[data-top-key="top-1"]')).toHaveAttribute("data-open", "false");
    expect(document.querySelector('[data-top-key="top-2"]')).toHaveAttribute("data-open", "true");
    expect(document.querySelector('[data-top-key="top-3"]')).toHaveAttribute("data-open", "true");
  });
});
