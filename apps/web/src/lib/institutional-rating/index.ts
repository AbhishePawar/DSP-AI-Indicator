/** ARCH-002 — Unified Institutional Rating Framework (presentation). */

export type {
  InstitutionalGrade,
  InstitutionalRatingFramework,
  InvestmentAction,
  ModuleRating,
  OverallInvestmentRating,
  RatingDimension,
  ScorecardRow,
} from "./types";
export {
  averageGradeFromExisting,
  averageScoreOutOf10,
  confidenceDisplay,
  isUnavailableDisplay,
  letterGradeFromExistingScore,
  parseExistingScoreTo100,
  scoreOutOf10FromExisting,
  starsFromGrade,
} from "./scale";
export {
  investmentActionFromExisting,
  mapInstitutionalRatings,
} from "./mapInstitutionalRatings";
