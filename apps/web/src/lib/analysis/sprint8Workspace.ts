/** Sprint 8 — Saved Analysis & Workspace Management (localStorage only). */

import type { AnalysisWorkspaceView } from "@/lib/analysis/types";
import { CONFIDENCE_LABELS, type ConfidenceLevel } from "@/lib/trust/labels";

const STORAGE_KEY = "dsp.savedWorkspace.v1";

export type WorkspaceFolder = {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
};

export type AnalysisVersion = {
  id: string;
  label: string;
  savedAt: string;
  modifiedSections: string[];
  reportGenerated: boolean;
  confidence: ConfidenceLevel;
  confidenceLabel: string;
  evidenceCount: number;
  summary: string;
  /** Snapshot of workspace view at this version */
  view: AnalysisWorkspaceView;
};

export type SavedAnalysis = {
  id: string;
  name: string;
  company: string;
  ticker: string;
  industry: string | null;
  folderId: string | null;
  tags: string[];
  pinned: boolean;
  archived: boolean;
  createdAt: string;
  updatedAt: string;
  analysisDate: string | null;
  templateUsed: string;
  researchMode: string;
  confidence: ConfidenceLevel;
  confidenceLabel: string;
  evidenceCount: number;
  reportGenerated: boolean;
  version: number;
  versions: AnalysisVersion[];
  methodologyVersion: string;
  limitationsNote: string;
  aiAssistanceNotice: string;
};

export type WorkspaceStore = {
  folders: WorkspaceFolder[];
  analyses: SavedAnalysis[];
};

export type WorkspaceFilterId =
  | "all"
  | "favorites"
  | "recent"
  | "archived"
  | "high_confidence"
  | "low_confidence"
  | "generated_reports";

export type WorkspaceSortId =
  | "newest"
  | "oldest"
  | "alphabetical"
  | "confidence"
  | "recently_modified";

export type CompareDiff = {
  field: string;
  left: string;
  right: string;
  changed: boolean;
};

function uid(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

function emptyStore(): WorkspaceStore {
  return {
    folders: [
      {
        id: "folder-default",
        name: "My Analyses",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ],
    analyses: [],
  };
}

export function loadWorkspaceStore(): WorkspaceStore {
  if (typeof window === "undefined") return emptyStore();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyStore();
    const parsed = JSON.parse(raw) as WorkspaceStore;
    if (!parsed?.folders || !parsed?.analyses) return emptyStore();
    return parsed;
  } catch {
    return emptyStore();
  }
}

export function saveWorkspaceStore(store: WorkspaceStore): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function evidenceCount(view: AnalysisWorkspaceView): number {
  return (
    view.conclusion.evidence.supportingEvidence.length +
    view.conclusion.evidence.primaryEvidence.length +
    view.evidenceExplorer.items.filter((i) => i.group !== "unavailable").length
  );
}

function metaFromView(view: AnalysisWorkspaceView) {
  const ticker = view.snapshot.ticker.value ?? "—";
  const company = view.snapshot.companyName.value ?? ticker;
  return {
    company,
    ticker,
    industry: view.snapshot.industry.value,
    analysisDate:
      view.freshness.researchDate ?? view.snapshot.researchDate.value,
    researchMode: view.freshness.researchMode,
    confidence: view.confidenceBreakdown.overall,
    confidenceLabel: CONFIDENCE_LABELS[view.confidenceBreakdown.overall],
    evidenceCount: evidenceCount(view),
    methodologyVersion: view.freshness.methodologyVersion,
    limitationsNote:
      view.researchLimitations.unavailableData.slice(0, 2).join(" · ") ||
      "See Research Limitations in the workspace",
    aiAssistanceNotice:
      "AI Research Copilot (when used) explains DSP Research only — it does not produce Buy/Sell advice.",
  };
}

function versionFromView(
  view: AnalysisWorkspaceView,
  versionNumber: number,
  modifiedSections: string[],
  reportGenerated: boolean,
): AnalysisVersion {
  const m = metaFromView(view);
  return {
    id: uid("ver"),
    label: `Analysis v${versionNumber}`,
    savedAt: new Date().toISOString(),
    modifiedSections,
    reportGenerated,
    confidence: m.confidence,
    confidenceLabel: m.confidenceLabel,
    evidenceCount: m.evidenceCount,
    summary:
      view.conclusion.conclusion.value ??
      view.dashboard.researchConclusion.value ??
      "Unavailable",
    view,
  };
}

export function createSavedAnalysis(
  store: WorkspaceStore,
  view: AnalysisWorkspaceView,
  opts?: { name?: string; folderId?: string | null; templateUsed?: string },
): WorkspaceStore {
  const m = metaFromView(view);
  const now = new Date().toISOString();
  const v1 = versionFromView(view, 1, ["initial_save"], false);
  const analysis: SavedAnalysis = {
    id: uid("analysis"),
    name: opts?.name ?? `${m.ticker} Research`,
    company: m.company,
    ticker: m.ticker,
    industry: m.industry,
    folderId: opts?.folderId ?? store.folders[0]?.id ?? null,
    tags: [m.ticker, m.industry ?? "unclassified"].filter(Boolean) as string[],
    pinned: false,
    archived: false,
    createdAt: now,
    updatedAt: now,
    analysisDate: m.analysisDate,
    templateUsed: opts?.templateUsed ?? "Full Research",
    researchMode: m.researchMode,
    confidence: m.confidence,
    confidenceLabel: m.confidenceLabel,
    evidenceCount: m.evidenceCount,
    reportGenerated: false,
    version: 1,
    versions: [v1],
    methodologyVersion: m.methodologyVersion,
    limitationsNote: m.limitationsNote,
    aiAssistanceNotice: m.aiAssistanceNotice,
  };
  return {
    ...store,
    analyses: [analysis, ...store.analyses],
  };
}

export function updateAnalysisVersion(
  store: WorkspaceStore,
  analysisId: string,
  view: AnalysisWorkspaceView,
  modifiedSections: string[],
): WorkspaceStore {
  return {
    ...store,
    analyses: store.analyses.map((a) => {
      if (a.id !== analysisId) return a;
      const nextVersion = a.version + 1;
      const m = metaFromView(view);
      const ver = versionFromView(
        view,
        nextVersion,
        modifiedSections,
        a.reportGenerated,
      );
      return {
        ...a,
        ...m,
        version: nextVersion,
        updatedAt: new Date().toISOString(),
        versions: [...a.versions, ver],
      };
    }),
  };
}

export function renameAnalysis(
  store: WorkspaceStore,
  id: string,
  name: string,
): WorkspaceStore {
  return {
    ...store,
    analyses: store.analyses.map((a) =>
      a.id === id
        ? { ...a, name: name.trim() || a.name, updatedAt: new Date().toISOString() }
        : a,
    ),
  };
}

export function duplicateAnalysis(
  store: WorkspaceStore,
  id: string,
): WorkspaceStore {
  const src = store.analyses.find((a) => a.id === id);
  if (!src) return store;
  const now = new Date().toISOString();
  const copy: SavedAnalysis = {
    ...structuredClone(src),
    id: uid("analysis"),
    name: `${src.name} (copy)`,
    pinned: false,
    createdAt: now,
    updatedAt: now,
    versions: src.versions.map((v) => ({
      ...structuredClone(v),
      id: uid("ver"),
    })),
  };
  return { ...store, analyses: [copy, ...store.analyses] };
}

export function deleteAnalysis(store: WorkspaceStore, id: string): WorkspaceStore {
  return { ...store, analyses: store.analyses.filter((a) => a.id !== id) };
}

export function togglePin(store: WorkspaceStore, id: string): WorkspaceStore {
  return {
    ...store,
    analyses: store.analyses.map((a) =>
      a.id === id
        ? { ...a, pinned: !a.pinned, updatedAt: new Date().toISOString() }
        : a,
    ),
  };
}

export function archiveAnalysis(
  store: WorkspaceStore,
  id: string,
  archived: boolean,
): WorkspaceStore {
  return {
    ...store,
    analyses: store.analyses.map((a) =>
      a.id === id
        ? { ...a, archived, pinned: archived ? false : a.pinned, updatedAt: new Date().toISOString() }
        : a,
    ),
  };
}

export function moveAnalysis(
  store: WorkspaceStore,
  id: string,
  folderId: string | null,
): WorkspaceStore {
  return {
    ...store,
    analyses: store.analyses.map((a) =>
      a.id === id
        ? { ...a, folderId, updatedAt: new Date().toISOString() }
        : a,
    ),
  };
}

export function markReportGenerated(
  store: WorkspaceStore,
  id: string,
): WorkspaceStore {
  return {
    ...store,
    analyses: store.analyses.map((a) =>
      a.id === id
        ? {
            ...a,
            reportGenerated: true,
            updatedAt: new Date().toISOString(),
            versions: a.versions.map((v, i) =>
              i === a.versions.length - 1
                ? { ...v, reportGenerated: true }
                : v,
            ),
          }
        : a,
    ),
  };
}

export function createFolder(store: WorkspaceStore, name: string): WorkspaceStore {
  const now = new Date().toISOString();
  return {
    ...store,
    folders: [
      ...store.folders,
      {
        id: uid("folder"),
        name: name.trim() || "Untitled folder",
        createdAt: now,
        updatedAt: now,
      },
    ],
  };
}

export function renameFolder(
  store: WorkspaceStore,
  id: string,
  name: string,
): WorkspaceStore {
  return {
    ...store,
    folders: store.folders.map((f) =>
      f.id === id
        ? { ...f, name: name.trim() || f.name, updatedAt: new Date().toISOString() }
        : f,
    ),
  };
}

export function deleteFolder(store: WorkspaceStore, id: string): WorkspaceStore {
  if (id === "folder-default") return store;
  return {
    folders: store.folders.filter((f) => f.id !== id),
    analyses: store.analyses.map((a) =>
      a.folderId === id
        ? { ...a, folderId: "folder-default", updatedAt: new Date().toISOString() }
        : a,
    ),
  };
}

const CONF_RANK: Record<ConfidenceLevel, number> = {
  very_high: 5,
  high: 4,
  moderate: 3,
  low: 2,
  insufficient_evidence: 1,
};

export function filterAndSortAnalyses(
  analyses: SavedAnalysis[],
  opts: {
    query: string;
    filter: WorkspaceFilterId;
    sort: WorkspaceSortId;
    folderId: string | null | "all";
  },
): SavedAnalysis[] {
  const q = opts.query.trim().toLowerCase();
  let list = analyses.filter((a) => {
    if (opts.folderId !== "all" && a.folderId !== opts.folderId) return false;
    if (opts.filter === "favorites" && !a.pinned) return false;
    if (opts.filter === "archived" && !a.archived) return false;
    if (opts.filter !== "archived" && a.archived && opts.filter !== "all")
      return false;
    if (opts.filter === "recent") {
      const week = Date.now() - 7 * 24 * 60 * 60 * 1000;
      if (new Date(a.updatedAt).getTime() < week) return false;
    }
    if (opts.filter === "high_confidence") {
      if (CONF_RANK[a.confidence] < CONF_RANK.moderate) return false;
    }
    if (opts.filter === "low_confidence") {
      if (CONF_RANK[a.confidence] > CONF_RANK.low) return false;
    }
    if (opts.filter === "generated_reports" && !a.reportGenerated) return false;
    if (opts.filter === "all" && a.archived) return false;

    if (!q) return true;
    const hay = [
      a.name,
      a.company,
      a.ticker,
      a.industry ?? "",
      a.folderId ?? "",
      ...a.tags,
      a.createdAt,
      a.updatedAt,
    ]
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  });

  list = [...list].sort((a, b) => {
    switch (opts.sort) {
      case "oldest":
        return a.createdAt.localeCompare(b.createdAt);
      case "alphabetical":
        return a.name.localeCompare(b.name);
      case "confidence":
        return CONF_RANK[b.confidence] - CONF_RANK[a.confidence];
      case "recently_modified":
        return b.updatedAt.localeCompare(a.updatedAt);
      case "newest":
      default:
        return b.createdAt.localeCompare(a.createdAt);
    }
  });

  // Pinned first within non-archived views
  if (opts.filter !== "archived") {
    list = [...list.filter((a) => a.pinned), ...list.filter((a) => !a.pinned)];
  }
  return list;
}

export function compareVersions(
  left: AnalysisVersion,
  right: AnalysisVersion,
): CompareDiff[] {
  const lv = left.view;
  const rv = right.view;
  const rows: CompareDiff[] = [
    {
      field: "Summary / DSP View",
      left: left.summary,
      right: right.summary,
      changed: left.summary !== right.summary,
    },
    {
      field: "Confidence",
      left: left.confidenceLabel,
      right: right.confidenceLabel,
      changed: left.confidence !== right.confidence,
    },
    {
      field: "Evidence count",
      left: String(left.evidenceCount),
      right: String(right.evidenceCount),
      changed: left.evidenceCount !== right.evidenceCount,
    },
    {
      field: "Coverage %",
      left: `${lv.coverage.coveragePercent}%`,
      right: `${rv.coverage.coveragePercent}%`,
      changed: lv.coverage.coveragePercent !== rv.coverage.coveragePercent,
    },
    {
      field: "Research mode",
      left: lv.freshness.researchMode,
      right: rv.freshness.researchMode,
      changed: lv.freshness.researchMode !== rv.freshness.researchMode,
    },
    {
      field: "Methodology",
      left: lv.freshness.methodologyVersion,
      right: rv.freshness.methodologyVersion,
      changed: lv.freshness.methodologyVersion !== rv.freshness.methodologyVersion,
    },
    {
      field: "Limitations (count)",
      left: String(lv.researchLimitations.unavailableData.length),
      right: String(rv.researchLimitations.unavailableData.length),
      changed:
        lv.researchLimitations.unavailableData.length !==
        rv.researchLimitations.unavailableData.length,
    },
    {
      field: "Report generated",
      left: left.reportGenerated ? "Yes" : "No",
      right: right.reportGenerated ? "Yes" : "No",
      changed: left.reportGenerated !== right.reportGenerated,
    },
    {
      field: `${presentField("recommendation")}`,
      left: String(lv.conclusion.conclusion.value ?? "Unavailable"),
      right: String(rv.conclusion.conclusion.value ?? "Unavailable"),
      changed:
        lv.conclusion.conclusion.value !== rv.conclusion.conclusion.value,
    },
  ];
  return rows;
}

function presentField(key: string): string {
  // Avoid importing terminology circularly for a label — keep local
  if (key === "recommendation") return "Research Conclusion";
  return key;
}

export function latestVersion(analysis: SavedAnalysis): AnalysisVersion | null {
  return analysis.versions[analysis.versions.length - 1] ?? null;
}
