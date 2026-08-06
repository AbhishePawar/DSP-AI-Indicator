/**
 * EPIC-012/013 — Comparison workspace types + future comparison-engine abstraction.
 *
 * Presentation aggregation only. Ranking uses server-provided scores/fields.
 * Designed so portfolio / ETF / MF / sector / industry / watchlist subjects
 * can later plug in without redesigning the workspace shell.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";

export type HonestUnavailable =
  | "Data unavailable."
  | "Unable to calculate."
  | "Coverage unavailable."
  | "Analysis pending."
  | "Analysis unavailable."
  | "Unavailable";

/** Future-proof subject kinds for the comparison engine. */
export type ComparisonSubjectKind =
  | "company"
  | "portfolio"
  | "etf"
  | "mutual_fund"
  | "sector"
  | "industry"
  | "watchlist";

export type ComparisonSubjectRef = {
  kind: ComparisonSubjectKind;
  id: string;
  symbol?: string;
  label: string;
  exchange?: string;
};

export type ComparisonSlotStatus =
  | "idle"
  | "loading"
  | "ready"
  | "error"
  | "unavailable";

export type ComparisonCompanySlot = {
  symbol: string;
  company: string;
  exchange: string;
  pinned: boolean;
  status: ComparisonSlotStatus;
  analysedAt: string | null;
  correlationId: string | null;
  error: string | null;
  /** Mapped research view when analyse succeeded. */
  view: ResearchView | null;
  /** Research Intelligence overlays (measurement only). */
  intelligence: CompanyIntelligenceOverlay | null;
};

export type CompanyIntelligenceOverlay = {
  symbol: string;
  overallAccuracy: string;
  recommendationAccuracy: string;
  calibrationStatus: string;
  timelineCount: string;
  freshness: string;
  coverage: string;
  source: "research_intelligence" | "unavailable";
};

export type Medal = "gold" | "silver" | "bronze" | null;

export type WinnerMatrixDimensionId =
  | "businessQuality"
  | "management"
  | "moat"
  | "risk"
  | "valuation"
  | "capitalAllocation"
  | "cashFlow"
  | "roce"
  | "margins"
  | "growth"
  | "financialStrength"
  | "confidence"
  | "overall";

export type WinnerMatrixCell = {
  symbol: string;
  display: string;
  numeric: number | null;
  medal: Medal;
  evidence: string;
};

export type WinnerMatrixRow = {
  id: WinnerMatrixDimensionId;
  label: string;
  cells: WinnerMatrixCell[];
  /** Symbol with gold medal, or unavailable. */
  leader: string;
};

export type TradeOffItem = {
  dimension: string;
  summary: string;
  stronger: string;
  weaker: string;
  evidence: string[];
};

export type BuffettPreferenceDimensionId =
  | "understandability"
  | "moat"
  | "management"
  | "capitalAllocation"
  | "roce"
  | "debt"
  | "cash"
  | "reinvestment"
  | "marginOfSafety"
  | "durability";

export type BuffettAlignment = "aligned" | "partial" | "not_aligned" | "unavailable";

export type BuffettPreferenceCell = {
  symbol: string;
  alignment: BuffettAlignment;
  reason: string;
  evidence: string;
  confidence: string;
};

export type BuffettPreferenceRow = {
  id: BuffettPreferenceDimensionId;
  label: string;
  framing: string;
  cells: BuffettPreferenceCell[];
  tradeOff: string;
};

export type EvidenceQualityCell = {
  symbol: string;
  evidenceCount: string;
  confidence: string;
  coverage: string;
  freshness: string;
  sources: string[];
  status: string;
};

export type ExplainabilityCompareCell = {
  symbol: string;
  moduleSummaries: { title: string; summary: string; confidence: string }[];
  overallExplanation: string;
};

export type ValuationCompareCell = {
  symbol: string;
  intrinsicValue: string;
  price: string;
  marginOfSafety: string;
  dcf: string;
  relative: string;
  residualIncome: string;
  epv: string;
  overall: string;
  confidence: string;
  historical: string;
};

export type ScenarioCompareCell = {
  symbol: string;
  bull: string;
  base: string;
  bear: string;
};

export type PortfolioFitCell = {
  symbol: string;
  quality: string;
  value: string;
  growth: string;
  income: string;
  buffettFramework: string;
  note: string;
};

export type HeatmapCell = {
  symbol: string;
  dimension: string;
  intensity: "high" | "medium" | "low" | "unavailable";
  display: string;
};

export type ExecutiveSummaryView = {
  overall: string;
  institutionalSummary: string;
  winnerSummary: string;
  tradeOffs: string[];
  confidence: string;
  coverage: string;
  evidenceQuality: string;
};

/** EPIC-012/013A — Executive Comparison Scorecard row. */
export type ExecutiveScorecardRowId =
  | "overall"
  | "businessQuality"
  | "management"
  | "moat"
  | "risk"
  | "valuation"
  | "financial"
  | "researchConfidence"
  | "evidenceStrength"
  | "overallPosition";

export type ExecutiveScorecardCell = {
  symbol: string;
  display: string;
  evidence: string;
  /** Presentation emphasis from weighting profile — does not alter scores. */
  emphasis: "highlight" | "normal" | "deemphasize";
};

export type ExecutiveScorecardRow = {
  id: ExecutiveScorecardRowId;
  label: string;
  emphasis: "highlight" | "normal" | "deemphasize";
  cells: ExecutiveScorecardCell[];
};

export type EvidenceStrengthLevel =
  | "Strong"
  | "Moderate"
  | "Limited"
  | "Data unavailable.";

export type EvidenceStrengthMeter = {
  symbol: string;
  level: EvidenceStrengthLevel;
  coverage: string;
  freshness: string;
  completeness: string;
  sourceQuality: string;
  researchConfidence: string;
  rationale: string;
};

export type ContradictoryEvidenceCell = {
  symbol: string;
  supporting: string[];
  contradictory: string[];
  coverage: string;
  confidence: string;
  sourceQuality: string;
  honestyNote: string;
};

export type WhyNotReason = {
  dimension: string;
  reason: string;
  evidence: string;
};

export type WhyNotAnalysis = {
  symbol: string;
  reasons: WhyNotReason[];
  note: string;
};

export type CommitteeMemo = {
  title: string;
  companies: string[];
  executiveSummary: string;
  winnerMatrixSummary: string;
  tradeOffs: string[];
  supportingEvidence: string[];
  contradictoryEvidence: string[];
  buffettSummary: string;
  confidence: string;
  outstandingQuestions: string[];
  decisionNotes: string[];
  disclaimer: string;
  generatedAt: string;
  exportNote: string;
};

export type SectorContextCell = {
  symbol: string;
  sector: string;
  industry: string;
  sectorMedian: string;
  industryMedian: string;
  relativePosition: string;
  note: string;
};

export type SensitivityCell = {
  symbol: string;
  coverageInput: string;
  evidenceInput: string;
  confidenceInput: string;
  coverageSensitivity: string;
  evidenceSensitivity: string;
  confidenceSensitivity: string;
  note: string;
};

/** Immutable historical comparison snapshot (append-only store). */
export type ComparisonHistoryEntry = {
  id: string;
  at: string;
  symbols: string[];
  researchVersion: string;
  confidence: string;
  winnerSummary: string;
  changes: string;
  immutable: true;
};

/**
 * Extensible comparison engine contract — v1 implements company subjects only.
 * Future adapters may supply portfolio/ETF/MF/sector packs without UI redesign.
 */
export type ComparisonEngineAdapter = {
  kind: ComparisonSubjectKind;
  /** Resolve subject refs into comparable research packs (server-authored). */
  describe(): string;
};

export type ComparisonWorkspaceModel = {
  kind: "institutional_company_comparison";
  version: "1.1";
  disclaimer: string;
  buffettDisclaimer: string;
  generatedAt: string;
  symbols: string[];
  slots: ComparisonCompanySlot[];
  executive: ExecutiveSummaryView;
  /** EPIC-012/013A institutional scorecard. */
  scorecard: ExecutiveScorecardRow[];
  winnerMatrix: WinnerMatrixRow[];
  tradeOffs: TradeOffItem[];
  valuation: ValuationCompareCell[];
  qualityModules: {
    businessQuality: { symbol: string; score: string; label: string; confidence: string }[];
    management: { symbol: string; score: string; label: string; confidence: string }[];
    moat: { symbol: string; score: string; label: string; confidence: string }[];
    risk: { symbol: string; score: string; label: string; confidence: string }[];
    financial: { symbol: string; score: string; label: string; confidence: string }[];
  };
  evidence: EvidenceQualityCell[];
  evidenceStrength: EvidenceStrengthMeter[];
  contradictoryEvidence: ContradictoryEvidenceCell[];
  whyNot: WhyNotAnalysis[];
  committeeMemo: CommitteeMemo;
  sectorContext: SectorContextCell[];
  sensitivity: SensitivityCell[];
  explainability: ExplainabilityCompareCell[];
  intelligence: CompanyIntelligenceOverlay[];
  buffettPreference: BuffettPreferenceRow[];
  heatmap: HeatmapCell[];
  scenarios: ScenarioCompareCell[];
  portfolioFit: PortfolioFitCell[];
  coverageNotes: string[];
  /** Active weighting profile id (presentation emphasis only). */
  weightingProfileId: string;
  institutionalQuestions: string[];
};

/** Saved comparison snapshot (user-authored metadata + symbol set). */
export type SavedComparison = {
  id: string;
  title: string;
  symbols: string[];
  savedAt: string;
  notes?: string;
};
