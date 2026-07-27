/** Session-only recent analyses list — no persistence beyond the browser tab. */

export type RecentAnalysisEntry = {
  ticker: string;
  company: string;
  exchange: string;
  recommendation: string;
  analysedAt: string;
};

const STORAGE_KEY = "dsp.recentAnalyses.v1";
const MAX_ENTRIES = 12;

/** In-memory mirror for SSR / test environments without sessionStorage. */
let memoryStore: RecentAnalysisEntry[] = [];

export function loadRecentAnalyses(): RecentAnalysisEntry[] {
  if (typeof window === "undefined") return [...memoryStore];
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [...memoryStore];
    const parsed = JSON.parse(raw) as RecentAnalysisEntry[];
    memoryStore = Array.isArray(parsed) ? parsed : [];
    return [...memoryStore];
  } catch {
    return [...memoryStore];
  }
}

export function pushRecentAnalysis(
  entry: RecentAnalysisEntry,
): RecentAnalysisEntry[] {
  const next = [
    entry,
    ...loadRecentAnalyses().filter(
      (item) => item.ticker.toUpperCase() !== entry.ticker.toUpperCase(),
    ),
  ].slice(0, MAX_ENTRIES);
  memoryStore = next;
  if (typeof window !== "undefined") {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* ignore quota */
    }
  }
  return [...next];
}

export function clearRecentAnalyses(): void {
  memoryStore = [];
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
