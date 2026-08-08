"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button, Input } from "@/components/ds";
import {
  RESEARCH_SECTIONS,
  useResearchWorkspacePrefsStore,
} from "@/lib/research-workspace";
import type { ResearchView } from "@/lib/research/mapResearchView";

export function ResearchRightPanel({
  view,
  ticker,
}: {
  view: ResearchView | null;
  ticker: string | null;
}) {
  const notes = useResearchWorkspacePrefsStore((s) => s.notes);
  const tags = useResearchWorkspacePrefsStore((s) => s.tags);
  const addNote = useResearchWorkspacePrefsStore((s) => s.addNote);
  const removeNote = useResearchWorkspacePrefsStore((s) => s.removeNote);
  const addTag = useResearchWorkspacePrefsStore((s) => s.addTag);
  const removeTag = useResearchWorkspacePrefsStore((s) => s.removeTag);
  const setActiveSection = useResearchWorkspacePrefsStore(
    (s) => s.setActiveSection,
  );
  const favourites = useResearchWorkspacePrefsStore((s) => s.favourites);
  const [noteText, setNoteText] = useState("");
  const [tagText, setTagText] = useState("");

  const sym = (ticker || "").toUpperCase();
  const symbolNotes = notes.filter((n) => n.ticker === sym);
  const symbolTags = tags.filter((t) => t.ticker === sym);

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
            if (!sym) return;
            addNote(sym, noteText);
            setNoteText("");
          }}
        >
          <Input
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Local note"
            aria-label="Add research note"
            disabled={!sym}
          />
          <Button size="sm" type="submit" variant="secondary" disabled={!sym}>
            Add note
          </Button>
        </form>
        {!sym || symbolNotes.length === 0 ? (
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
            if (!sym) return;
            addTag(sym, tagText);
            setTagText("");
          }}
        >
          <Input
            value={tagText}
            onChange={(e) => setTagText(e.target.value)}
            placeholder="Tag"
            aria-label="Add research tag"
            disabled={!sym}
          />
          <Button size="sm" type="submit" variant="secondary" disabled={!sym}>
            Add
          </Button>
        </form>
        <div className="mt-2 flex flex-wrap gap-1">
          {!sym || symbolTags.length === 0 ? (
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
          Related research
        </p>
        {favourites.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {favourites.slice(0, 6).map((f) => (
              <li key={f.ticker}>
                <Link
                  href={`/research/${encodeURIComponent(f.ticker)}`}
                  className="text-[var(--accent)] hover:underline"
                >
                  {f.ticker}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Related companies
        </p>
        {view ? (
          <Link
            href={`/analysis?symbol=${encodeURIComponent(view.ticker)}`}
            className="text-sm text-[var(--accent)] hover:underline"
          >
            {view.ticker} · {view.company}
          </Link>
        ) : (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Quick actions
        </p>
        <div className="flex flex-col gap-2">
          <Button
            size="sm"
            variant="secondary"
            className="justify-start"
            onClick={() => setActiveSection("viewer")}
          >
            Open viewer
          </Button>
          <Link href="/copilot">
            <Button size="sm" variant="secondary" className="w-full justify-start">
              Open Copilot
            </Button>
          </Link>
          <Link href="/research/institutional">
            <Button size="sm" variant="secondary" className="w-full justify-start">
              Institutional dashboard
            </Button>
          </Link>
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Sections
        </p>
        <ul className="space-y-1">
          {RESEARCH_SECTIONS.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                className="text-sm text-[var(--accent)] hover:underline"
                onClick={() => setActiveSection(s.id)}
              >
                {s.label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
