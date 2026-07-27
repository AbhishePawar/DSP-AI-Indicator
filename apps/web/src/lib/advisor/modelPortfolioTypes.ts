/**
 * Sprint 4 — Model Portfolio Manager types (presentation only).
 */

export type MpCategory =
  | "growth"
  | "balanced"
  | "income"
  | "value"
  | "quality"
  | "small_cap"
  | "large_cap"
  | "custom";

export type MpRiskLevel = "conservative" | "moderate" | "growth" | "aggressive";

export type MpTemplateId =
  | "tpl-aggressive-growth"
  | "tpl-balanced-growth"
  | "tpl-conservative-income"
  | "tpl-quality-compounders"
  | "tpl-dividend-focus"
  | "tpl-value-opportunities"
  | "tpl-custom";

export type MpHolding = {
  envelopeId: string;
  companyLabel: string;
  allocationPct: number;
  sector: string;
  marketCapBand: "small" | "mid" | "large";
};

export type MpNoteKind = "advisor" | "review" | "suitability" | "version";

export type MpNote = {
  id: string;
  kind: MpNoteKind;
  title: string;
  body: string;
  updatedAt: string;
};

export type ModelPortfolioDraft = {
  id: string;
  name: string;
  category: MpCategory;
  objective: string;
  riskLevel: MpRiskLevel;
  targetHorizon: string;
  cashAllocationPct: number;
  holdings: MpHolding[];
  notes: MpNote[];
  templateId: MpTemplateId | null;
};

export type PortfolioReviewView = {
  strengths: string[];
  potentialRisks: string[];
  diversification: string;
  concentration: string;
  researchCoverage: string;
  evidenceCompleteness: string;
};

export type AllocationTotals = {
  holdingsPct: number;
  cashPct: number;
  totalPct: number;
  isBalanced: boolean;
  deltaFrom100: number;
};
