/**
 * Honest session-derived facts for Portfolio Intelligence.
 * Count aggregations only — never invents market values, returns, or scores.
 */

import type { PortfolioHolding } from "@/lib/portfolio/model";

export type CountSegment = {
  name: string;
  count: number;
  /** Share of holdings count (not market weight). */
  shareOfHoldings: string;
};

function segmentsFromCounts(counts: Map<string, number>, total: number): CountSegment[] {
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([name, count]) => ({
      name,
      count,
      shareOfHoldings:
        total > 0 ? `${((count / total) * 100).toFixed(1)}% of holdings` : "Data unavailable.",
    }));
}

/** Observed sector labels on session holdings — count-based only. */
export function sectorHoldingCounts(holdings: PortfolioHolding[]): CountSegment[] {
  const counts = new Map<string, number>();
  for (const h of holdings) {
    const key = h.sector?.trim() || "Unknown";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return segmentsFromCounts(counts, holdings.length);
}

/**
 * Session allocationPercent when present on holdings.
 * Labeled as session metadata — not certified market weights.
 */
export function sessionAllocationBySector(holdings: PortfolioHolding[]): {
  segments: { name: string; percentLabel: string }[];
  note: string;
} {
  const hasAny = holdings.some(
    (h) => typeof h.allocationPercent === "number" && Number.isFinite(h.allocationPercent),
  );
  if (!hasAny || holdings.length === 0) {
    return {
      segments: [],
      note: "Data unavailable. No session allocationPercent values on holdings.",
    };
  }
  const sums = new Map<string, number>();
  for (const h of holdings) {
    const key = h.sector?.trim() || "Unknown";
    const w =
      typeof h.allocationPercent === "number" && Number.isFinite(h.allocationPercent)
        ? h.allocationPercent
        : 0;
    sums.set(key, (sums.get(key) ?? 0) + w);
  }
  const segments = [...sums.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([name, pct]) => ({
      name,
      percentLabel: `${pct.toFixed(1)}% (session)`,
    }));
  return {
    segments,
    note: "Session allocationPercent summed by sector — not market-value weights from a portfolio engine.",
  };
}

export function researchCoverageFacts(holdings: PortfolioHolding[]) {
  const covered = holdings.filter((h) => h.researchAvailable).length;
  const pending = holdings.length - covered;
  return { covered, pending, total: holdings.length };
}

export function attentionItems(holdings: PortfolioHolding[]): string[] {
  const items: string[] = [];
  const pending = holdings.filter((h) => !h.researchAvailable);
  if (pending.length) {
    items.push(
      `${pending.length} holding(s) pending research coverage: ${pending
        .slice(0, 5)
        .map((h) => h.ticker)
        .join(", ")}${pending.length > 5 ? "…" : ""}`,
    );
  }
  const unknownSector = holdings.filter(
    (h) => !h.sector || h.sector === "Unknown",
  );
  if (unknownSector.length) {
    items.push(`${unknownSector.length} holding(s) missing sector classification.`);
  }
  return items;
}
