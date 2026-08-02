/** EPIC-014 — Institutional Research Canvas public exports. */

export {
  CANVAS_TABS,
  asCanvasTabId,
  canvasTabMeta,
  isCanvasTabId,
  type CanvasTabId,
  type CanvasTabMeta,
} from "./sections";

export {
  NOTEBOOK_KINDS,
  NOTEBOOK_KIND_LABELS,
  useResearchNotebookStore,
  type NotebookEntry,
  type NotebookEntryKind,
  type SavedResearchSession,
} from "./notebookStore";

export { useResearchCanvasPrefsStore } from "./prefsStore";

export {
  searchResearchCanvas,
  type CanvasSearchHit,
  type CanvasSearchInput,
} from "./search";

export {
  composeResearchTimeline,
  type TimelineEvent,
  type TimelineEventKind,
  type TimelineInput,
} from "./timeline";

export {
  buildCanvasExportPackage,
  canvasPackageToHtml,
  canvasPackageToJson,
  downloadText,
  type CanvasExportPackage,
} from "./exportCanvas";

export {
  RESEARCH_QUICK_ACTIONS,
  filterResearchQuickActions,
  type ResearchQuickAction,
} from "./quickActions";
