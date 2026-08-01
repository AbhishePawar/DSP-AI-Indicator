/** P2.2 — Institutional Explainability Framework (presentation). */

export type {
  InstitutionalExplainabilityFramework,
  ModuleExplainability,
  TraceableMetric,
} from "./types";
export {
  EXPLAINABILITY_FRAMEWORK_VERSION,
  mapInstitutionalExplainability,
  mapModuleExplainability,
  oneLineSummaryFromModule,
  truncateWords,
} from "./mapExplainability";
