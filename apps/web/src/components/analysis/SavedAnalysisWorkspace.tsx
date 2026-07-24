"use client";

import {
  memo,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ComponentProps,
  type FormEvent,
  type ReactNode,
} from "react";

import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";
import {
  archiveAnalysis,
  compareVersions,
  createFolder,
  createSavedAnalysis,
  deleteAnalysis,
  deleteFolder,
  duplicateAnalysis,
  filterAndSortAnalyses,
  latestVersion,
  loadWorkspaceStore,
  markReportGenerated,
  moveAnalysis,
  renameAnalysis,
  renameFolder,
  saveWorkspaceStore,
  togglePin,
  updateAnalysisVersion,
  type SavedAnalysis,
  type WorkspaceFilterId,
  type WorkspaceFolder,
  type WorkspaceSortId,
  type WorkspaceStore,
} from "@/lib/analysis/sprint8Workspace";

const FILTERS: { id: WorkspaceFilterId; label: string }[] = [
  { id: "all", label: "All" },
  { id: "favorites", label: "Favorites" },
  { id: "recent", label: "Recent" },
  { id: "archived", label: "Archived" },
  { id: "high_confidence", label: "High Confidence" },
  { id: "low_confidence", label: "Low Confidence" },
  { id: "generated_reports", label: "Generated Reports" },
];

const SORTS: { id: WorkspaceSortId; label: string }[] = [
  { id: "newest", label: "Newest" },
  { id: "oldest", label: "Oldest" },
  { id: "alphabetical", label: "Alphabetical" },
  { id: "confidence", label: "Confidence" },
  { id: "recently_modified", label: "Recently Modified" },
];

export const SavedAnalysisWorkspace = memo(function SavedAnalysisWorkspace({
  view,
  onReopen,
}: {
  view: AnalysisWorkspaceView;
  onReopen: (view: AnalysisWorkspaceView, meta: { ticker: string; name: string }) => void;
}) {
  const [store, setStore] = useState<WorkspaceStore>(() =>
    typeof window === "undefined"
      ? { folders: [], analyses: [] }
      : loadWorkspaceStore(),
  );
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<WorkspaceFilterId>("all");
  const [sort, setSort] = useState<WorkspaceSortId>("newest");
  const [folderId, setFolderId] = useState<string | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [announce, setAnnounce] = useState("");
  const [dialog, setDialog] = useState<
    | null
    | { type: "rename"; id: string }
    | { type: "delete"; id: string }
    | { type: "duplicate"; id: string }
    | { type: "folder_create" }
    | { type: "folder_rename"; id: string }
    | { type: "move"; id: string }
  >(null);
  const [compareLeft, setCompareLeft] = useState<string | null>(null);
  const [compareRight, setCompareRight] = useState<string | null>(null);

  useEffect(() => {
    setStore(loadWorkspaceStore());
  }, []);

  const persist = useCallback((next: WorkspaceStore, message: string) => {
    setStore(next);
    saveWorkspaceStore(next);
    setAnnounce(message);
  }, []);

  const selected = useMemo(
    () => store.analyses.find((a) => a.id === selectedId) ?? null,
    [store.analyses, selectedId],
  );

  const visible = useMemo(
    () =>
      filterAndSortAnalyses(store.analyses, {
        query,
        filter,
        sort,
        folderId,
      }),
    [store.analyses, query, filter, sort, folderId],
  );

  // Virtualize: show first N with expand
  const [listLimit, setListLimit] = useState(24);
  const shown = visible.slice(0, listLimit);

  const onSaveCurrent = () => {
    const next = createSavedAnalysis(store, view, {
      folderId: folderId === "all" ? store.folders[0]?.id ?? null : folderId,
    });
    const created = next.analyses[0];
    persist(next, `Saved analysis “${created.name}” (local only).`);
    setSelectedId(created.id);
  };

  const onSaveNewVersion = () => {
    if (!selectedId) {
      onSaveCurrent();
      return;
    }
    const next = updateAnalysisVersion(store, selectedId, view, [
      "workspace_refresh",
      "manual_save",
    ]);
    persist(next, "Saved new analysis version (local only).");
  };

  return (
    <div className="space-y-4">
      <p className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm">
        <span className="font-medium">What you should know — </span>
        Organize, search, compare, and reopen analyses. Storage is{" "}
        <strong>local to this browser</strong> — no cloud sync, no accounts.
      </p>

      <div id="workspace-live" className="sr-only" aria-live="polite">
        {announce}
      </div>

      <WorkspaceToolbar
        onSave={onSaveCurrent}
        onSaveVersion={onSaveNewVersion}
        onOpenDrawer={() => setDrawerOpen(true)}
        canVersion={Boolean(selectedId)}
      />

      <div className="grid gap-4 lg:grid-cols-[16rem_minmax(0,1fr)_20rem]">
        <div className="hidden lg:block">
          <WorkspaceSidebar
            folders={store.folders}
            folderId={folderId}
            onSelectFolder={setFolderId}
            onCreateFolder={() => setDialog({ type: "folder_create" })}
            onRenameFolder={(id) => setDialog({ type: "folder_rename", id })}
            onDeleteFolder={(id) => {
              persist(deleteFolder(store, id), "Folder deleted (analyses moved to default).");
              if (folderId === id) setFolderId("all");
            }}
          />
        </div>

        {drawerOpen ? (
          <MobileDrawer onClose={() => setDrawerOpen(false)}>
            <WorkspaceSidebar
              folders={store.folders}
              folderId={folderId}
              onSelectFolder={(id) => {
                setFolderId(id);
                setDrawerOpen(false);
              }}
              onCreateFolder={() => setDialog({ type: "folder_create" })}
              onRenameFolder={(id) => setDialog({ type: "folder_rename", id })}
              onDeleteFolder={(id) => {
                persist(deleteFolder(store, id), "Folder deleted.");
                if (folderId === id) setFolderId("all");
              }}
            />
          </MobileDrawer>
        ) : null}

        <div className="min-w-0 space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <WorkspaceSearch query={query} onChange={setQuery} />
            <WorkspaceFilters filter={filter} onChange={setFilter} />
            <WorkspaceSortMenu sort={sort} onChange={setSort} />
          </div>

          {shown.length === 0 ? (
            <EmptyWorkspaceState onSave={onSaveCurrent} />
          ) : (
            <ul className="space-y-2" aria-label="Saved analyses">
              {shown.map((a) => (
                <li key={a.id}>
                  <AnalysisCard
                    analysis={a}
                    selected={a.id === selectedId}
                    favorite={a.pinned}
                    onSelect={() => setSelectedId(a.id)}
                    onPin={() =>
                      persist(togglePin(store, a.id), a.pinned ? "Unpinned" : "Pinned")
                    }
                    onRename={() => setDialog({ type: "rename", id: a.id })}
                    onDuplicate={() => setDialog({ type: "duplicate", id: a.id })}
                    onDelete={() => setDialog({ type: "delete", id: a.id })}
                    onMove={() => setDialog({ type: "move", id: a.id })}
                    onArchive={() =>
                      persist(
                        archiveAnalysis(store, a.id, !a.archived),
                        a.archived ? "Restored" : "Archived",
                      )
                    }
                    onReopen={() => {
                      const v = latestVersion(a);
                      if (v) onReopen(v.view, { ticker: a.ticker, name: a.name });
                    }}
                  />
                </li>
              ))}
            </ul>
          )}
          {visible.length > listLimit ? (
            <Button variant="secondary" size="sm" onClick={() => setListLimit((n) => n + 24)}>
              Show more ({visible.length - listLimit} remaining)
            </Button>
          ) : null}
        </div>

        <div className="space-y-3 lg:sticky lg:top-20 lg:self-start">
          {selected ? (
            <>
              <AnalysisMetadataCard analysis={selected} />
              <AnalysisVersionHistory
                analysis={selected}
                compareLeft={compareLeft}
                compareRight={compareRight}
                onSelectLeft={setCompareLeft}
                onSelectRight={setCompareRight}
                onReopenVersion={(verId) => {
                  const ver = selected.versions.find((v) => v.id === verId);
                  if (ver)
                    onReopen(ver.view, {
                      ticker: selected.ticker,
                      name: `${selected.name} (${ver.label})`,
                    });
                }}
              />
              {compareLeft && compareRight ? (
                <AnalysisCompareView
                  analysis={selected}
                  leftId={compareLeft}
                  rightId={compareRight}
                />
              ) : (
                <p className="text-xs text-[var(--muted)]">
                  Select two versions above to compare.
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() => {
                    const v = latestVersion(selected);
                    if (v)
                      onReopen(v.view, {
                        ticker: selected.ticker,
                        name: selected.name,
                      });
                  }}
                >
                  Reopen
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    persist(
                      markReportGenerated(store, selected.id),
                      "Marked report generated (local flag).",
                    )
                  }
                >
                  Mark report generated
                </Button>
              </div>
            </>
          ) : (
            <Card>
              <CardHeader title="Details" description="Select an analysis" />
              <CardBody className="text-sm text-[var(--muted)]">
                Confidence, methodology, limitations, and evidence count appear here.
              </CardBody>
            </Card>
          )}
        </div>
      </div>

      {dialog?.type === "rename" ? (
        <RenameAnalysisDialog
          name={store.analyses.find((a) => a.id === dialog.id)?.name ?? ""}
          onClose={() => setDialog(null)}
          onConfirm={(name) => {
            persist(renameAnalysis(store, dialog.id, name), "Renamed.");
            setDialog(null);
          }}
        />
      ) : null}
      {dialog?.type === "delete" ? (
        <DeleteAnalysisDialog
          name={store.analyses.find((a) => a.id === dialog.id)?.name ?? ""}
          onClose={() => setDialog(null)}
          onConfirm={() => {
            persist(deleteAnalysis(store, dialog.id), "Deleted.");
            if (selectedId === dialog.id) setSelectedId(null);
            setDialog(null);
          }}
        />
      ) : null}
      {dialog?.type === "duplicate" ? (
        <DuplicateAnalysisDialog
          name={store.analyses.find((a) => a.id === dialog.id)?.name ?? ""}
          onClose={() => setDialog(null)}
          onConfirm={() => {
            const next = duplicateAnalysis(store, dialog.id);
            persist(next, "Duplicated.");
            setSelectedId(next.analyses[0]?.id ?? null);
            setDialog(null);
          }}
        />
      ) : null}
      {dialog?.type === "folder_create" ? (
        <PromptDialog
          title="Create folder"
          label="Folder name"
          initial="New folder"
          onClose={() => setDialog(null)}
          onConfirm={(name) => {
            persist(createFolder(store, name), "Folder created.");
            setDialog(null);
          }}
        />
      ) : null}
      {dialog?.type === "folder_rename" ? (
        <PromptDialog
          title="Rename folder"
          label="Folder name"
          initial={store.folders.find((f) => f.id === dialog.id)?.name ?? ""}
          onClose={() => setDialog(null)}
          onConfirm={(name) => {
            persist(renameFolder(store, dialog.id, name), "Folder renamed.");
            setDialog(null);
          }}
        />
      ) : null}
      {dialog?.type === "move" ? (
        <FolderPicker
          folders={store.folders}
          currentId={store.analyses.find((a) => a.id === dialog.id)?.folderId ?? null}
          onClose={() => setDialog(null)}
          onPick={(fid) => {
            persist(moveAnalysis(store, dialog.id, fid), "Moved.");
            setDialog(null);
          }}
        />
      ) : null}
    </div>
  );
});

function WorkspaceToolbar({
  onSave,
  onSaveVersion,
  onOpenDrawer,
  canVersion,
}: {
  onSave: () => void;
  onSaveVersion: () => void;
  onOpenDrawer: () => void;
  canVersion: boolean;
}) {
  return (
    <div
      className="flex flex-wrap gap-2"
      role="toolbar"
      aria-label="Workspace actions"
    >
      <Button size="sm" className="lg:hidden" variant="secondary" onClick={onOpenDrawer}>
        Folders
      </Button>
      <Button size="sm" onClick={onSave}>
        Save analysis
      </Button>
      <Button size="sm" variant="secondary" onClick={onSaveVersion} disabled={!canVersion}>
        Save as new version
      </Button>
    </div>
  );
}

export function WorkspaceSidebar({
  folders,
  folderId,
  onSelectFolder,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
}: {
  folders: WorkspaceFolder[];
  folderId: string | "all";
  onSelectFolder: (id: string | "all") => void;
  onCreateFolder: () => void;
  onRenameFolder: (id: string) => void;
  onDeleteFolder: (id: string) => void;
}) {
  return (
    <nav aria-label="Workspace folders" className="space-y-2">
      <p className="text-xs font-medium uppercase text-[var(--muted)]">Folders</p>
      <button
        type="button"
        className={`flex min-h-11 w-full items-center rounded-md border px-3 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
          folderId === "all"
            ? "border-[var(--accent)] bg-[var(--accent-soft)]"
            : "border-[var(--border)]"
        }`}
        onClick={() => onSelectFolder("all")}
      >
        All folders
      </button>
      <ul className="space-y-2">
        {folders.map((f) => (
          <li key={f.id}>
            <AnalysisFolderCard
              folder={f}
              selected={folderId === f.id}
              onSelect={() => onSelectFolder(f.id)}
              onRename={() => onRenameFolder(f.id)}
              onDelete={() => onDeleteFolder(f.id)}
            />
          </li>
        ))}
      </ul>
      <Button size="sm" variant="secondary" onClick={onCreateFolder}>
        Create folder
      </Button>
    </nav>
  );
}

export function AnalysisFolderCard({
  folder,
  selected,
  onSelect,
  onRename,
  onDelete,
}: {
  folder: WorkspaceFolder;
  selected: boolean;
  onSelect: () => void;
  onRename: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className={`rounded-md border p-2 ${
        selected ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-[var(--border)]"
      }`}
    >
      <button
        type="button"
        className="min-h-11 w-full text-left text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        onClick={onSelect}
      >
        {folder.name}
      </button>
      <div className="mt-1 flex gap-2">
        <button type="button" className="text-xs text-[var(--accent)] underline" onClick={onRename}>
          Rename
        </button>
        {folder.id !== "folder-default" ? (
          <button
            type="button"
            className="text-xs text-[var(--muted)] underline"
            onClick={onDelete}
          >
            Delete
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function WorkspaceSearch({
  query,
  onChange,
}: {
  query: string;
  onChange: (q: string) => void;
}) {
  const id = useId();
  return (
    <label className="block flex-1 text-sm">
      <span className="text-xs uppercase text-[var(--muted)]">Search</span>
      <input
        id={id}
        type="search"
        value={query}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Company, ticker, industry, tags, folder, date…"
        className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      />
    </label>
  );
}

export function WorkspaceFilters({
  filter,
  onChange,
}: {
  filter: WorkspaceFilterId;
  onChange: (f: WorkspaceFilterId) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="text-xs uppercase text-[var(--muted)]">Filter</span>
      <select
        value={filter}
        onChange={(e) => onChange(e.target.value as WorkspaceFilterId)}
        className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        aria-label="Filter analyses"
      >
        {FILTERS.map((f) => (
          <option key={f.id} value={f.id}>
            {f.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function WorkspaceSortMenu({
  sort,
  onChange,
}: {
  sort: WorkspaceSortId;
  onChange: (s: WorkspaceSortId) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="text-xs uppercase text-[var(--muted)]">Sort</span>
      <select
        value={sort}
        onChange={(e) => onChange(e.target.value as WorkspaceSortId)}
        className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        aria-label="Sort analyses"
      >
        {SORTS.map((s) => (
          <option key={s.id} value={s.id}>
            {s.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export const AnalysisCard = memo(function AnalysisCard({
  analysis,
  selected,
  favorite,
  onSelect,
  onPin,
  onRename,
  onDuplicate,
  onDelete,
  onMove,
  onArchive,
  onReopen,
}: {
  analysis: SavedAnalysis;
  selected: boolean;
  favorite?: boolean;
  onSelect: () => void;
  onPin: () => void;
  onRename: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onMove: () => void;
  onArchive: () => void;
  onReopen: () => void;
}) {
  return (
    <article
      className={`rounded-md border p-3 ${
        selected ? "border-[var(--accent)] bg-[var(--accent-soft)]/40" : "border-[var(--border)]"
      } ${favorite ? "border-[var(--accent)]/50" : ""}`}
    >
      {favorite ? (
        <p className="mb-1 text-xs font-medium uppercase text-[var(--muted)]">Favorite</p>
      ) : null}
      <button
        type="button"
        className="w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        onClick={onSelect}
        aria-pressed={selected}
      >
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-medium">{analysis.name}</h3>
          <ConfidenceBadge level={analysis.confidence} />
          {analysis.archived ? <Badge tone="neutral">Archived</Badge> : null}
          {analysis.reportGenerated ? <Badge tone="accent">Report</Badge> : null}
        </div>
        <p className="mt-1 text-xs text-[var(--muted)]">
          {analysis.ticker} · {analysis.company} · v{analysis.version} · Evidence{" "}
          {analysis.evidenceCount}
        </p>
      </button>
      <div className="mt-2 flex flex-wrap gap-2 text-xs">
        <ActionLink onClick={onReopen}>Reopen</ActionLink>
        <ActionLink onClick={onPin}>{analysis.pinned ? "Unpin" : "Pin"}</ActionLink>
        <ActionLink onClick={onRename}>Rename</ActionLink>
        <ActionLink onClick={onDuplicate}>Duplicate</ActionLink>
        <ActionLink onClick={onMove}>Move</ActionLink>
        <ActionLink onClick={onArchive}>
          {analysis.archived ? "Restore" : "Archive"}
        </ActionLink>
        <ActionLink onClick={onDelete}>Delete</ActionLink>
      </div>
    </article>
  );
});

/** Alias for pinned presentation — same card with favorite chrome. */
export function PinnedAnalysisCard(props: ComponentProps<typeof AnalysisCard>) {
  return <AnalysisCard {...props} favorite />;
}

function ActionLink({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className="text-[var(--accent)] underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
    >
      {children}
    </button>
  );
}

export function AnalysisMetadataCard({ analysis }: { analysis: SavedAnalysis }) {
  return (
    <Card>
      <CardHeader title="Analysis metadata" />
      <CardBody className="grid gap-2 text-sm sm:grid-cols-2">
        <Meta label="Company" value={analysis.company} />
        <Meta label="Ticker" value={analysis.ticker} />
        <Meta
          label="Analysis date"
          value={analysis.analysisDate ?? "Unavailable"}
        />
        <Meta label="Last modified" value={new Date(analysis.updatedAt).toLocaleString()} />
        <Meta label="Template used" value={analysis.templateUsed} />
        <Meta label="Research mode" value={analysis.researchMode} />
        <Meta label="Confidence" value={analysis.confidenceLabel} />
        <Meta label="Evidence count" value={String(analysis.evidenceCount)} />
        <Meta
          label="Report generated"
          value={analysis.reportGenerated ? "Yes" : "No"}
        />
        <Meta label="Version" value={`v${analysis.version}`} />
        <Meta label="Methodology" value={analysis.methodologyVersion} />
        <div className="sm:col-span-2">
          <Meta label="Limitations" value={analysis.limitationsNote} />
        </div>
        <div className="sm:col-span-2">
          <Meta label="AI assistance notice" value={analysis.aiAssistanceNotice} />
        </div>
      </CardBody>
    </Card>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase text-[var(--muted)]">{label}</p>
      <p className="mt-0.5">{value}</p>
    </div>
  );
}

export function AnalysisVersionHistory({
  analysis,
  compareLeft,
  compareRight,
  onSelectLeft,
  onSelectRight,
  onReopenVersion,
}: {
  analysis: SavedAnalysis;
  compareLeft: string | null;
  compareRight: string | null;
  onSelectLeft: (id: string) => void;
  onSelectRight: (id: string) => void;
  onReopenVersion: (id: string) => void;
}) {
  return (
    <Card>
      <CardHeader
        title="Version history"
        description="Timestamps · modified sections · confidence & evidence changes"
      />
      <CardBody>
        <ul className="max-h-56 space-y-2 overflow-y-auto">
          {[...analysis.versions].reverse().map((v) => (
            <li
              key={v.id}
              className="rounded-md border border-[var(--border)] px-2 py-2 text-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">{v.label}</span>
                <ConfidenceBadge level={v.confidence} />
              </div>
              <p className="text-xs text-[var(--muted)]">
                {new Date(v.savedAt).toLocaleString()} · Evidence {v.evidenceCount}
                {v.reportGenerated ? " · Report" : ""}
              </p>
              <p className="text-xs text-[var(--muted)]">
                Modified: {v.modifiedSections.join(", ") || "—"}
              </p>
              <div className="mt-1 flex flex-wrap gap-2 text-xs">
                <ActionLink onClick={() => onSelectLeft(v.id)}>
                  Compare as A{compareLeft === v.id ? " ✓" : ""}
                </ActionLink>
                <ActionLink onClick={() => onSelectRight(v.id)}>
                  Compare as B{compareRight === v.id ? " ✓" : ""}
                </ActionLink>
                <ActionLink onClick={() => onReopenVersion(v.id)}>Reopen</ActionLink>
              </div>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

export function AnalysisCompareView({
  analysis,
  leftId,
  rightId,
}: {
  analysis: SavedAnalysis;
  leftId: string;
  rightId: string;
}) {
  const left = analysis.versions.find((v) => v.id === leftId);
  const right = analysis.versions.find((v) => v.id === rightId);
  const diffs = useMemo(() => {
    if (!left || !right) return [];
    return compareVersions(left, right);
  }, [left, right]);

  if (!left || !right) return null;

  return (
    <Card>
      <CardHeader
        title="Compare view"
        description={`${left.label} vs ${right.label} — differences highlighted`}
      />
      <CardBody>
        <div className="max-h-72 overflow-x-auto overflow-y-auto">
          <table className="w-full min-w-[28rem] text-left text-sm">
            <caption className="sr-only">Version comparison</caption>
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                <th scope="col" className="px-2 py-2">
                  Field
                </th>
                <th scope="col" className="px-2 py-2">
                  {left.label}
                </th>
                <th scope="col" className="px-2 py-2">
                  {right.label}
                </th>
              </tr>
            </thead>
            <tbody>
              {diffs.map((d) => (
                <tr
                  key={d.field}
                  className={`border-b border-[var(--border)] last:border-0 ${
                    d.changed ? "bg-[var(--accent-soft)]/50" : ""
                  }`}
                >
                  <th scope="row" className="px-2 py-2 font-medium">
                    {d.field}
                    {d.changed ? (
                      <span className="ml-1 text-xs text-[var(--accent)]">changed</span>
                    ) : null}
                  </th>
                  <td className="px-2 py-2 text-[var(--muted)]">{d.left}</td>
                  <td className="px-2 py-2 text-[var(--muted)]">{d.right}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardBody>
    </Card>
  );
}

export function EmptyWorkspaceState({ onSave }: { onSave: () => void }) {
  return (
    <Card>
      <CardHeader title="No saved analyses yet" />
      <CardBody className="space-y-3 text-sm text-[var(--muted)]">
        <p>
          Save the current Company Analysis to organize it here. Data stays in this
          browser only.
        </p>
        <Button size="sm" onClick={onSave}>
          Save current analysis
        </Button>
      </CardBody>
    </Card>
  );
}

function MobileDrawer({
  children,
  onClose,
}: {
  children: ReactNode;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
  }, []);
  return (
    <div
      className="fixed inset-0 z-40 lg:hidden"
      role="dialog"
      aria-modal="true"
      aria-label="Folders"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/40"
        aria-label="Close folders"
        onClick={onClose}
      />
      <div className="absolute bottom-0 left-0 right-0 max-h-[70vh] overflow-y-auto rounded-t-lg border border-[var(--border)] bg-[var(--surface)] p-4 shadow-lg">
        <div className="mb-3 flex justify-end">
          <button
            ref={closeRef}
            type="button"
            className="min-h-11 rounded-md border border-[var(--border)] px-3 text-sm"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function DialogShell({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
  }, []);
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
      <button
        type="button"
        className="absolute inset-0 bg-black/40"
        aria-label="Dismiss dialog"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative z-10 w-full max-w-md rounded-md border border-[var(--border)] bg-[var(--surface)] p-4 shadow-lg"
      >
        <div className="mb-3 flex items-start justify-between gap-2">
          <h2 id={titleId} className="font-medium">
            {title}
          </h2>
          <button
            ref={closeRef}
            type="button"
            className="min-h-11 rounded-md border border-[var(--border)] px-3 text-sm"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function RenameAnalysisDialog({
  name,
  onClose,
  onConfirm,
}: {
  name: string;
  onClose: () => void;
  onConfirm: (name: string) => void;
}) {
  return (
    <PromptDialog
      title="Rename analysis"
      label="Name"
      initial={name}
      onClose={onClose}
      onConfirm={onConfirm}
    />
  );
}

export function DeleteAnalysisDialog({
  name,
  onClose,
  onConfirm,
}: {
  name: string;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <DialogShell title="Delete analysis" onClose={onClose}>
      <p className="text-sm text-[var(--muted)]">
        Delete “{name}”? This cannot be undone. Local storage only.
      </p>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="danger" size="sm" onClick={onConfirm}>
          Delete
        </Button>
      </div>
    </DialogShell>
  );
}

export function DuplicateAnalysisDialog({
  name,
  onClose,
  onConfirm,
}: {
  name: string;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <DialogShell title="Duplicate analysis" onClose={onClose}>
      <p className="text-sm text-[var(--muted)]">
        Create a local copy of “{name}”?
      </p>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button size="sm" onClick={onConfirm}>
          Duplicate
        </Button>
      </div>
    </DialogShell>
  );
}

function PromptDialog({
  title,
  label,
  initial,
  onClose,
  onConfirm,
}: {
  title: string;
  label: string;
  initial: string;
  onClose: () => void;
  onConfirm: (value: string) => void;
}) {
  const [value, setValue] = useState(initial);
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    onConfirm(value);
  };
  return (
    <DialogShell title={title} onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-3">
        <label className="block text-sm">
          <span className="text-[var(--muted)]">{label}</span>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            autoFocus
          />
        </label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" size="sm">
            Save
          </Button>
        </div>
      </form>
    </DialogShell>
  );
}

export function FolderPicker({
  folders,
  currentId,
  onClose,
  onPick,
}: {
  folders: WorkspaceFolder[];
  currentId: string | null;
  onClose: () => void;
  onPick: (folderId: string) => void;
}) {
  return (
    <DialogShell title="Move to folder" onClose={onClose}>
      <ul className="space-y-2">
        {folders.map((f) => (
          <li key={f.id}>
            <button
              type="button"
              className={`min-h-11 w-full rounded-md border px-3 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                currentId === f.id
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                  : "border-[var(--border)]"
              }`}
              onClick={() => onPick(f.id)}
            >
              {f.name}
            </button>
          </li>
        ))}
      </ul>
    </DialogShell>
  );
}
