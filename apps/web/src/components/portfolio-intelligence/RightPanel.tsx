"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button, Input } from "@/components/ds";
import {
  PORTFOLIO_SECTIONS,
  usePortfolioIntelPrefsStore,
} from "@/lib/portfolio-intelligence";
import type { PortfolioActivity, PortfolioHolding } from "@/lib/portfolio/model";

export function PortfolioRightPanel({
  holdings,
  activities,
}: {
  holdings: PortfolioHolding[];
  activities: PortfolioActivity[];
}) {
  const portfolioId = usePortfolioIntelPrefsStore((s) => s.activePortfolioId);
  const notes = usePortfolioIntelPrefsStore((s) => s.notes);
  const tags = usePortfolioIntelPrefsStore((s) => s.tags);
  const addNote = usePortfolioIntelPrefsStore((s) => s.addNote);
  const removeNote = usePortfolioIntelPrefsStore((s) => s.removeNote);
  const addTag = usePortfolioIntelPrefsStore((s) => s.addTag);
  const removeTag = usePortfolioIntelPrefsStore((s) => s.removeTag);
  const setActiveSection = usePortfolioIntelPrefsStore((s) => s.setActiveSection);
  const [noteText, setNoteText] = useState("");
  const [tagText, setTagText] = useState("");

  const symbolNotes = notes.filter((n) => n.portfolioId === portfolioId);
  const symbolTags = tags.filter((t) => t.portfolioId === portfolioId);

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
            addNote(portfolioId, noteText);
            setNoteText("");
          }}
        >
          <Input
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Local note"
            aria-label="Add portfolio note"
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
            addTag(portfolioId, tagText);
            setTagText("");
          }}
        >
          <Input
            value={tagText}
            onChange={(e) => setTagText(e.target.value)}
            placeholder="Tag"
            aria-label="Add portfolio tag"
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
          Quick actions
        </p>
        <div className="flex flex-col gap-2">
          <Button
            size="sm"
            variant="secondary"
            className="justify-start"
            onClick={() => setActiveSection("holdings")}
          >
            View holdings
          </Button>
          <Link href="/analysis">
            <Button size="sm" variant="secondary" className="w-full justify-start">
              Analyze company
            </Button>
          </Link>
          <Link href="/research">
            <Button size="sm" variant="secondary" className="w-full justify-start">
              Research workspace
            </Button>
          </Link>
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Related companies
        </p>
        {holdings.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1">
            {holdings.slice(0, 8).map((h) => (
              <li key={h.ticker}>
                <Link
                  href={`/analysis?symbol=${encodeURIComponent(h.ticker)}`}
                  className="text-sm text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                >
                  {h.ticker}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Recent activity
        </p>
        {activities.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-2 text-xs">
            {activities.slice(0, 6).map((a) => (
              <li key={a.id}>
                <p>{a.label}</p>
                <p className="text-[var(--muted)]">
                  {new Date(a.timestamp).toLocaleString()}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Sections
        </p>
        <ul className="space-y-1">
          {PORTFOLIO_SECTIONS.map((s) => (
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
