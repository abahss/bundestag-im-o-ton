interface SummaryCache {
  general?: string;
  parties?: Record<string, string>;
}

// v2: only ever written after a user's own "Neu generieren" click (see
// ParliamentChart/GeneralSummary), never seeded from the server's initial
// response. v1 blindly seeded on first render and never invalidated, so a
// returning visitor's cache could silently diverge from the server forever —
// bumping the namespace drops all v1 entries instead of migrating them.
function key(topKey: string) {
  return `summaries:v2:${topKey}`;
}

export function loadSummaryCache(topKey: string): SummaryCache {
  try {
    const s = localStorage.getItem(key(topKey));
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}

export function saveSummaryCache(topKey: string, update: SummaryCache) {
  try {
    const existing = loadSummaryCache(topKey);
    const merged: SummaryCache = {
      ...existing,
      ...update,
      parties: { ...existing.parties, ...update.parties },
    };
    localStorage.setItem(key(topKey), JSON.stringify(merged));
  } catch {}
}
