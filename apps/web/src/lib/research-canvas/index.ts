/** EPIC-014 — Institutional Research Canvas public exports. */

import {
  CANVAS_TABS,
  asCanvasTabId,
  canvasTabMeta,
  isCanvasTabId,
} from "./sections";
import type { CanvasTabId, CanvasTabMeta } from "./sections";

import {
  NOTEBOOK_KINDS,
  NOTEBOOK_KIND_LABELS,
  useResearchNotebookStore,
} from "./notebookStore";
import type { NotebookEntry, NotebookEntryKind, SavedResearchSession } from "./notebookStore";

import { useResearchCanvasPrefsStore } from "./prefsStore";

import { searchResearchCanvas } from "./search";
import type { CanvasSearchHit, CanvasSearchInput } from "./search";

import { composeResearchTimeline } from "./timeline";
import type { TimelineEvent, TimelineEventKind, TimelineInput } from "./timeline";

import {
  buildCanvasExportPackage,
  canvasPackageToHtml,
  canvasPackageToJson,
  downloadText,
} from "./exportCanvas";
import type { CanvasExportPackage } from "./exportCanvas";

import {
  RESEARCH_QUICK_ACTIONS,
  filterResearchQuickActions,
} from "./quickActions";
import type { ResearchQuickAction } from "./quickActions";

export {
  CANVAS_TABS,
  asCanvasTabId,
  canvasTabMeta,
  isCanvasTabId,
  NOTEBOOK_KINDS,
  NOTEBOOK_KIND_LABELS,
  useResearchNotebookStore,
  useResearchCanvasPrefsStore,
  searchResearchCanvas,
  composeResearchTimeline,
  buildCanvasExportPackage,
  canvasPackageToHtml,
  canvasPackageToJson,
  downloadText,
  RESEARCH_QUICK_ACTIONS,
  filterResearchQuickActions,
};

export type {
  CanvasTabId,
  CanvasTabMeta,
  NotebookEntry,
  NotebookEntryKind,
  SavedResearchSession,
  CanvasSearchHit,
  CanvasSearchInput,
  TimelineEvent,
  TimelineEventKind,
  TimelineInput,
  CanvasExportPackage,
  ResearchQuickAction,
};
