/**
 * Figma `ResearchHub.tsx` view-model.
 *
 * Saved Research = real `/api/v1/analyse` sessions from this browser
 * session (archive + recent list). Research Templates are navigation
 * presets into the Company Analysis workspace — copy only, no results.
 * The Figma prototype's TCS/INFY/HDFC rows are not reproduced.
 */

import type { RecentAnalysisEntry } from "@/lib/analysis/recentAnalyses";
import type { SavedResearchItem } from "@/lib/api/workspaceTypes";
import type { ArchivedResearchSession } from "@/lib/copilot/sessionArchive";
import { mapAnalyseResponse } from "@/lib/intelligence/mapResponse";
import {
  libraryFromArchive,
  libraryFromRecent,
  mergeLibraryItems,
  type ResearchLibraryItem,
} from "@/lib/research-workspace/library";

export type SavedResearchRow = {
  id: string;
  symbol: string;
  title: string;
  /** Engine-published context tags (recommendation / committee) — not prose. */
  tags: string[];
  analysedAt: string | null;
  exchange: string | null;
  /** Figma footer: "{turns} conversation turns" — server-recorded, else null. */
  turns: number | null;
  /** `server` = GET /workspace/research/saved · `session` = this browser's analyse history. */
  origin: "server" | "session";
};

/** Server-saved research (per account) → Figma saved-research cards. */
export function mapServerSavedResearch(items: readonly SavedResearchItem[]): SavedResearchRow[] {
  return items.map((item) => ({
    id: `saved:${item.saved_id}`,
    symbol: item.symbol.toUpperCase(),
    title: item.title,
    tags: [...item.tags],
    analysedAt: item.updated_at || item.created_at || null,
    exchange: null,
    turns: typeof item.turns === "number" ? item.turns : null,
    origin: "server",
  }));
}

/** Server rows first; session rows only for symbols not already saved server-side. */
export function mergeSavedResearch(
  server: readonly SavedResearchRow[],
  session: readonly SavedResearchRow[],
): SavedResearchRow[] {
  const covered = new Set(server.map((r) => r.symbol));
  return [...server, ...session.filter((r) => !covered.has(r.symbol))].sort((a, b) =>
    (b.analysedAt ?? "").localeCompare(a.analysedAt ?? ""),
  );
}

export type ResearchTemplate = {
  id: string;
  title: string;
  description: string;
  /** Analysis workspace sections the template walks through (labels). */
  sections: string[];
};

/** Figma TEMPLATES, re-expressed as walks through the real workspace sections. */
export const RESEARCH_TEMPLATES: readonly ResearchTemplate[] = [
  {
    id: "full",
    title: "Full Financial Analysis",
    description: "Summary → Financials → Earnings Quality → Valuation → Margin of Safety",
    sections: ["Summary", "Financials", "Earnings Quality", "Valuation", "Margin of Safety"],
  },
  {
    id: "quality",
    title: "Quick Quality Check",
    description: "Business Quality → Moat → Management → Strengths & Weaknesses",
    sections: ["Business Quality", "Moat", "Management", "Strengths & Weaknesses"],
  },
  {
    id: "valuation",
    title: "Valuation Assessment",
    description: "Valuation → Valuation Transparency → Margin of Safety → Investment Context",
    sections: ["Valuation", "Valuation Transparency", "Margin of Safety", "Investment Context"],
  },
  {
    id: "risk",
    title: "Risk Profile",
    description: "Risk → Ownership → Evidence → Explainability",
    sections: ["Risk", "Ownership", "Evidence", "Explainability"],
  },
  {
    id: "peers",
    title: "Peer Comparison",
    description: "Peers → Compare workspace",
    sections: ["Peers", "Compare"],
  },
];

function sessionTags(session: ArchivedResearchSession | undefined): string[] {
  if (!session) return [];
  const view = mapAnalyseResponse(session.response);
  const tags: string[] = [];
  if (view.recommendation && view.recommendation !== "—") tags.push(view.recommendation);
  if (view.businessQualityLabel && view.businessQualityLabel !== "—") {
    tags.push(`Quality: ${view.businessQualityLabel}`);
  }
  if (view.committeeDecision && view.committeeDecision !== "—") {
    tags.push(`Committee: ${view.committeeDecision}`);
  }
  return tags;
}

export function buildSavedResearch(
  sessions: readonly ArchivedResearchSession[],
  recent: readonly RecentAnalysisEntry[],
): SavedResearchRow[] {
  const items: ResearchLibraryItem[] = mergeLibraryItems([
    ...libraryFromArchive([...sessions]),
    ...libraryFromRecent([...recent]),
  ]);
  const seen = new Set<string>();
  const rows: SavedResearchRow[] = [];
  for (const item of items) {
    if (seen.has(item.ticker)) continue;
    seen.add(item.ticker);
    const session = sessions.find((s) => s.ticker.toUpperCase() === item.ticker);
    const tags = sessionTags(session);
    if (!tags.length && item.recommendation && item.recommendation !== "—") {
      tags.push(item.recommendation);
    }
    rows.push({
      id: item.id,
      symbol: item.ticker,
      title: `${item.company || item.ticker} — Company Analysis`,
      tags,
      analysedAt: item.analysedAt,
      exchange: item.exchange ?? session?.exchange ?? null,
      turns: null,
      origin: "session",
    });
  }
  return rows.sort((a, b) => (b.analysedAt ?? "").localeCompare(a.analysedAt ?? ""));
}

export function filterSavedResearch(rows: readonly SavedResearchRow[], search: string): SavedResearchRow[] {
  const q = search.trim().toLowerCase();
  if (!q) return [...rows];
  return rows.filter(
    (r) => r.title.toLowerCase().includes(q) || r.symbol.toLowerCase().includes(q),
  );
}

/** Normalise the "Start new research" input into a ticker for /analysis. */
export function normaliseResearchSymbol(input: string): string | null {
  const s = input.trim().toUpperCase();
  if (!s) return null;
  if (!/^[A-Z0-9.&_-]{1,20}$/.test(s)) return null;
  return s;
}

export function analysisHref(symbol: string, exchange?: string | null): string {
  const params = new URLSearchParams({ symbol });
  if (exchange) params.set("exchange", exchange);
  return `/analysis?${params.toString()}`;
}
