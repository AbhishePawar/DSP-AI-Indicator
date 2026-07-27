/** Process-local recent report ids — not a business store. */

const KEY = "dsp.recentReports.v1";
const MAX = 8;

export type RecentReportEntry = {
  reportId: string;
  symbol?: string;
  savedAt: string;
};

export function listRecentReports(): RecentReportEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as RecentReportEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function pushRecentReport(entry: RecentReportEntry): void {
  if (typeof window === "undefined") return;
  const next = [
    entry,
    ...listRecentReports().filter((r) => r.reportId !== entry.reportId),
  ].slice(0, MAX);
  window.localStorage.setItem(KEY, JSON.stringify(next));
}
