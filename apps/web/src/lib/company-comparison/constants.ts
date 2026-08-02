/** EPIC-012/013 — honest display constants (CV-001). */

export const DATA_UNAVAILABLE = "Data unavailable.";
export const UNABLE_TO_CALCULATE = "Unable to calculate.";
export const COVERAGE_UNAVAILABLE = "Coverage unavailable.";
export const ANALYSIS_PENDING = "Analysis pending.";
export const ANALYSIS_UNAVAILABLE = "Analysis unavailable.";

/** Mandatory Buffett framing — never imply personal Buffett endorsement. */
export const BUFFETT_FRAMEWORK_PREFIX =
  "According to the Buffett-inspired framework implemented by DSP AI Indicator";

export const BUFFETT_DISCLAIMER =
  `${BUFFETT_FRAMEWORK_PREFIX}, this preference alignment is a presentation remapping of existing /api/v1/analyse research outputs. It does not recalculate fundamentals, does not constitute investment advice, and never asserts a personal Buffett endorsement or buy recommendation.`;

export const WORKSPACE_DISCLAIMER =
  "Institutional Company Comparison is an Investment Decision Workspace. It assists decision-making by presenting side-by-side research outputs — it never makes investment decisions for users. Thin client: no client-side valuation, recommendation, or scoring engines.";

export const MIN_COMPANIES = 2;
export const MAX_COMPANIES = 5;
