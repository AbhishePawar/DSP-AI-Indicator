/** P9.6 / EPIC-007 — Institutional Research Reports workspace exports. */

export {
  REPORT_SECTIONS,
  asReportMode,
  asReportSectionId,
  isReportMode,
  isReportSectionId,
  type ReportMode,
  type ReportSectionId,
  type ReportSectionMeta,
} from "./sections";

export {
  useInstitutionalReportsPrefsStore,
  type ReportNote,
  type ReportTag,
} from "./prefsStore";
