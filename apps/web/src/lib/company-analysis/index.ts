/** EPIC-F005 — Company Analysis Workspace exports. */

export {
  ANALYSIS_SECTIONS,
  asAnalysisSectionId,
  isAnalysisSectionId,
  type AnalysisSectionId,
  type AnalysisSectionMeta,
} from "./sections";

export {
  useWorkspacePrefsStore,
  type WorkspaceNote,
  type WorkspaceTag,
} from "./workspacePrefsStore";

export {
  formatTrendValue,
  mapFinancialTrends,
  type FinancialTrendId,
  type FinancialTrendPoint,
  type FinancialTrendSeries,
  type FinancialTrendsView,
} from "./financialTrends";

export {
  downloadBase64,
  downloadText,
  researchViewToCsv,
  researchViewToHtml,
  researchViewToJson,
} from "./exportView";
