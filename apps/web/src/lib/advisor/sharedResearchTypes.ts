/**
 * Sprint 7.2 — Shared Research Workspace types (presentation / session only).
 */

export type SharedResearchMarketCap = "mega" | "large" | "mid" | "small";

export type SharedResearchFilterState = {
  query: string;
  sector: string;
  industry: string;
  marketCap: SharedResearchMarketCap | "";
  rating: string;
  risk: string;
  valuation: string;
  watchlistOnly: boolean;
  bookmarkedOnly: boolean;
  pinnedOnly: boolean;
  favoritesOnly: boolean;
};

export type SharedResearchActivityKind =
  | "opened"
  | "compared"
  | "presented"
  | "bookmarked"
  | "collection_add"
  | "pinned"
  | "favorited";

export type SharedResearchActivityItem = {
  id: string;
  kind: SharedResearchActivityKind;
  label: string;
  at: string;
  envelopeId?: string;
};

export type SharedCollection = {
  id: string;
  name: string;
  theme: string;
  itemIds: string[];
  lifecycle: "active" | "archived";
  favorite: boolean;
  updatedAt: string;
};

export type EnvelopeFilterMeta = {
  envelopeId: string;
  sector: string;
  industry: string;
  marketCap: SharedResearchMarketCap;
  rating: string;
  watchlist: boolean;
};

export const DEFAULT_SHARED_RESEARCH_FILTERS: SharedResearchFilterState = {
  query: "",
  sector: "",
  industry: "",
  marketCap: "",
  rating: "",
  risk: "",
  valuation: "",
  watchlistOnly: false,
  bookmarkedOnly: false,
  pinnedOnly: false,
  favoritesOnly: false,
};

export const SHARED_RESEARCH_NAV = [
  { href: "/advisor/team/shared-research", label: "Overview", exact: true },
  { href: "/advisor/team/shared-research/library", label: "Library" },
  { href: "/advisor/team/shared-research/collections", label: "Collections" },
  { href: "/advisor/team/shared-research/compare", label: "Compare" },
  { href: "/advisor/team/shared-research/bookmarks", label: "Bookmarks" },
  { href: "/advisor/team/shared-research/activity", label: "Activity" },
] as const;
