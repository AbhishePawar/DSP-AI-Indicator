"use client";

/**
 * Research Canvas — Figma Make `ResearchCanvas.tsx` (canvas column · 200px
 * outline panel · block toolbar). Blocks load/save through the authenticated
 * workspace canvas API. Nothing is prefilled: the Figma demo thesis is not
 * copied (CV-001).
 */

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorState } from "@/components/ds";
import { FigmaPage } from "@/components/pages/PagePrimitives";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import type { CanvasBlockPayload, CanvasItem } from "@/lib/api/workspaceTypes";

const BLOCK_TYPES: CanvasBlockPayload["type"][] = [
  "heading",
  "text",
  "metric",
  "table",
  "chart-ref",
  "divider",
];

type DraftBlock = Pick<CanvasBlockPayload, "id" | "type" | "content">;

function fromServer(item: CanvasItem | undefined): DraftBlock[] {
  if (!item) return [];
  return item.blocks.map((block) => ({
    id: block.id,
    type: block.type,
    content: block.content,
  }));
}

function newBlockId(): string {
  return `local-${
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : Date.now().toString(36)
  }`;
}

export function FigmaNotebook() {
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ["workspace-canvases"],
    queryFn: () => api.workspaceCanvases(),
  });
  const current = list.data?.items?.[0];
  const [title, setTitle] = useState<string | null>(null);
  const [blocks, setBlocks] = useState<DraftBlock[] | null>(null);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const viewTitle = title ?? current?.title ?? "Untitled canvas";
  const viewBlocks = blocks ?? fromServer(current);

  const headings = useMemo(
    () => viewBlocks.filter((block) => block.type === "heading" && block.content.trim()),
    [viewBlocks],
  );
  const textBlocks = viewBlocks.filter((block) => block.type === "text");
  const wordCount = textBlocks.reduce(
    (total, block) => total + block.content.split(/\s+/).filter(Boolean).length,
    0,
  );

  const save = useMutation({
    mutationFn: () =>
      api.workspaceCanvasSave({
        title: viewTitle.trim() || "Untitled canvas",
        canvas_id: current?.canvas_id ?? null,
        blocks: viewBlocks.map((block) => ({
          id: block.id,
          type: block.type,
          content: block.content,
          meta: {},
        })),
      }),
    onSuccess: async (res) => {
      setError(null);
      setDirty(false);
      setTitle(res.item.title);
      setBlocks(fromServer(res.item));
      await queryClient.invalidateQueries({ queryKey: ["workspace-canvases"] });
    },
    onError: (err) => {
      setError(err instanceof ApiClientError ? err.message : "Save failed.");
    },
  });

  function mutateBlocks(next: DraftBlock[]) {
    setBlocks(next);
    setDirty(true);
  }

  function update(id: string, content: string) {
    mutateBlocks(viewBlocks.map((block) => (block.id === id ? { ...block, content } : block)));
  }

  function add(type: DraftBlock["type"]) {
    mutateBlocks([...viewBlocks, { id: newBlockId(), type, content: "" }]);
  }

  function remove(id: string) {
    mutateBlocks(viewBlocks.filter((block) => block.id !== id));
  }

  const status = save.isPending
    ? "Saving…"
    : error
      ? error
      : dirty
        ? "Unsaved changes"
        : current || blocks
          ? "✓ Saved"
          : "New canvas";

  return (
    <FigmaPage title="Research Canvas" subtitle="Notebook-style research environment">
      {list.isError ? (
        <ErrorState
          title="Research canvas unavailable"
          description={
            list.error instanceof ApiClientError
              ? list.error.message
              : "The canvas service did not respond."
          }
        />
      ) : (
        <div className="grid min-h-[60vh] grid-cols-1 overflow-hidden rounded-[var(--card-radius)] border border-[var(--border)] bg-[var(--bg)] lg:grid-cols-[minmax(0,1fr)_200px]">
          <div className="overflow-auto px-6 py-8 sm:px-12">
            <div className="mx-auto max-w-[700px]">
              <div className="mb-7 flex flex-wrap items-center justify-between gap-3">
                <p
                  className="font-mono text-[11px] text-[var(--muted)]"
                  role="status"
                  aria-live="polite"
                >
                  {status}
                </p>
                <button
                  type="button"
                  onClick={() => save.mutate()}
                  disabled={save.isPending || list.isLoading}
                  className="min-h-11 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3.5 text-xs text-[var(--fg)] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                >
                  Save canvas
                </button>
              </div>

              <label className="mb-6 block">
                <span className="font-mono text-[10px] uppercase tracking-[0.07em] text-[var(--muted)]">
                  Canvas title
                </span>
                <input
                  value={list.isLoading ? "" : viewTitle}
                  onChange={(event) => {
                    setTitle(event.target.value);
                    setDirty(true);
                  }}
                  disabled={list.isLoading}
                  className="mt-1 w-full border-0 border-b border-[var(--border)] bg-transparent py-1 font-[family-name:var(--font-heading)] text-lg text-[var(--fg)] outline-none focus-visible:border-[var(--accent)]"
                />
              </label>

              {list.isLoading ? (
                <p className="text-sm text-[var(--muted)]">Loading canvas…</p>
              ) : viewBlocks.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">
                  No blocks yet. Add a heading or note below. Nothing is prefilled.
                </p>
              ) : (
                viewBlocks.map((block) => (
                  <div key={block.id} className="group relative mb-4 pl-7">
                    <button
                      type="button"
                      onClick={() => remove(block.id)}
                      aria-label={`Remove ${block.type} block`}
                      className="absolute left-0 top-1 flex h-6 w-6 items-center justify-center rounded text-sm text-[var(--muted)] opacity-60 hover:text-[var(--fg)] focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] group-hover:opacity-100"
                    >
                      ×
                    </button>
                    <BlockEditor block={block} onChange={(content) => update(block.id, content)} />
                  </div>
                ))
              )}

              <div className="mt-6 flex flex-wrap gap-2 border-t border-[var(--border)] pt-6">
                {BLOCK_TYPES.map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => add(type)}
                    disabled={list.isLoading}
                    className="min-h-11 rounded-lg border border-[var(--border)] px-3 font-mono text-xs text-[var(--muted)] transition-colors hover:border-[var(--c-dsp)] hover:text-[var(--c-dsp)] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  >
                    + {type}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <aside
            aria-label="Canvas outline"
            className="border-t border-[var(--border)] bg-[var(--surface)] px-4 py-5 lg:border-l lg:border-t-0"
          >
            <p className="mb-3.5 font-mono text-[11px] uppercase tracking-[0.07em] text-[var(--muted)]">
              Outline
            </p>
            {headings.length === 0 ? (
              <p className="text-xs text-[var(--muted)]">No headings yet.</p>
            ) : (
              <ul className="space-y-1">
                {headings.map((heading) => (
                  <li key={heading.id} className="text-xs leading-snug text-[var(--muted)]">
                    {heading.content}
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-6 border-t border-[var(--border)] pt-5">
              <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.07em] text-[var(--muted)]">
                Info
              </p>
              <dl className="space-y-1 text-xs leading-relaxed text-[var(--muted)]">
                <div>{viewBlocks.length} blocks</div>
                <div>{textBlocks.length} text sections</div>
                <div>~{wordCount} words</div>
                {current?.updated_at ? (
                  <div className="font-mono text-[10px]">
                    Updated {new Date(current.updated_at).toLocaleString()}
                  </div>
                ) : null}
              </dl>
            </div>
          </aside>
        </div>
      )}
    </FigmaPage>
  );
}

function BlockEditor({
  block,
  onChange,
}: {
  block: DraftBlock;
  onChange: (content: string) => void;
}) {
  const base =
    "w-full border-0 bg-transparent p-0 outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-sm";
  switch (block.type) {
    case "heading":
      return (
        <input
          aria-label="Heading"
          value={block.content}
          onChange={(event) => onChange(event.target.value)}
          placeholder="New section"
          className={`${base} font-[family-name:var(--font-heading)] text-[22px] font-medium text-[var(--fg)]`}
        />
      );
    case "text":
      return (
        <textarea
          aria-label="Note"
          value={block.content}
          onChange={(event) => onChange(event.target.value)}
          rows={3}
          className={`${base} resize-y text-sm leading-[1.7] text-[var(--fg)]`}
        />
      );
    case "metric":
      return (
        <div className="rounded-[10px] border border-[var(--border)] border-l-[3px] border-l-[var(--c-dsp)] bg-[var(--surface-2)] px-4 py-3">
          <input
            aria-label="Metric note"
            value={block.content}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Metric: value"
            className={`${base} font-mono text-[13px] text-[var(--c-dsp)]`}
          />
        </div>
      );
    case "table":
      return (
        <textarea
          aria-label="Table (markdown)"
          value={block.content}
          onChange={(event) => onChange(event.target.value)}
          rows={4}
          placeholder="| Metric | Value |"
          className={`${base} rounded-[10px] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 font-mono text-xs text-[var(--fg)]`}
        />
      );
    case "chart-ref":
      return (
        <div className="rounded-[10px] border border-dashed border-[var(--border)] bg-[var(--surface-2)] p-5 text-center font-mono text-xs text-[var(--muted)]">
          Chart placeholder — charts render only from analysis data.
        </div>
      );
    case "divider":
    default:
      return <hr className="my-2 border-t border-[var(--border)]" />;
  }
}
