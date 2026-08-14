/**
 * EPIC-F007 — Re-export F005 research export helpers + library row helpers.
 */

import type { RecentAnalysisEntry } from "@/lib/analysis/recentAnalyses";
import type { ArchivedResearchSession } from "@/lib/copilot/sessionArchive";
import type { RecentReportEntry } from "@/lib/recentReports";

export {
  downloadText,
  researchViewToCsv,
  researchViewToHtml,
  researchViewToJson,
} from "@/lib/company-analysis/exportView";

export type ResearchLibraryItem = {
  id: string;
  ticker: string;
  company: string;
  exchange?: string;
  analysedAt: string | null;
  source: "recent" | "archive" | "report" | "favourite" | "pinned";
  recommendation?: string;
  reportId?: string;
};

export function libraryFromRecent(
  entries: RecentAnalysisEntry[],
): ResearchLibraryItem[] {
  return entries.map((e) => ({
    id: `recent-${e.ticker}-${e.analysedAt}`,
    ticker: e.ticker.toUpperCase(),
    company: e.company,
    exchange: e.exchange,
    analysedAt: e.analysedAt,
    source: "recent" as const,
    recommendation: e.recommendation,
  }));
}

export function libraryFromArchive(
  sessions: ArchivedResearchSession[],
): ResearchLibraryItem[] {
  return sessions.map((s) => ({
    id: `archive-${s.ticker}-${s.analysedAt}`,
    ticker: s.ticker.toUpperCase(),
    company: s.company || s.ticker,
    exchange: s.exchange || undefined,
    analysedAt: s.analysedAt,
    source: "archive" as const,
  }));
}

export function libraryFromReports(
  reports: RecentReportEntry[],
): ResearchLibraryItem[] {
  return reports.map((r) => ({
    id: `report-${r.reportId}`,
    ticker: (r.symbol || "UNKNOWN").toUpperCase(),
    company: r.symbol || r.reportId,
    analysedAt: r.savedAt,
    source: "report" as const,
    reportId: r.reportId,
  }));
}

export function mergeLibraryItems(
  items: ResearchLibraryItem[],
): ResearchLibraryItem[] {
  const seen = new Set<string>();
  const out: ResearchLibraryItem[] = [];
  for (const item of items) {
    const key = `${item.source}:${item.ticker}:${item.reportId ?? item.analysedAt ?? ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}
