/**
 * Client directory — pure filter/sort (memo-friendly, no persistence).
 */

import type {
  ClientDirectoryFilters,
  ClientDirectorySort,
  ClientSummary,
  PortfolioSizeBand,
  ReviewStatus,
  RiskBand,
} from "./advisorTypes";

const SIZE_ORDER: Record<PortfolioSizeBand, number> = {
  small: 1,
  medium: 2,
  large: 3,
  institutional: 4,
};

const REVIEW_ORDER: Record<ReviewStatus, number> = {
  overdue: 0,
  due_soon: 1,
  on_track: 2,
  completed: 3,
};

const RISK_ORDER: Record<RiskBand, number> = {
  conservative: 0,
  moderate: 1,
  growth: 2,
  aggressive: 3,
};

export const DEFAULT_CLIENT_FILTERS: ClientDirectoryFilters = {
  query: "",
  riskProfile: "all",
  reviewStatus: "all",
  portfolioSize: "all",
  sort: "alias_asc",
};

export function filterAndSortClients(
  clients: ClientSummary[],
  filters: ClientDirectoryFilters,
): ClientSummary[] {
  const q = filters.query.trim().toLowerCase();
  let list = clients.filter((c) => {
    if (filters.riskProfile !== "all" && c.riskProfile !== filters.riskProfile) return false;
    if (filters.reviewStatus !== "all" && c.reviewStatus !== filters.reviewStatus) return false;
    if (filters.portfolioSize !== "all" && c.portfolioSizeBand !== filters.portfolioSize)
      return false;
    if (!q) return true;
    return (
      c.alias.toLowerCase().includes(q) ||
      c.segment.toLowerCase().includes(q) ||
      c.portfolioSnapshotLabel.toLowerCase().includes(q)
    );
  });

  list = [...list].sort((a, b) => compareClients(a, b, filters.sort));
  return list;
}

function compareClients(
  a: ClientSummary,
  b: ClientSummary,
  sort: ClientDirectorySort,
): number {
  switch (sort) {
    case "alias_desc":
      return b.alias.localeCompare(a.alias);
    case "activity":
      return b.lastTouchAt.localeCompare(a.lastTouchAt);
    case "meeting_due": {
      const am = a.meetingDueAt ?? "9999";
      const bm = b.meetingDueAt ?? "9999";
      return am.localeCompare(bm);
    }
    case "risk":
      return RISK_ORDER[a.riskProfile] - RISK_ORDER[b.riskProfile];
    case "portfolio_size":
      return SIZE_ORDER[a.portfolioSizeBand] - SIZE_ORDER[b.portfolioSizeBand];
    case "review_status":
      return REVIEW_ORDER[a.reviewStatus] - REVIEW_ORDER[b.reviewStatus];
    case "alias_asc":
    default:
      return a.alias.localeCompare(b.alias);
  }
}
