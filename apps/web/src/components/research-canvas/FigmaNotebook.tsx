"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button, ErrorState } from "@/components/ds";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import type { CanvasItem } from "@/lib/api/workspaceTypes";

const BLOCK_TYPES = ["heading", "text", "metric", "divider"] as const;

type DraftBlock = {
  id: string;
  type: (typeof BLOCK_TYPES)[number] | "chart-ref" | "table";
  content: string;
};

function fromServer(item: CanvasItem | undefined): DraftBlock[] {
  if (!item) return [];
  return item.blocks.map((block) => ({
    id: block.id,
    type: block.type,
    content: block.content,
  }));
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
  const [message, setMessage] = useState<string | null>(null);

  const viewTitle = title ?? current?.title ?? "Untitled canvas";
  const viewBlocks = blocks ?? fromServer(current);

  const headings = useMemo(
    () => viewBlocks.filter((block) => block.type === "heading" && block.content.trim()),
    [viewBlocks],
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
      setMessage("Saved.");
      setTitle(res.item.title);
      setBlocks(fromServer(res.item));
      await queryClient.invalidateQueries({ queryKey: ["workspace-canvases"] });
    },
    onError: (error) => {
      setMessage(error instanceof ApiClientError ? error.message : "Save failed.");
    },
  });

  function update(id: string, content: string) {
    setBlocks(viewBlocks.map((block) => (block.id === id ? { ...block, content } : block)));
  }

  function add(type: DraftBlock["type"]) {
    const block: DraftBlock = {
      id: `local-${crypto.randomUUID()}`,
      type,
      content: type === "divider" ? "" : "",
    };
    setBlocks([...viewBlocks, block]);
  }

  if (list.isError) {
    return (
      <ErrorState
        title="Research canvas unavailable"
        description={
          list.error instanceof ApiClientError
            ? list.error.message
            : "The canvas service did not respond."
        }
      />
    );
  }

  return (
    <section aria-labelledby="figma-canvas-title" className="space-y-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2
            id="figma-canvas-title"
            className="font-[family-name:var(--font-heading)] text-2xl font-medium text-[var(--fg)]"
          >
            Research Canvas
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Notebook-style research environment
          </p>
        </div>
        <Button type="button" onClick={() => save.mutate()} disabled={save.isPending || list.isLoading}>
          {save.isPending ? "Saving…" : "Save"}
        </Button>
      </header>
      {message ? <p className="text-sm text-[var(--muted)]">{message}</p> : null}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_220px]">
        <div className="space-y-3 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <label className="block text-xs text-[var(--muted)]" htmlFor="canvas-title">
            Title
          </label>
          <input
            id="canvas-title"
            value={list.isLoading ? "" : viewTitle}
            onChange={(event) => setTitle(event.target.value)}
            className="w-full rounded-[10px] border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--fg)]"
          />
          {list.isLoading ? (
            <p className="text-sm text-[var(--muted)]">Loading canvas…</p>
          ) : viewBlocks.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">
              No blocks yet. Add a heading or note. Nothing is prefilled.
            </p>
          ) : (
            viewBlocks.map((block) => (
              <BlockEditor key={block.id} block={block} onChange={(content) => update(block.id, content)} />
            ))
          )}
          <div className="flex flex-wrap gap-2 pt-2">
            {BLOCK_TYPES.map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => add(type)}
                className="min-h-11 rounded-full border border-[var(--border)] px-3 text-xs capitalize text-[var(--fg)]"
              >
                Add {type}
              </button>
            ))}
          </div>
        </div>
        <aside className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Outline</h3>
          {headings.length === 0 ? (
            <p className="mt-3 text-sm text-[var(--muted)]">No headings yet.</p>
          ) : (
            <ul className="mt-3 space-y-2 text-sm text-[var(--fg)]">
              {headings.map((heading) => (
                <li key={heading.id}>{heading.content}</li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </section>
  );
}

function BlockEditor({
  block,
  onChange,
}: {
  block: DraftBlock;
  onChange: (content: string) => void;
}) {
  if (block.type === "divider") {
    return <hr className="border-[var(--border)]" />;
  }
  const label = block.type === "heading" ? "Heading" : block.type === "metric" ? "Metric note" : "Note";
  return (
    <label className="block space-y-1">
      <span className="text-xs text-[var(--muted)]">{label}</span>
      <textarea
        value={block.content}
        onChange={(event) => onChange(event.target.value)}
        rows={block.type === "heading" ? 1 : 3}
        className="w-full rounded-[10px] border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--fg)]"
      />
    </label>
  );
}
