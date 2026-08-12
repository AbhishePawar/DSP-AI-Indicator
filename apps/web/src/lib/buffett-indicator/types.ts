/**
 * ARCH-001 — Buffett Indicator report types.
 * Presentation synthesis only — no engines, no pipeline, no new scores.
 */

export type BuffettMatrixState = "met" | "not_met" | "unavailable";

export type BuffettAction = "BUY" | "WATCH" | "HOLD" | "AVOID" | "Unavailable";

export type BuffettSubsection = {
  title: string;
  bullets: string[];
  verdict: string;
  evidenceSources: string[];
};

export type BuffettMatrixItem = {
  criterion: string;
  state: BuffettMatrixState;
  evidence: string;
};

export type BuffettScorecardRow = {
  dimension: string;
  grade: string;
  evidence: string;
};

export type BuffettRecommendationBlock = {
  businessQuality: string;
  investmentQuality: string;
  currentValuation: string;
  marginOfSafety: string;
  action: BuffettAction;
  actionEvidence: string;
};

export type BuffettReportView = {
  /** Presentation-only synthesis from mapped ResearchView / stage summaries. */
  kind: "buffett_indicator_report";
  circleOfCompetence: BuffettSubsection;
  economicMoat: BuffettSubsection;
  managementQuality: BuffettSubsection;
  financialFortress: BuffettSubsection;
  earningsPredictability: BuffettSubsection;
  capitalAllocation: BuffettSubsection;
  intrinsicValue: BuffettSubsection & {
    currentPrice: string;
    intrinsicValue: string;
    marginOfSafety: string;
  };
  longTermRisks: BuffettSubsection;
  decisionMatrix: BuffettMatrixItem[];
  scorecard: BuffettScorecardRow[];
  overallRating: string;
  verdict: string;
  recommendation: BuffettRecommendationBlock;
  keyStrengths: string[];
  keyWeaknesses: string[];
  confidence: string;
  disclaimer: string;
};
