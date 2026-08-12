/** P2.1 — Institutional Report Transparency (presentation). */

export type {
  DataFreshnessLabel,
  QualityBadge,
  ReportTransparencyView,
} from "./types";
export { buildReportId, fnv1aHex } from "./reportId";
export {
  BUFFETT_FRAMEWORK_VERSION,
  INSTITUTIONAL_RATING_FRAMEWORK_VERSION,
  mapDataFreshness,
  mapReportTransparency,
} from "./mapReportTransparency";
