/**
 * ARCH-002 — Unified Institutional Rating Framework (presentation).
 * Score/grade/confidence taxonomy only — never recalculates fundamentals.
 */

export type InstitutionalGrade =
  | "A+"
  | "A"
  | "B+"
  | "B"
  | "C"
  | "D"
  | "F"
  | "Unavailable";

export type InvestmentAction =
  | "BUY"
  | "ACCUMULATE"
  | "WATCH"
  | "HOLD"
  | "REDUCE"
  | "AVOID"
  | "Unavailable";

export type RatingDimension = {
  label: string;
  value: string;
  evidence: string;
};

export type ModuleRating = {
  id: string;
  title: string;
  /** Existing score remapped to /10 display, or Unavailable */
  scoreOutOf10: string;
  grade: InstitutionalGrade | string;
  confidence: string;
  evidence: string[];
  strengths: string[];
  weaknesses: string[];
  explanation: string;
  dimensions: RatingDimension[];
  sourceStages: string[];
};

export type ScorecardRow = {
  module: string;
  scoreOutOf10: string;
  grade: string;
  confidence: string;
};

export type OverallInvestmentRating = {
  scoreOutOf10: string;
  grade: string;
  confidence: string;
  stars: number;
  investmentQuality: string;
  businessQuality: string;
  valuationQuality: string;
  riskLevel: string;
  expectedLongTermQuality: string;
  recommendation: InvestmentAction;
  recommendationReasoning: string;
  explanation: string;
};

export type InstitutionalRatingFramework = {
  kind: "institutional_rating_framework";
  disclaimer: string;
  modules: {
    financialStrength: ModuleRating;
    valuation: ModuleRating;
    economicMoat: ModuleRating;
    managementQuality: ModuleRating;
    earningsQuality: ModuleRating;
    financialFortress: ModuleRating;
    capitalAllocation: ModuleRating;
    riskAssessment: ModuleRating;
    aiCommittee: ModuleRating;
    buffettIndicator: ModuleRating;
  };
  scorecard: ScorecardRow[];
  overall: OverallInvestmentRating;
};
