/** P9.5 / EPIC-006 — Portfolio Intelligence public exports. */

export {
  PORTFOLIO_SECTIONS,
  asPortfolioSectionId,
  isPortfolioSectionId,
  type PortfolioSectionId,
  type PortfolioSectionMeta,
} from "./sections";

export {
  usePortfolioIntelPrefsStore,
  type NamedPortfolioMeta,
  type PortfolioNote,
  type PortfolioTag,
  type WatchlistEntry,
} from "./prefsStore";

export {
  buildPortfolioExportSnapshot,
  downloadText,
  portfolioSnapshotToCsv,
  portfolioSnapshotToHtml,
  portfolioSnapshotToJson,
  type PortfolioExportSnapshot,
} from "./exportSnapshot";

export {
  attentionItems,
  researchCoverageFacts,
  sectorHoldingCounts,
  sessionAllocationBySector,
  type CountSegment,
} from "./sessionFacts";

export {
  buildPortfolioIntelligenceRequest,
  mapPortfolioIntelligenceResult,
  type PortfolioIntelligenceView,
} from "./mapPortfolioIntelligence";
