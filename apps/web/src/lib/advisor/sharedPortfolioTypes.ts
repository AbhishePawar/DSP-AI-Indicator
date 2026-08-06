/**
 * Sprint 7.3 — Shared Portfolio Collaboration types (presentation / session only).
 */

import type { MpRiskLevel } from "./modelPortfolioTypes";

export type SharedPortfolioFilterState = {
  query: string;
  riskLevel: MpRiskLevel | "";
  strategy: string;
  sector: string;
  marketCap: "small" | "mid" | "large" | "";
  allocationBand: "" | "equity_heavy" | "balanced" | "cash_heavy";
  watchlistOnly: boolean;
  pinnedOnly: boolean;
  favoritesOnly: boolean;
  recentlyViewedOnly: boolean;
};

export type SharedPortfolioActivityKind =
  | "viewed"
  | "compared"
  | "presented"
  | "reviewed"
  | "updated"
  | "pinned"
  | "favorited"
  | "discussion";

export type SharedPortfolioActivityItem = {
  id: string;
  kind: SharedPortfolioActivityKind;
  label: string;
  at: string;
  portfolioId?: string;
};

export type SharedPortfolioCollection = {
  id: string;
  name: string;
  portfolioIds: string[];
  updatedAt: string;
};

export type PortfolioDiscussionDraft = {
  portfolioId: string;
  portfolioNotes: string;
  reviewNotes: string;
  investmentThesis: string;
  concerns: string;
  followUps: string;
  updatedAt: string;
};

export type PortfolioScenarioId =
  | "conservative"
  | "base"
  | "bull"
  | "bear"
  | "stress";

export type PortfolioScenarioView = {
  id: PortfolioScenarioId;
  label: string;
  framing: string;
  riskCue: string;
  allocationCue: string;
  note: string;
};

export const DEFAULT_SHARED_PORTFOLIO_FILTERS: SharedPortfolioFilterState = {
  query: "",
  riskLevel: "",
  strategy: "",
  sector: "",
  marketCap: "",
  allocationBand: "",
  watchlistOnly: false,
  pinnedOnly: false,
  favoritesOnly: false,
  recentlyViewedOnly: false,
};

export const SHARED_PORTFOLIO_NAV: ReadonlyArray<{
  href: string;
  label: string;
  exact?: boolean;
}> = [
  { href: "/advisor/team/shared-portfolios", label: "Overview", exact: true },
  { href: "/advisor/team/shared-portfolios/library", label: "Library" },
  { href: "/advisor/team/shared-portfolios/compare", label: "Compare" },
  { href: "/advisor/team/shared-portfolios/scenarios", label: "Scenarios" },
  { href: "/advisor/team/shared-portfolios/discussion", label: "Discussion" },
  { href: "/advisor/team/shared-portfolios/activity", label: "Activity" },
];
