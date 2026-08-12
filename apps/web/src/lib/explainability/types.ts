/**
 * P2.2 — Institutional Explainability Framework (presentation).
 * Expandable explainability over existing ModuleRating fields only.
 */

export type TraceableMetric = {
  label: string;
  value: string;
  /** Existing source attribution — never a derived formula. */
  sourceField: string;
};

export type ModuleExplainability = {
  moduleId: string;
  title: string;
  scoreOutOf10: string;
  grade: string;
  confidence: string;
  oneLineSummary: string;
  evidence: TraceableMetric[];
  strengths: string[];
  weaknesses: string[];
  /** Deterministic explanation ≤ 120 words from existing outputs. */
  explanation: string;
  traceability: TraceableMetric[];
};

export type InstitutionalExplainabilityFramework = {
  kind: "institutional_explainability_framework";
  version: string;
  disclaimer: string;
  modules: ModuleExplainability[];
};
