interface SummaryCache {
  general?: string;
  parties?: Record<string, string>;
}

function key(topKey: string, lang: string) {
  // German keeps the legacy key so existing caches stay valid
  return lang === "de" ? `summaries:${topKey}` : `summaries:${topKey}:${lang}`;
}

export function loadSummaryCache(topKey: string, lang: string = "de"): SummaryCache {
  try {
    const s = localStorage.getItem(key(topKey, lang));
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}

export function saveSummaryCache(topKey: string, update: SummaryCache, lang: string = "de") {
  try {
    const existing = loadSummaryCache(topKey, lang);
    const merged: SummaryCache = {
      ...existing,
      ...update,
      parties: { ...existing.parties, ...update.parties },
    };
    localStorage.setItem(key(topKey, lang), JSON.stringify(merged));
  } catch {}
}
