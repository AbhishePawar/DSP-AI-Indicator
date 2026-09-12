/** P9.5 / EPIC-006 — Portfolio Intelligence public exports. */

export { PORTFOLIO_SECTIONS, asPortfolioSectionId, isPortfolioSectionId } from "./sections";
export type { PortfolioSectionId, PortfolioSectionMeta } from "./sections";

export { usePortfolioIntelPrefsStore } from "./prefsStore";
export type { NamedPortfolioMeta, PortfolioNote, PortfolioTag, WatchlistEntry } from "./prefsStore";

export { buildPortfolioExportSnapshot, downloadText, portfolioSnapshotToCsv, portfolioSnapshotToHtml, portfolioSnapshotToJson } from "./exportSnapshot";
export type { PortfolioExportSnapshot } from "./exportSnapshot";

export { attentionItems, researchCoverageFacts, sectorHoldingCounts, sessionAllocationBySector } from "./sessionFacts";
export type { CountSegment } from "./sessionFacts";

export { buildPortfolioIntelligenceRequest, mapPortfolioIntelligenceResult } from "./mapPortfolioIntelligence";
export type { PortfolioIntelligenceView } from "./mapPortfolioIntelligence";
