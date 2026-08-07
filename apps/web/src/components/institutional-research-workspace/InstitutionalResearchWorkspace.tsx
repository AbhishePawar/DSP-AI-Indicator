"use client";

/**
 * RC1 Milestone 8 — Institutional Research Workspace.
 * Thin /api/v1/research-workspace client — orchestration only; reuses Copilot 2.0 + workflow.
 */

import {
  Suspense,
  lazy,
  useCallback,
  useMemo,
  useState,
  startTransition,
} from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Alert, Button, Input, Textarea } from "@/components/ds";
import { PageHeader } from "@/components/layout/PageHeader";
import { SurfaceTrustChrome } from "@/components/trust/SurfaceTrustChrome";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { featureFlags } from "@/lib/featureFlags";
import {
  PUBLISH_STATUSES,
  RESEARCH_WORKSPACE_AI_ACTIONS,
  RESEARCH_WORKSPACE_TEMPLATES,
} from "@/lib/research-workspace/templates";
import { dashboardSurfaceTrust } from "@/lib/trust/surfaceTrust";
import { cn } from "@/lib/utils";

import type {
  WorkspaceBookmark,
  WorkspaceComment,
  WorkspaceDashboard,
  WorkspaceFolder,
  WorkspaceNote,
  WorkspaceVersion,
} from "./types";

const LazyDashboardPanel = lazy(() =>
  import("./WorkspaceDashboardPanel").then((m) => ({
    default: m.WorkspaceDashboardPanel,
  })),
);

type RightTab = "comments" | "versions" | "bookmarks" | "search";

function asNotes(raw: unknown): WorkspaceNote[] {
  return Array.isArray(raw) ? (raw as WorkspaceNote[]) : [];
}

function asFolders(raw: unknown): WorkspaceFolder[] {
  return Array.isArray(raw) ? (raw as WorkspaceFolder[]) : [];
}

function asBookmarks(raw: unknown): WorkspaceBookmark[] {
  return Array.isArray(raw) ? (raw as WorkspaceBookmark[]) : [];
}

function asComments(raw: unknown): WorkspaceComment[] {
  return Array.isArray(raw) ? (raw as WorkspaceComment[]) : [];
}

function asVersions(raw: unknown): WorkspaceVersion[] {
  return Array.isArray(raw) ? (raw as WorkspaceVersion[]) : [];
}

export function InstitutionalResearchWorkspace() {
  const { session, user } = useAuth();
  const token = session?.accessToken;
  const qc = useQueryClient();
  const actorId =
    (user as { id?: string } | null)?.id ||
    (user as { email?: string } | null)?.email ||
    "analyst";

  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [selectedFolderId, setSelectedFolderId] = useState<string>("folder-root");
  const [draftTitle, setDraftTitle] = useState("");
  const [draftBody, setDraftBody] = useState("");
  const [draftCompany, setDraftCompany] = useState("");
  const [rightTab, setRightTab] = useState<RightTab>("comments");
  const [searchQ, setSearchQ] = useState("");
  const [commentBody, setCommentBody] = useState("");
  const [shareUser, setShareUser] = useState("");
  const [aiPreview, setAiPreview] = useState<string | null>(null);
  const [diffText, setDiffText] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [tagLabel, setTagLabel] = useState("");

  const opts = useMemo(() => ({ token }), [token]);

  const dashQuery = useQuery({
    queryKey: ["rw-dashboard"],
    queryFn: () => api.researchWorkspaceDashboard(opts),
    enabled: featureFlags.researchWorkspacePlatform,
    retry: false,
  });

  const notesQuery = useQuery({
    queryKey: ["rw-notes"],
    queryFn: () => api.researchWorkspaceListNotes(opts),
    enabled: featureFlags.researchWorkspacePlatform,
    retry: false,
  });

  const foldersQuery = useQuery({
    queryKey: ["rw-folders"],
    queryFn: () => api.researchWorkspaceListFolders(opts),
    enabled: featureFlags.researchWorkspacePlatform,
    retry: false,
  });

  const bookmarksQuery = useQuery({
    queryKey: ["rw-bookmarks"],
    queryFn: () => api.researchWorkspaceListBookmarks(opts),
    enabled: featureFlags.researchWorkspacePlatform,
    retry: false,
  });

  const noteQuery = useQuery({
    queryKey: ["rw-note", selectedNoteId],
    queryFn: () => api.researchWorkspaceGetNote(selectedNoteId!, opts),
    enabled: Boolean(selectedNoteId) && featureFlags.researchWorkspacePlatform,
    retry: false,
  });

  const versionsQuery = useQuery({
    queryKey: ["rw-versions", selectedNoteId],
    queryFn: () => api.researchWorkspaceNoteVersions(selectedNoteId!, opts),
    enabled: Boolean(selectedNoteId) && rightTab === "versions",
    retry: false,
  });

  const searchQuery = useQuery({
    queryKey: ["rw-search", searchQ],
    queryFn: () => api.researchWorkspaceSearch(searchQ, opts),
    enabled: rightTab === "search" && searchQ.trim().length > 0,
    retry: false,
  });

  const notes = asNotes(notesQuery.data?.result?.notes);
  const folders = asFolders(foldersQuery.data?.result?.folders);
  const bookmarks = asBookmarks(bookmarksQuery.data?.result?.bookmarks);
  const dashboard = (dashQuery.data?.result || {}) as WorkspaceDashboard;
  const activeNote = (noteQuery.data?.result?.note || null) as WorkspaceNote | null;
  const versions = asVersions(versionsQuery.data?.result?.versions);
  const openComments = asComments(dashboard.open_comments).filter(
    (c) => !selectedNoteId || c.note_id === selectedNoteId,
  );

  const selectNote = useCallback((note: WorkspaceNote) => {
    startTransition(() => {
      setSelectedNoteId(note.note_id);
      setDraftTitle(note.title || "");
      setDraftBody(note.body || "");
      setDraftCompany(String(note.company || ""));
      setAiPreview(null);
      setDiffText(null);
      setStatusMsg(null);
    });
  }, []);

  const invalidateAll = () => {
    void qc.invalidateQueries({ queryKey: ["rw-dashboard"] });
    void qc.invalidateQueries({ queryKey: ["rw-notes"] });
    void qc.invalidateQueries({ queryKey: ["rw-folders"] });
    void qc.invalidateQueries({ queryKey: ["rw-bookmarks"] });
    if (selectedNoteId) {
      void qc.invalidateQueries({ queryKey: ["rw-note", selectedNoteId] });
      void qc.invalidateQueries({ queryKey: ["rw-versions", selectedNoteId] });
    }
  };

  const createNote = useMutation({
    mutationFn: () =>
      api.researchWorkspaceCreateNote(
        {
          title: "Untitled note",
          body: "",
          format: "markdown",
          folder_id: selectedFolderId,
          created_by: actorId,
        },
        opts,
      ),
    onSuccess: (res) => {
      const note = res.result?.note as WorkspaceNote | undefined;
      invalidateAll();
      if (note) selectNote(note);
    },
  });

  const saveNote = useMutation({
    mutationFn: () => {
      if (!selectedNoteId) throw new Error("No note selected");
      return api.researchWorkspaceUpdateNote(
        selectedNoteId,
        {
          title: draftTitle,
          body: draftBody,
          company: draftCompany || undefined,
          folder_id: selectedFolderId,
        },
        opts,
      );
    },
    onSuccess: (res) => {
      const note = res.result?.note as WorkspaceNote | undefined;
      setStatusMsg(`Saved · v${note?.version ?? "?"}`);
      invalidateAll();
      if (note) {
        setDraftTitle(note.title || "");
        setDraftBody(note.body || "");
      }
    },
    onError: (err) => setStatusMsg((err as Error).message || "Data unavailable."),
  });

  const applyTemplate = useMutation({
    mutationFn: (templateId: string) =>
      api.researchWorkspaceApplyTemplate(
        {
          template_id: templateId,
          company: draftCompany || undefined,
          folder_id: selectedFolderId,
        },
        opts,
      ),
    onSuccess: (res) => {
      const note = res.result?.note as WorkspaceNote | undefined;
      invalidateAll();
      if (note) selectNote(note);
    },
  });

  const publish = useMutation({
    mutationFn: (status: string) => {
      if (!selectedNoteId) throw new Error("No note selected");
      return api.researchWorkspacePublish(
        { note_id: selectedNoteId, status, actor_id: actorId },
        opts,
      );
    },
    onSuccess: () => {
      setStatusMsg("Publish workflow updated.");
      invalidateAll();
    },
  });

  const createFolder = useMutation({
    mutationFn: () =>
      api.researchWorkspaceCreateFolder(
        { name: "New folder", parent_id: selectedFolderId },
        opts,
      ),
    onSuccess: invalidateAll,
  });

  const archiveFolder = useMutation({
    mutationFn: () =>
      api.researchWorkspaceUpdateFolder(
        selectedFolderId,
        { archived: true },
        opts,
      ),
    onSuccess: () => {
      setSelectedFolderId("folder-root");
      invalidateAll();
    },
  });

  const deleteFolder = useMutation({
    mutationFn: () =>
      api.researchWorkspaceDeleteFolder(selectedFolderId, opts),
    onSuccess: () => {
      setSelectedFolderId("folder-root");
      invalidateAll();
    },
  });

  const createTag = useMutation({
    mutationFn: () =>
      api.researchWorkspaceUpsertTag(
        { label: tagLabel.trim(), color: "#0f766e", kind: "custom" },
        opts,
      ),
    onSuccess: () => {
      setTagLabel("");
      invalidateAll();
    },
  });

  const addComment = useMutation({
    mutationFn: () => {
      if (!selectedNoteId) throw new Error("No note selected");
      return api.researchWorkspaceAddComment(
        { note_id: selectedNoteId, body: commentBody, author_id: actorId },
        opts,
      );
    },
    onSuccess: () => {
      setCommentBody("");
      invalidateAll();
    },
  });

  const resolveComment = useMutation({
    mutationFn: (commentId: string) =>
      api.researchWorkspaceResolveComment(commentId, true, opts),
    onSuccess: invalidateAll,
  });

  const shareNote = useMutation({
    mutationFn: () => {
      if (!selectedNoteId || !shareUser.trim()) throw new Error("Share user required");
      return api.researchWorkspaceShare(
        {
          note_id: selectedNoteId,
          user_ids: [shareUser.trim()],
          permission: "comment",
          created_by: actorId,
        },
        opts,
      );
    },
    onSuccess: () => {
      setShareUser("");
      setStatusMsg("Shared.");
      invalidateAll();
    },
  });

  const bookmarkNote = useMutation({
    mutationFn: () => {
      if (!selectedNoteId) throw new Error("No note selected");
      return api.researchWorkspaceCreateBookmark(
        {
          kind: "note",
          label: draftTitle || selectedNoteId,
          target_id: selectedNoteId,
          company: draftCompany || undefined,
          href: `/research/workspace?note=${selectedNoteId}`,
        },
        opts,
      );
    },
    onSuccess: invalidateAll,
  });

  const restoreVersion = useMutation({
    mutationFn: (version: number) => {
      if (!selectedNoteId) throw new Error("No note selected");
      return api.researchWorkspaceRestoreVersion(selectedNoteId, version, opts);
    },
    onSuccess: (res) => {
      const note = res.result?.note as WorkspaceNote | undefined;
      if (note) selectNote(note);
      invalidateAll();
    },
  });

  const runAi = useMutation({
    mutationFn: (instruction: string) =>
      api.researchWorkspaceAi(
        {
          note_id: selectedNoteId || undefined,
          instruction,
          company: draftCompany || undefined,
          apply_to_note: false,
        },
        opts,
      ),
    onSuccess: (res) => {
      const answer =
        (res.result?.answer as string | undefined) ||
        res.message ||
        "Data unavailable.";
      setAiPreview(answer);
    },
  });

  const trustSummary = useMemo(
    () =>
      dashboardSurfaceTrust({
        widgetCount: notes.length + folders.length,
        note: "Institutional Research Workspace · orchestration only · Copilot 2.0 + workflow reuse",
      }),
    [notes.length, folders.length],
  );

  if (!featureFlags.researchWorkspacePlatform) {
    return (
      <div className="space-y-4 p-6">
        <Alert variant="warning" title="Research Workspace platform disabled.">
          Set NEXT_PUBLIC_RESEARCH_WORKSPACE_PLATFORM=true to enable.
        </Alert>
      </div>
    );
  }

  const folderNotes = notes.filter(
    (n) => (n.folder_id || "folder-root") === selectedFolderId,
  );

  return (
    <div
      className="flex min-h-[calc(100vh-4rem)] flex-col gap-4 p-3 md:p-5"
      data-testid="institutional-research-workspace"
    >
      <SurfaceTrustChrome summary={trustSummary} />
      <PageHeader
        title="Research Workspace"
        description="Analyst notes, folders, bookmarks, templates, versions, and publish workflow — thin client over /api/v1/research-workspace."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/research">
              <Button size="sm" variant="secondary">
                Library
              </Button>
            </Link>
            <Link href="/copilot">
              <Button size="sm" variant="secondary">
                Copilot 2.0
              </Button>
            </Link>
            <Button
              size="sm"
              onClick={() => createNote.mutate()}
              disabled={createNote.isPending}
            >
              New note
            </Button>
          </div>
        }
      />

      {(dashQuery.isError || notesQuery.isError) && (
        <Alert variant="error" title="Data unavailable.">
          Unable to load Research Workspace.
        </Alert>
      )}

      {statusMsg ? (
        <p className="text-xs text-[var(--muted)]" role="status">
          {statusMsg}
        </p>
      ) : null}

      <Suspense
        fallback={
          <p className="text-xs text-[var(--muted)]">Loading dashboard…</p>
        }
      >
        <LazyDashboardPanel dashboard={dashboard} onOpenNote={selectNote} />
      </Suspense>

      <div className="grid min-h-[28rem] flex-1 gap-3 lg:grid-cols-[220px_minmax(0,1fr)_280px]">
        {/* Folder tree + notes */}
        <aside
          className="space-y-3 rounded-md border border-[var(--border)] p-3"
          aria-label="Folders and notes"
        >
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-medium">Folders</h2>
            <div className="flex gap-1">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => createFolder.mutate()}
              >
                +
              </Button>
              {selectedFolderId !== "folder-root" ? (
                <>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => archiveFolder.mutate()}
                  >
                    Archive
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => deleteFolder.mutate()}
                  >
                    Del
                  </Button>
                </>
              ) : null}
            </div>
          </div>
          <ul className="max-h-40 space-y-1 overflow-auto text-sm">
            {folders.map((f) => (
              <li key={f.folder_id}>
                <button
                  type="button"
                  className={cn(
                    "w-full rounded px-2 py-1 text-left hover:bg-[var(--surface-2)]",
                    selectedFolderId === f.folder_id &&
                      "bg-[var(--surface-2)] font-medium",
                    f.archived && "opacity-50",
                  )}
                  onClick={() => setSelectedFolderId(f.folder_id)}
                >
                  {f.name || f.folder_id}
                </button>
              </li>
            ))}
          </ul>
          <h2 className="text-sm font-medium">Notes</h2>
          <ul className="max-h-64 space-y-1 overflow-auto text-sm">
            {folderNotes.map((n) => (
              <li key={n.note_id}>
                <button
                  type="button"
                  className={cn(
                    "w-full rounded px-2 py-1 text-left hover:bg-[var(--surface-2)]",
                    selectedNoteId === n.note_id &&
                      "bg-[var(--surface-2)] font-medium",
                  )}
                  onClick={() => selectNote(n)}
                >
                  <span className="block truncate">{n.title || "Untitled"}</span>
                  <span className="text-[10px] text-[var(--muted)]">
                    {n.status || "draft"}
                    {n.company ? ` · ${n.company}` : ""}
                  </span>
                </button>
              </li>
            ))}
            {folderNotes.length === 0 ? (
              <li className="text-xs text-[var(--muted)]">No notes in folder.</li>
            ) : null}
          </ul>
          <div className="space-y-1">
            <p className="text-xs text-[var(--muted)]">Templates</p>
            <div className="flex flex-wrap gap-1">
              {RESEARCH_WORKSPACE_TEMPLATES.map((t) => (
                <Button
                  key={t.id}
                  size="sm"
                  variant="secondary"
                  onClick={() => applyTemplate.mutate(t.id)}
                >
                  {t.label}
                </Button>
              ))}
            </div>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-[var(--muted)]">Tags</p>
            <ul className="mb-1 flex flex-wrap gap-1 text-[10px]">
              {(dashboard.tags || []).slice(0, 8).map((t) => (
                <li
                  key={String(t.tag_id)}
                  className="rounded px-1.5 py-0.5"
                  style={{
                    background: String(t.color || "#64748b33"),
                  }}
                >
                  {String(t.label || t.tag_id)}
                </li>
              ))}
            </ul>
            <div className="flex gap-1">
              <Input
                value={tagLabel}
                onChange={(e) => setTagLabel(e.target.value)}
                placeholder="New tag"
                aria-label="New tag label"
              />
              <Button
                size="sm"
                variant="secondary"
                disabled={!tagLabel.trim()}
                onClick={() => createTag.mutate()}
              >
                Add
              </Button>
            </div>
          </div>
        </aside>

        {/* Editor */}
        <section
          className="flex min-h-[24rem] flex-col gap-2 rounded-md border border-[var(--border)] p-3"
          aria-label="Note editor"
        >
          {selectedNoteId ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                  aria-label="Note title"
                  className="min-w-[12rem] flex-1"
                />
                <Input
                  value={draftCompany}
                  onChange={(e) => setDraftCompany(e.target.value)}
                  aria-label="Attached company"
                  placeholder="Company"
                  className="w-28"
                />
                <Button
                  size="sm"
                  onClick={() => saveNote.mutate()}
                  disabled={saveNote.isPending}
                >
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => bookmarkNote.mutate()}
                >
                  Bookmark
                </Button>
              </div>
              <Textarea
                value={draftBody}
                onChange={(e) => setDraftBody(e.target.value)}
                aria-label="Note body markdown"
                className="min-h-[16rem] flex-1 font-mono text-sm"
              />
              <div className="flex flex-wrap items-center gap-2">
                <label className="text-xs text-[var(--muted)]" htmlFor="rw-status">
                  Publish
                </label>
                <select
                  id="rw-status"
                  className="rounded border border-[var(--border)] bg-transparent px-2 py-1 text-sm"
                  defaultValue="review"
                  onChange={(e) => {
                    if (e.target.value) publish.mutate(e.target.value);
                  }}
                >
                  <option value="">Select status…</option>
                  {PUBLISH_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <span className="text-xs text-[var(--muted)]">
                  Current: {activeNote?.status || "draft"}
                  {activeNote?.version != null
                    ? ` · v${activeNote.version}`
                    : ""}
                </span>
              </div>
              <div className="flex flex-wrap gap-1">
                {RESEARCH_WORKSPACE_AI_ACTIONS.map((a) => (
                  <Button
                    key={a.id}
                    size="sm"
                    variant="secondary"
                    disabled={runAi.isPending}
                    onClick={() => runAi.mutate(a.instruction)}
                  >
                    {a.id}
                  </Button>
                ))}
              </div>
              {aiPreview ? (
                <div className="rounded border border-[var(--border)] p-2 text-sm whitespace-pre-wrap">
                  <p className="mb-1 text-xs text-[var(--muted)]">
                    Copilot 2.0 preview (not applied)
                  </p>
                  {aiPreview}
                </div>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-[var(--muted)]">
              Select a note or create one to begin. Markdown editor · versioned
              saves · workflow publish.
            </p>
          )}
        </section>

        {/* Right panel */}
        <aside
          className="flex flex-col gap-2 rounded-md border border-[var(--border)] p-3"
          aria-label="Workspace side panel"
        >
          <div className="flex flex-wrap gap-1">
            {(
              [
                "comments",
                "versions",
                "bookmarks",
                "search",
              ] as const satisfies readonly RightTab[]
            ).map((tab) => (
              <Button
                key={tab}
                size="sm"
                variant={rightTab === tab ? "primary" : "secondary"}
                onClick={() => setRightTab(tab)}
              >
                {tab}
              </Button>
            ))}
          </div>

          {rightTab === "comments" ? (
            <div className="space-y-2">
              <ul className="max-h-48 space-y-2 overflow-auto text-sm">
                {openComments.map((c) => (
                  <li
                    key={c.comment_id}
                    className="rounded border border-[var(--border)] p-2"
                  >
                    <p>{c.body}</p>
                    <p className="text-[10px] text-[var(--muted)]">
                      {c.author_id} · {c.resolved ? "resolved" : "open"}
                    </p>
                    {!c.resolved ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => resolveComment.mutate(c.comment_id)}
                      >
                        Resolve
                      </Button>
                    ) : null}
                  </li>
                ))}
                {openComments.length === 0 ? (
                  <li className="text-xs text-[var(--muted)]">No comments.</li>
                ) : null}
              </ul>
              <Textarea
                value={commentBody}
                onChange={(e) => setCommentBody(e.target.value)}
                placeholder="Comment… use @user to mention"
                aria-label="New comment"
                className="min-h-[4rem] text-sm"
              />
              <Button
                size="sm"
                disabled={!selectedNoteId || !commentBody.trim()}
                onClick={() => addComment.mutate()}
              >
                Add comment
              </Button>
              <div className="flex gap-1">
                <Input
                  value={shareUser}
                  onChange={(e) => setShareUser(e.target.value)}
                  placeholder="Share user id"
                  aria-label="Share with user"
                />
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={!selectedNoteId || !shareUser.trim()}
                  onClick={() => shareNote.mutate()}
                >
                  Share
                </Button>
              </div>
            </div>
          ) : null}

          {rightTab === "versions" ? (
            <div className="space-y-2">
              <ul className="max-h-64 space-y-1 overflow-auto text-sm">
                {versions.map((v) => (
                  <li
                    key={v.version}
                    className="flex items-center justify-between gap-2 rounded border border-[var(--border)] px-2 py-1"
                  >
                    <span>
                      v{v.version}
                      <span className="ml-1 text-[10px] text-[var(--muted)]">
                        {v.saved_at}
                      </span>
                    </span>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={async () => {
                          if (!selectedNoteId || versions.length < 2) return;
                          const from = Math.max(1, v.version - 1);
                          const res = await api.researchWorkspaceDiffVersions(
                            selectedNoteId,
                            from,
                            v.version,
                            opts,
                          );
                          const hunks = (res.result?.hunks || []) as Array<{
                            line?: number;
                            from?: string | null;
                            to?: string | null;
                          }>;
                          setDiffText(
                            [
                              `Diff v${from} → v${v.version}`,
                              ...hunks.map(
                                (h) =>
                                  `L${h.line ?? "?"}: - ${h.from ?? ""} / + ${h.to ?? ""}`,
                              ),
                            ].join("\n") || "No changes.",
                          );
                        }}
                      >
                        Diff
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => restoreVersion.mutate(v.version)}
                      >
                        Restore
                      </Button>
                    </div>
                  </li>
                ))}
                {versions.length === 0 ? (
                  <li className="text-xs text-[var(--muted)]">
                    Save a note to create versions.
                  </li>
                ) : null}
              </ul>
              {diffText ? (
                <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded border border-[var(--border)] p-2 text-xs">
                  {diffText}
                </pre>
              ) : null}
            </div>
          ) : null}

          {rightTab === "bookmarks" ? (
            <ul className="max-h-72 space-y-1 overflow-auto text-sm">
              {bookmarks.map((b) => (
                <li
                  key={b.bookmark_id}
                  className="rounded border border-[var(--border)] px-2 py-1"
                >
                  <span className="font-medium">{b.label}</span>
                  <span className="ml-1 text-[10px] text-[var(--muted)]">
                    {b.kind}
                  </span>
                </li>
              ))}
              {bookmarks.length === 0 ? (
                <li className="text-xs text-[var(--muted)]">No bookmarks.</li>
              ) : null}
            </ul>
          ) : null}

          {rightTab === "search" ? (
            <div className="space-y-2">
              <Input
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="Full-text search…"
                aria-label="Workspace search"
              />
              <ul className="max-h-64 space-y-1 overflow-auto text-sm">
                {asNotes(searchQuery.data?.result?.notes).map((n) => (
                  <li key={n.note_id}>
                    <button
                      type="button"
                      className="w-full rounded px-2 py-1 text-left hover:bg-[var(--surface-2)]"
                      onClick={() => selectNote(n)}
                    >
                      {n.title}
                    </button>
                  </li>
                ))}
                {searchQ &&
                !searchQuery.isFetching &&
                asNotes(searchQuery.data?.result?.notes).length === 0 ? (
                  <li className="text-xs text-[var(--muted)]">No matches.</li>
                ) : null}
              </ul>
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
