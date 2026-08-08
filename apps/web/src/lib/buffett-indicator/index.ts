/** ARCH-001 — Buffett Indicator report (presentation synthesis). */

export type {
  BuffettAction,
  BuffettMatrixItem,
  BuffettMatrixState,
  BuffettRecommendationBlock,
  BuffettReportView,
  BuffettScorecardRow,
  BuffettSubsection,
} from "./types";
export {
  buffettActionFromExistingDecision,
  letterGradeFromExistingScore,
  mapBuffettReport,
} from "./mapBuffettReport";
