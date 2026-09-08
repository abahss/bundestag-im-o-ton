import Fuse from "fuse.js";
import { describe, expect, test } from "vitest";
import type { Top } from "./api";
import { FUSE_OPTIONS, searchTops, substringMatch } from "./search";

function top(partial: Partial<Top> & { top_key: string }): Top {
  return {
    top_id: "Tagesordnungspunkt 1",
    title: "",
    subtitle: "",
    session: "90",
    date: "10.07.2026",
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

const WOLF = top({ top_key: "90_TOP 3", title: "Zweite Beratung", topic: "Wolf, Artenschutz" });
const RENTE = top({
  top_key: "90_TOP 4",
  topic: "Rentenreform",
  subtopics: [{ key: "a", title: "Antrag der SPD", nas: "", drucksache: "", drucksache_url: "", drucksachen: [] }],
});

describe("substringMatch", () => {
  test("without a blob: matches the title-level fields, case-insensitive", () => {
    expect(substringMatch(WOLF, "artenschutz")).toBe(true);
    expect(substringMatch(RENTE, "antrag der spd")).toBe(true);
    expect(substringMatch(WOLF, "weidetierhaltung")).toBe(false);
  });

  test("with a blob: matches only the blob (which already contains the title fields)", () => {
    const blob = "zweite beratung wolf, artenschutz die spd fordert mehr weidetierhaltung";
    expect(substringMatch(WOLF, "weidetierhaltung", blob)).toBe(true);
    expect(substringMatch(WOLF, "artenschutz", blob)).toBe(true);
    expect(substringMatch(WOLF, "kernenergie", blob)).toBe(false);
  });

  test("empty blob means indexed-but-nothing: no title fallback", () => {
    expect(substringMatch(WOLF, "artenschutz", "")).toBe(false);
  });
});

describe("searchTops", () => {
  const topics = [WOLF, RENTE];
  const fuse = new Fuse(topics, FUSE_OPTIONS);

  test("blank query -> nothing", () => {
    expect(searchTops(topics, "  ", fuse, null)).toEqual([]);
  });

  test("no index -> title-level substring", () => {
    expect(searchTops(topics, "artenschutz", fuse, null)).toEqual([WOLF]);
  });

  test("with index -> full-text hit that the titles don't have", () => {
    const index = { "90_TOP 3": "zweite beratung wolf herdenschutzzäune finanzieren", "90_TOP 4": "rentenreform" };
    expect(searchTops(topics, "herdenschutzzäune", fuse, index)).toEqual([WOLF]);
  });

  test("falls back to fuzzy only when substring finds nothing", () => {
    // "Rentenreformm" (typo) has no substring hit, Fuse should still find RENTE
    const res = searchTops(topics, "Rentenreformm", fuse, null);
    expect(res).toContain(RENTE);
  });
});
