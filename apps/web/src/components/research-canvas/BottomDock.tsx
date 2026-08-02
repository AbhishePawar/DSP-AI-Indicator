"use client";

import Link from "next/link";
import { useMemo } from "react";

import { Button } from "@/components/ds";
import {
  composeResearchTimeline,
  useResearchNotebookStore,
} from "@/lib/research-canvas";
import { useComparisonPrefsStore } from "@/lib/company-comparison";
import { SectionCard } from "./Primitives";

export function CanvasBottomDock({ symbol }: { symbol: string | null }) {
  const entries = useResearchNotebookStore((s) => s.entries);
  const savedSessions = useResearchNotebookStore((s) => s.savedSessions);
  const savedComparisons = useComparisonPrefsStore((s) => s.saved);

  const timeline = useMemo(
    () =>
      composeResearchTimeline({
        symbol,
        notebookEntries: entries,
        savedSessions,
        comparisonEvents: savedComparisons.map((c) => ({
          id: c.id,
          at: c.savedAt,
          title: c.title,
          symbols: c.symbols,
          href: `/analysis/compare?symbols=${encodeURIComponent(c.symbols.join(","))}`,
        })),
      }).slice(0, 12),
    [entries, savedComparisons, savedSessions, symbol],
  );

  const analysisHref = symbol
    ? `/analysis?symbol=${encodeURIComponent(symbol)}`
    : "/analysis";

  return (
    <div
      aria-label="Research bottom dock"
      className="grid gap-3 border-t border-[var(--border)] bg-[var(--surface)] p-3 md:grid-cols-2 xl:grid-cols-4"
    >
      <SectionCard title="Timeline" description="Local + available history">
        <ul className="max-h-40 space-y-2 overflow-y-auto text-sm">
          {timeline.map((ev) => (
            <li key={ev.id}>
              {ev.href ? (
                <Link
                  href={ev.href}
                  className="text-[var(--accent)] hover:underline"
                >
                  {ev.title}
                </Link>
              ) : (
                <span>{ev.title}</span>
              )}
              <p className="text-xs text-[var(--muted)]">{ev.detail}</p>
            </li>
          ))}
        </ul>
      </SectionCard>

      <SectionCard title="Committee" description="AI Committee surface">
        <p className="text-sm text-[var(--muted)]">
          Committee outputs come from Company Analysis — not recalculated here.
        </p>
        <Link href={`${analysisHref}&section=ai`} className="mt-2 inline-block">
          <Button size="sm" variant="secondary">
            Open committee
          </Button>
        </Link>
      </SectionCard>

      <SectionCard title="Version History" description="Research versions">
        <p className="text-sm text-[var(--muted)]">
          Data unavailable. Version diffs require Research Archive / Diff APIs —
          open Research Workspace archive when linked.
        </p>
        <Link href="/research?section=archive" className="mt-2 inline-block">
          <Button size="sm" variant="ghost">
            Research archive
          </Button>
        </Link>
      </SectionCard>

      <SectionCard title="Supporting Evidence">
        <p className="text-sm text-[var(--muted)]">
          Evidence chain is institutional — open Company Analysis Evidence.
        </p>
        <Link
          href={`${analysisHref}&section=evidence`}
          className="mt-2 inline-block"
        >
          <Button size="sm" variant="secondary">
            Open evidence
          </Button>
        </Link>
      </SectionCard>
    </div>
  );
}
