/**
 * EPIC-014 — Research Timeline composer.
 * Consumes local history + optional RI / comparison / notebook events.
 * Never fabricates confidence or recommendation evolution.
 */

import { loadRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import { listRecentReports } from "@/lib/recentReports";
import type { NotebookEntry } from "./notebookStore";
import type { SavedResearchSession } from "./notebookStore";

export type TimelineEventKind =
  | "analysis"
  | "report"
  | "notebook"
  | "comparison"
  | "session"
  | "ri"
  | "committee"
  | "evidence"
  | "unavailable";

export type TimelineEvent = {
  id: string;
  kind: TimelineEventKind;
  at: string;
  title: string;
  detail: string;
  href?: string;
  symbol?: string | null;
};

export type TimelineInput = {
  symbol?: string | null;
  notebookEntries?: NotebookEntry[];
  savedSessions?: SavedResearchSession[];
  comparisonEvents?: {
    id: string;
    at: string;
    title: string;
    symbols: string[];
    href: string;
  }[];
  /** Optional RI timeline rows already mapped by caller (pass-through). */
  riEvents?: TimelineEvent[];
};

export function composeResearchTimeline(input: TimelineInput): TimelineEvent[] {
  const sym = input.symbol?.toUpperCase() ?? null;
  const events: TimelineEvent[] = [];

  for (const a of loadRecentAnalyses()) {
    if (sym && a.ticker.toUpperCase() !== sym) continue;
    events.push({
      id: `analysis-${a.ticker}-${a.analysedAt}`,
      kind: "analysis",
      at: a.analysedAt,
      title: `Analysis · ${a.ticker}`,
      detail: a.recommendation || "Data unavailable.",
      href: `/analysis?symbol=${encodeURIComponent(a.ticker)}`,
      symbol: a.ticker,
    });
  }

  for (const r of listRecentReports()) {
    if (sym && (r.symbol ?? "").toUpperCase() !== sym) continue;
    events.push({
      id: `report-${r.reportId}`,
      kind: "report",
      at: r.savedAt ?? new Date(0).toISOString(),
      title: `Report · ${r.reportId}`,
      detail: r.symbol ? `Symbol ${r.symbol}` : "Data unavailable.",
      href: r.symbol
        ? `/research/institutional?symbol=${encodeURIComponent(r.symbol)}`
        : "/research/institutional",
      symbol: r.symbol ?? null,
    });
  }

  for (const e of input.notebookEntries ?? []) {
    if (sym && e.symbol && e.symbol !== sym) continue;
    if (sym && !e.symbol) {
      /* keep global notes visible when filtering — optional */
    }
    events.push({
      id: `nb-${e.id}`,
      kind: "notebook",
      at: e.at,
      title: `Notebook · ${e.kind}`,
      detail: e.text.slice(0, 120),
      href: e.symbol
        ? `/research/canvas?symbol=${encodeURIComponent(e.symbol)}&tab=notes`
        : "/research/canvas?tab=notes",
      symbol: e.symbol,
    });
  }

  for (const s of input.savedSessions ?? []) {
    if (sym && s.symbol && s.symbol !== sym) continue;
    events.push({
      id: `ss-${s.id}`,
      kind: "session",
      at: s.at,
      title: `Saved session · ${s.title}`,
      detail: s.symbol ? `Symbol ${s.symbol}` : "No symbol",
      href: s.symbol
        ? `/research/canvas?symbol=${encodeURIComponent(s.symbol)}&tab=${s.tab}`
        : `/research/canvas?tab=${s.tab}`,
      symbol: s.symbol,
    });
  }

  for (const c of input.comparisonEvents ?? []) {
    if (sym && !c.symbols.map((x) => x.toUpperCase()).includes(sym)) continue;
    events.push({
      id: `cmp-${c.id}`,
      kind: "comparison",
      at: c.at,
      title: c.title,
      detail: c.symbols.join(", "),
      href: c.href,
      symbol: sym,
    });
  }

  for (const ri of input.riEvents ?? []) {
    if (sym && ri.symbol && ri.symbol.toUpperCase() !== sym) continue;
    events.push(ri);
  }

  if (events.length === 0) {
    events.push({
      id: "unavailable",
      kind: "unavailable",
      at: new Date(0).toISOString(),
      title: "Research Timeline",
      detail:
        "Data unavailable. Open Company Analysis, Research Intelligence, or add notebook entries to populate history. Recommendation / confidence evolution requires authenticated feeds.",
    });
  }

  return events.sort(
    (a, b) => new Date(b.at).getTime() - new Date(a.at).getTime(),
  );
}
