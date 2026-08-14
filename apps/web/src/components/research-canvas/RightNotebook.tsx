"use client";

import { useMemo, useState } from "react";

import { Button, Input, Textarea } from "@/components/ds";
import {
  NOTEBOOK_KIND_LABELS,
  NOTEBOOK_KINDS,
  useResearchNotebookStore,
  type NotebookEntryKind,
} from "@/lib/research-canvas";
import { SectionCard } from "./Primitives";

export function CanvasRightNotebook({ symbol }: { symbol: string | null }) {
  const entries = useResearchNotebookStore((s) => s.entries);
  const addEntry = useResearchNotebookStore((s) => s.addEntry);
  const removeEntry = useResearchNotebookStore((s) => s.removeEntry);
  const toggleBookmarkEntry = useResearchNotebookStore(
    (s) => s.toggleBookmarkEntry,
  );
  const addBookmark = useResearchNotebookStore((s) => s.addBookmark);

  const [kind, setKind] = useState<NotebookEntryKind>("note");
  const [text, setText] = useState("");

  const filtered = useMemo(() => {
    if (!symbol) return entries.slice(0, 40);
    const sym = symbol.toUpperCase();
    return entries
      .filter((e) => !e.symbol || e.symbol === sym)
      .slice(0, 40);
  }, [entries, symbol]);

  const thesis = filtered.filter((e) => e.kind === "thesis");
  const questions = filtered.filter((e) => e.kind === "question");
  const actions = filtered.filter((e) => e.kind === "action");

  function submit() {
    addEntry(kind, text, symbol);
    setText("");
  }

  return (
    <aside
      aria-label="Research Notebook"
      className="flex h-full flex-col gap-3 overflow-y-auto p-3"
    >
      <SectionCard
        title="Research Notebook"
        description="User-authored only — never overwrites institutional research"
      >
        <p className="mb-2 text-xs text-[var(--muted)]">
          Personal workspace. Not sent to /analyse. CV-001 honesty preserved for
          system research.
        </p>
        <label className="block text-xs text-[var(--muted)]" htmlFor="nb-kind">
          Entry type
        </label>
        <select
          id="nb-kind"
          className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 text-sm"
          value={kind}
          onChange={(e) => setKind(e.target.value as NotebookEntryKind)}
        >
          {NOTEBOOK_KINDS.map((k) => (
            <option key={k} value={k}>
              {NOTEBOOK_KIND_LABELS[k]}
            </option>
          ))}
        </select>
        <Textarea
          className="mt-2 min-h-24"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Capture thesis, questions, risks, catalysts…"
          aria-label="Notebook entry text"
        />
        <Button className="mt-2 min-h-11 w-full" onClick={submit} disabled={!text.trim()}>
          Add entry
        </Button>
      </SectionCard>

      <SectionCard title="Thesis">
        {thesis.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {thesis.map((e) => (
              <li key={e.id} className="border-b border-[var(--border)] pb-2">
                {e.text}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Questions">
        {questions.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {questions.map((e) => (
              <li key={e.id}>{e.text}</li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Action Items">
        {actions.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {actions.map((e) => (
              <li key={e.id} className="flex justify-between gap-2">
                <span>{e.text}</span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => removeEntry(e.id)}
                  aria-label="Remove action item"
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="All entries">
        {filtered.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {filtered.map((e) => (
              <li
                key={e.id}
                className="rounded-md border border-[var(--border)] p-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-medium uppercase text-[var(--muted)]">
                    {NOTEBOOK_KIND_LABELS[e.kind]}
                    {e.symbol ? ` · ${e.symbol}` : ""}
                  </span>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => toggleBookmarkEntry(e.id)}
                      aria-label={e.bookmarked ? "Unpin entry" : "Bookmark entry"}
                    >
                      {e.bookmarked ? "Pinned" : "Pin"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeEntry(e.id)}
                      aria-label="Remove notebook entry"
                    >
                      ×
                    </Button>
                  </div>
                </div>
                <p className="mt-1">{e.text}</p>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Bookmarks">
        <div className="flex gap-2">
          <Input
            id="bm-label"
            placeholder="Bookmark label"
            aria-label="Bookmark label"
            className="min-h-11"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const label = (e.target as HTMLInputElement).value;
                const href = symbol
                  ? `/research/canvas?symbol=${encodeURIComponent(symbol)}`
                  : "/research/canvas";
                addBookmark(label, href);
                (e.target as HTMLInputElement).value = "";
              }
            }}
          />
        </div>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Press Enter to bookmark the active canvas context.
        </p>
      </SectionCard>
    </aside>
  );
}
