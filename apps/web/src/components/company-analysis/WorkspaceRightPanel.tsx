"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button, Input } from "@/components/ds";
import {
  ANALYSIS_SECTIONS,
  useWorkspacePrefsStore,
} from "@/lib/company-analysis";
import type { ResearchView } from "@/lib/research/mapResearchView";

export function WorkspaceRightPanel({
  view,
  symbol,
}: {
  view: ResearchView | null;
  symbol: string;
}) {
  const notes = useWorkspacePrefsStore((s) => s.notes);
  const tags = useWorkspacePrefsStore((s) => s.tags);
  const addNote = useWorkspacePrefsStore((s) => s.addNote);
  const removeNote = useWorkspacePrefsStore((s) => s.removeNote);
  const addTag = useWorkspacePrefsStore((s) => s.addTag);
  const removeTag = useWorkspacePrefsStore((s) => s.removeTag);
  const setActiveSection = useWorkspacePrefsStore((s) => s.setActiveSection);
  const [noteText, setNoteText] = useState("");
  const [tagText, setTagText] = useState("");

  const sym = symbol.toUpperCase();
  const symbolNotes = notes.filter((n) => n.symbol === sym);
  const symbolTags = tags.filter((t) => t.symbol === sym);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Notes
        </p>
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            addNote(sym, noteText);
            setNoteText("");
          }}
        >
          <Input
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Local note (not synced)"
            aria-label="Add note"
          />
          <Button size="sm" type="submit" variant="secondary">
            Add note
          </Button>
        </form>
        {symbolNotes.length === 0 ? (
          <p className="mt-2 text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {symbolNotes.map((n) => (
              <li
                key={n.id}
                className="rounded-[var(--radius-md)] border border-[var(--border)] p-2 text-xs"
              >
                <p>{n.text}</p>
                <button
                  type="button"
                  className="mt-1 text-[var(--accent)] hover:underline"
                  onClick={() => removeNote(n.id)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Tags
        </p>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            addTag(sym, tagText);
            setTagText("");
          }}
        >
          <Input
            value={tagText}
            onChange={(e) => setTagText(e.target.value)}
            placeholder="Tag"
            aria-label="Add tag"
          />
          <Button size="sm" type="submit" variant="secondary">
            Add
          </Button>
        </form>
        <div className="mt-2 flex flex-wrap gap-1">
          {symbolTags.length === 0 ? (
            <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
          ) : (
            symbolTags.map((t) => (
              <button key={t.id} type="button" onClick={() => removeTag(t.id)}>
                <Badge variant="accent">{t.label} ×</Badge>
              </button>
            ))
          )}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Related reports
        </p>
        {view?.correlationId ? (
          <p className="text-xs text-[var(--muted)]">
            Correlation: {view.correlationId}
          </p>
        ) : (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        )}
        <Link
          href="/reports"
          className="mt-2 inline-block text-sm text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Open reports
        </Link>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Quick navigation
        </p>
        <ul className="space-y-1">
          {ANALYSIS_SECTIONS.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                className="text-sm text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                onClick={() => setActiveSection(s.id)}
              >
                {s.label}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Context actions
        </p>
        <div className="flex flex-col gap-2">
          <Link href={`/research/${encodeURIComponent(sym)}`}>
            <Button size="sm" variant="secondary" className="w-full justify-start">
              Research workspace
            </Button>
          </Link>
          <Link href="/research/institutional">
            <Button size="sm" variant="secondary" className="w-full justify-start">
              Institutional dashboard
            </Button>
          </Link>
          <Link href="/copilot">
            <Button size="sm" variant="secondary" className="w-full justify-start">
              Open Copilot
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
