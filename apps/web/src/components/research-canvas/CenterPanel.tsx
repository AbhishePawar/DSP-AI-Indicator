"use client";

import Link from "next/link";
import { useMemo } from "react";

import { Badge, Button } from "@/components/ds";
import { featureFlags } from "@/lib/featureFlags";
import {
  CANVAS_TABS,
  composeResearchTimeline,
  searchResearchCanvas,
  useResearchNotebookStore,
  type CanvasTabId,
} from "@/lib/research-canvas";
import { useComparisonPrefsStore } from "@/lib/company-comparison";
import { cn } from "@/lib/utils";
import { SectionCard, WorkspaceEmpty } from "./Primitives";
import { CanvasRightNotebook } from "./RightNotebook";

export function CanvasCenterPanel({
  symbol,
  activeTab,
  onSelectTab,
  searchQuery,
}: {
  symbol: string | null;
  activeTab: CanvasTabId;
  onSelectTab: (id: CanvasTabId) => void;
  searchQuery: string;
}) {
  const entries = useResearchNotebookStore((s) => s.entries);
  const saved = useComparisonPrefsStore((s) => s.saved);

  const visibleTabs = useMemo(
    () =>
      CANVAS_TABS.filter((t) => {
        if (
          t.requiresFlag === "researchIntelligence" &&
          !featureFlags.researchIntelligence
        ) {
          return false;
        }
        if (
          t.requiresFlag === "companyComparison" &&
          !featureFlags.companyComparison
        ) {
          return false;
        }
        return true;
      }),
    [],
  );

  const activeMeta =
    visibleTabs.find((t) => t.id === activeTab) ?? visibleTabs[0];
  const deepLink = activeMeta.href(symbol);

  const searchHits = useMemo(
    () =>
      searchResearchCanvas({
        query: searchQuery,
        notebookEntries: entries,
        savedComparisonTitles: saved.map((c) => ({
          title: c.title,
          symbols: c.symbols,
          href: `/analysis/compare?symbols=${encodeURIComponent(c.symbols.join(","))}`,
        })),
      }),
    [entries, saved, searchQuery],
  );

  const timeline = useMemo(
    () =>
      composeResearchTimeline({
        symbol,
        notebookEntries: entries,
      }).slice(0, 8),
    [entries, symbol],
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        role="tablist"
        aria-label="Research workspace tabs"
        className="flex flex-wrap gap-1 border-b border-[var(--border)] bg-[var(--surface)] px-2 py-2"
      >
        {visibleTabs.map((tab) => {
          const selected = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={selected}
              id={`canvas-tab-${tab.id}`}
              className={cn(
                "min-h-11 rounded-md px-3 py-1.5 text-sm transition-colors motion-reduce:transition-none",
                selected
                  ? "bg-[var(--accent)] text-[var(--accent-fg,white)]"
                  : "text-[var(--muted)] hover:bg-[var(--surface-2,var(--border))]",
              )}
              onClick={() => onSelectTab(tab.id)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        aria-labelledby={`canvas-tab-${activeTab}`}
        className="flex-1 overflow-y-auto p-3"
      >
        {searchQuery.trim() ? (
          <SectionCard
            title="Search results"
            description="Client-side over available data — no fabricated rankings"
          >
            {searchHits.length === 0 ? (
              <WorkspaceEmpty description="No matches in available companies, notes, reports, or tabs." />
            ) : (
              <ul className="space-y-2 text-sm">
                {searchHits.map((hit) => (
                  <li key={hit.id} className="flex justify-between gap-3">
                    <div>
                      <Badge variant="outline" className="mr-2">
                        {hit.group}
                      </Badge>
                      <Link
                        href={hit.href}
                        className="text-[var(--accent)] hover:underline"
                      >
                        {hit.label}
                      </Link>
                      {hit.detail ? (
                        <p className="text-xs text-[var(--muted)]">{hit.detail}</p>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>
        ) : null}

        {activeTab === "notes" ? (
          <div className="lg:hidden">
            <CanvasRightNotebook symbol={symbol} />
          </div>
        ) : null}

        {activeTab === "timeline" ? (
          <SectionCard
            title="Research Timeline"
            description="Combined local history — RI / confidence evolution when feeds exist"
          >
            <ul className="space-y-2 text-sm">
              {timeline.map((ev) => (
                <li
                  key={ev.id}
                  className="border-b border-[var(--border)] pb-2 last:border-0"
                >
                  <div className="flex justify-between gap-2">
                    <span className="font-medium">{ev.title}</span>
                    <span className="text-xs text-[var(--muted)]">
                      {ev.at === new Date(0).toISOString()
                        ? "Data unavailable."
                        : new Date(ev.at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-[var(--muted)]">{ev.detail}</p>
                  {ev.href ? (
                    <Link
                      href={ev.href}
                      className="text-xs text-[var(--accent)] hover:underline"
                    >
                      Open
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          </SectionCard>
        ) : (
          <SectionCard
            title={activeMeta.label}
            description={activeMeta.description}
            action={
              <Badge variant="outline">
                {symbol ?? "No symbol"}
              </Badge>
            }
          >
            <p className="text-sm text-[var(--muted)]">
              Canvas composes existing institutional surfaces. Analytical engines
              remain unchanged — open the linked workspace for full interactive
              research.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href={deepLink}>
                <Button className="min-h-11">Open {activeMeta.label}</Button>
              </Link>
              {symbol ? (
                <Link href={`/analysis?symbol=${encodeURIComponent(symbol)}`}>
                  <Button className="min-h-11" variant="secondary">
                    Company Analysis
                  </Button>
                </Link>
              ) : null}
              {featureFlags.companyComparison ? (
                <Link
                  href={
                    symbol
                      ? `/analysis/compare?symbols=${encodeURIComponent(symbol)}`
                      : "/analysis/compare"
                  }
                >
                  <Button className="min-h-11" variant="ghost">
                    Comparison
                  </Button>
                </Link>
              ) : null}
              {featureFlags.researchIntelligence ? (
                <Link
                  href={
                    symbol
                      ? `/research/intelligence?symbol=${encodeURIComponent(symbol)}`
                      : "/research/intelligence"
                  }
                >
                  <Button className="min-h-11" variant="ghost">
                    Research Intelligence
                  </Button>
                </Link>
              ) : null}
            </div>
            <dl className="mt-4">
              <div className="flex justify-between gap-4 border-b border-[var(--border)] py-2 text-sm">
                <dt className="text-[var(--muted)]">Deep link</dt>
                <dd className="truncate text-right font-mono text-xs">
                  {deepLink}
                </dd>
              </div>
              <div className="flex justify-between gap-4 py-2 text-sm">
                <dt className="text-[var(--muted)]">Composition mode</dt>
                <dd>Embed via navigation — no engine rewrite</dd>
              </div>
            </dl>
          </SectionCard>
        )}
      </div>
    </div>
  );
}
