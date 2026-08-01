"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button, Input } from "@/components/ds";
import {
  REPORT_SECTIONS,
  useInstitutionalReportsPrefsStore,
  type ReportMode,
} from "@/lib/institutional-reports";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { cn } from "@/lib/utils";

const MODES: { id: ReportMode; label: string }[] = [
  { id: "interactive", label: "Interactive" },
  { id: "print", label: "Print" },
  { id: "pdf", label: "PDF" },
];

export function ReportsRightPanel({
  view,
  symbol,
}: {
  view: ResearchView | null;
  symbol: string;
}) {
  const notes = useInstitutionalReportsPrefsStore((s) => s.notes);
  const tags = useInstitutionalReportsPrefsStore((s) => s.tags);
  const addNote = useInstitutionalReportsPrefsStore((s) => s.addNote);
  const removeNote = useInstitutionalReportsPrefsStore((s) => s.removeNote);
  const addTag = useInstitutionalReportsPrefsStore((s) => s.addTag);
  const removeTag = useInstitutionalReportsPrefsStore((s) => s.removeTag);
  const setActiveSection = useInstitutionalReportsPrefsStore(
    (s) => s.setActiveSection,
  );
  const reportMode = useInstitutionalReportsPrefsStore((s) => s.reportMode);
  const setReportMode = useInstitutionalReportsPrefsStore(
    (s) => s.setReportMode,
  );
  const [noteText, setNoteText] = useState("");
  const [tagText, setTagText] = useState("");

  const sym = symbol.toUpperCase();
  const symbolNotes = notes.filter((n) => n.symbol === sym);
  const symbolTags = tags.filter((t) => t.symbol === sym);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3 print:hidden">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Report mode
        </p>
        <div
          className="flex flex-wrap gap-1"
          role="group"
          aria-label="Report display mode"
        >
          {MODES.map((mode) => (
            <button
              key={mode.id}
              type="button"
              onClick={() => setReportMode(mode.id)}
              aria-pressed={reportMode === mode.id}
              className={cn(
                "rounded-[var(--radius-md)] border border-[var(--border)] px-2 py-1 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                reportMode === mode.id
                  ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                  : "hover:bg-[var(--surface-2)]",
              )}
            >
              {mode.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[10px] text-[var(--muted)]">
          Print / PDF use browser print CSS — no fabricated PDF engine.
        </p>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Snapshot
        </p>
        {view ? (
          <dl className="space-y-1 text-xs">
            <div className="flex justify-between gap-2">
              <dt className="text-[var(--muted)]">Ticker</dt>
              <dd className="font-medium">{view.ticker}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-[var(--muted)]">Status</dt>
              <dd>
                <Badge variant={view.ok ? "accent" : "outline"}>
                  {view.ok ? "OK" : "Incomplete"}
                </Badge>
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-[var(--muted)]">Recommendation</dt>
              <dd className="max-w-[9rem] truncate text-right font-medium">
                {view.recommendation}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Notes
        </p>
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            addNote(symbol, noteText);
            setNoteText("");
          }}
        >
          <Input
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Local note"
            aria-label="Add report note"
          />
          <Button size="sm" type="submit" variant="secondary">
            Add note
          </Button>
        </form>
        {symbolNotes.length === 0 ? (
          <p className="mt-2 text-xs text-[var(--muted)]">No notes yet.</p>
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
            addTag(symbol, tagText);
            setTagText("");
          }}
        >
          <Input
            value={tagText}
            onChange={(e) => setTagText(e.target.value)}
            placeholder="Tag"
            aria-label="Add report tag"
          />
          <Button size="sm" type="submit" variant="secondary">
            Add
          </Button>
        </form>
        <div className="mt-2 flex flex-wrap gap-1">
          {symbolTags.length === 0 ? (
            <p className="text-xs text-[var(--muted)]">No tags yet.</p>
          ) : (
            symbolTags.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => removeTag(t.id)}
                className="rounded-[var(--radius-md)] bg-[var(--surface-2)] px-2 py-0.5 text-[10px]"
                aria-label={`Remove tag ${t.label}`}
              >
                {t.label} ×
              </button>
            ))
          )}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Quick links
        </p>
        <ul className="space-y-1 text-xs">
          <li>
            <button
              type="button"
              className="text-[var(--accent)] hover:underline"
              onClick={() => setActiveSection("explainability")}
            >
              {REPORT_SECTIONS.find((s) => s.id === "explainability")?.label}
            </button>
          </li>
          <li>
            <button
              type="button"
              className="text-[var(--accent)] hover:underline"
              onClick={() => setActiveSection("export")}
            >
              Downloads
            </button>
          </li>
          <li>
            <Link
              href={`/analysis?symbol=${encodeURIComponent(symbol)}`}
              className="text-[var(--accent)] hover:underline"
            >
              Company analysis workspace
            </Link>
          </li>
          <li>
            <Link
              href={`/research/${encodeURIComponent(symbol)}`}
              className="text-[var(--accent)] hover:underline"
            >
              Classic research page
            </Link>
          </li>
          <li>
            <Link
              href="/research/institutional/dashboard"
              className="text-[var(--accent)] hover:underline"
            >
              RS-001…RS-010 standards dashboard
            </Link>
          </li>
        </ul>
      </div>
    </div>
  );
}
