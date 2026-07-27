/**
 * Sprint 3 — Advisor Research domain (presentation bookmarks over demo research envelopes).
 * Does not call or mutate Decision / Research / KG / Copilot / Portfolio engines.
 */

export type ResearchCompanyId = string;
export type ResearchItemId = string;
export type AdvisorCollectionId = string;
export type ResearchNoteId = string;
export type ResearchTimelineId = string;
export type BookmarkId = string;

export type ResearchCollectionTheme =
  | "growth"
  | "value"
  | "dividend"
  | "small_cap"
  | "large_cap"
  | "high_quality"
  | "custom";

export type CollectionLifecycle = "active" | "archived";

export type ResearchNoteKind =
  | "pinned"
  | "private"
  | "client"
  | "meeting"
  | "finding";

export type TimelineKind =
  | "analysis_created"
  | "research_updated"
  | "report_generated"
  | "collection_modified"
  | "favorite";

export type BookmarkKind = "favorite" | "recent" | "pinned" | "collection" | "tag";

/** Demo envelope — mirrors trust fields without touching live research outputs. */
export type DemoResearchEnvelope = {
  id: ResearchItemId;
  companyId: ResearchCompanyId;
  companyLabel: string;
  thesis: string;
  topRisks: string[];
  keyOpportunities: string[];
  valuationSummary: string;
  confidence: string;
  methodology: string;
  evidence: string[];
  limitations: string[];
  businessQuality: string;
  financialStrength: string;
  valuation: string;
  growth: string;
  risk: string;
  management: string;
  moat: string;
  evidenceCoverage: string;
  viewedAt: string;
};

export type AdvisorResearchCollection = {
  id: AdvisorCollectionId;
  name: string;
  theme: ResearchCollectionTheme;
  itemIds: ResearchItemId[];
  lifecycle: CollectionLifecycle;
  updatedAt: string;
};

export type AdvisorResearchNote = {
  id: ResearchNoteId;
  kind: ResearchNoteKind;
  title: string;
  body: string;
  companyId: ResearchCompanyId | null;
  pinned: boolean;
  updatedAt: string;
};

export type AdvisorResearchTimelineEvent = {
  id: ResearchTimelineId;
  kind: TimelineKind;
  label: string;
  occurredAt: string;
};

export type AdvisorResearchBookmark = {
  id: BookmarkId;
  kind: BookmarkKind;
  label: string;
  target: string;
  tags: string[];
};

export type CompareDimension =
  | "businessQuality"
  | "financialStrength"
  | "valuation"
  | "growth"
  | "risk"
  | "management"
  | "moat"
  | "confidence"
  | "evidenceCoverage";

export const COMPARE_DIMENSIONS: { id: CompareDimension; label: string }[] = [
  { id: "businessQuality", label: "Business Quality" },
  { id: "financialStrength", label: "Financial Strength" },
  { id: "valuation", label: "Valuation" },
  { id: "growth", label: "Growth" },
  { id: "risk", label: "Risk" },
  { id: "management", label: "Management" },
  { id: "moat", label: "Moat" },
  { id: "confidence", label: "Confidence" },
  { id: "evidenceCoverage", label: "Evidence Coverage" },
];
