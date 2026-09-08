import Fuse, { IFuseOptions } from "fuse.js";
import type { Top } from "./api";

export const FUSE_OPTIONS: IFuseOptions<Top> = {
  keys: ["title", "subtitle", "topic", "subtopics.title"],
  threshold: 0.3,
  ignoreLocation: true,
  minMatchCharLength: 3,
};

// Fuse's fuzzy/edit-distance scoring is only reliable as a *fallback* for
// short German queries: at any threshold loose enough to survive a real
// typo (e.g. "Gesuntheit" -> "Gesundheit"), short words also start
// fuzzy-matching unrelated longer words purely by coincidental edit
// distance (e.g. "Rente" matched "retten", "AfD" matched a third of all
// TOPs) — verified empirically against the real dataset, not a hunch.
// Substring search has no such failure mode, so it always wins when it
// finds anything; Fuse only runs when the literal search comes up empty.
//
// `blob` (from /search-index, loaded after mount) is the full searchable text —
// title + subtitle + topic + subtopic titles + general summary + party
// Kernpositionen + quotes + Drucksachen-Zusammenfassungen, lower-cased. Until it
// loads we fall back to the title-level fields that ship with the TOP. Fuse
// stays on the short fields only — fuzzy matching over full summary text would
// be all noise.
export function substringMatch(top: Top, query: string, blob?: string): boolean {
  const q = query.toLowerCase();
  if (blob !== undefined) return blob.includes(q);
  const subtopicTitles = top.subtopics.map((s) => s.title);
  const fields = [top.title, top.subtitle, top.topic, ...subtopicTitles].join(" ").toLowerCase();
  return fields.includes(q);
}

/** Substring match first (title-level, or full blob once the index is in);
 *  Fuse fuzzy fallback only when substring finds nothing. */
export function searchTops(
  topics: Top[],
  query: string,
  fuse: Fuse<Top>,
  searchIndex: Record<string, string> | null,
): Top[] {
  const q = query.trim();
  if (!q) return [];
  const exact = topics.filter((t) => substringMatch(t, q, searchIndex?.[t.top_key]));
  if (exact.length > 0) return exact;
  return fuse.search(q).map((r) => r.item);
}
