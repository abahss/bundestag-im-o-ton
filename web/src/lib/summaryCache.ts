interface SummaryCache {
  general?: string;
  parties?: Record<string, string>;
}

function key(topKey: string) {
  return `summaries:${topKey}`;
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
