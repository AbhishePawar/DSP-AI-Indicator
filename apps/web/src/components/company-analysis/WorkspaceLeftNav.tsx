"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge, Button } from "@/components/ds";
import { ANALYSIS_SECTIONS, useWorkspacePrefsStore } from "@/lib/company-analysis";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import type { SecurityListingView } from "@/lib/securities/identity";
import { cn } from "@/lib/utils";

export function WorkspaceLeftNav({
  symbol,
  onSelectSymbol,
  onAnalyze,
  analyzing,
  identityLabel,
}: {
  symbol: string;
  onSelectSymbol: (next: SecurityListingView | string) => void;
  onAnalyze: () => void;
  analyzing: boolean;
  identityLabel?: string | null;
}) {
  const activeSection = useWorkspacePrefsStore((s) => s.activeSection);
  const setActiveSection = useWorkspacePrefsStore((s) => s.setActiveSection);
  const pinned = useDashboardPrefsStore((s) => s.pinnedCompanies);
  const recentSearches = useDashboardPrefsStore((s) => s.recentSearches);
  const pinCompany = useDashboardPrefsStore((s) => s.pinCompany);
  const isPinned = useDashboardPrefsStore((s) => s.isPinned);
  const [recent, setRecent] = useState<RecentAnalysisEntry[]>([]);

  useEffect(() => {
    setRecent(loadRecentAnalyses());
  }, [symbol, analyzing]);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <div>
        {identityLabel ? (
          <p className="mb-2 font-mono text-[11px] text-[var(--muted)]">
            {identityLabel}
          </p>
        ) : (
          <p className="mb-2 text-xs text-[var(--muted)]">
            Use Company Research in the main pane to identify a listing.
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button className="min-h-11" onClick={onAnalyze} disabled={analyzing}>
            {analyzing ? "Analyzing…" : "Analyze"}
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={!symbol || isPinned(symbol)}
            onClick={() => pinCompany(symbol)}
          >
            Pin
          </Button>
        </div>
      </div>

      <nav aria-label="Analysis sections">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Workspace
        </p>
        <ul className="space-y-0.5">
          {ANALYSIS_SECTIONS.filter((s) =>
            [
              "summary",
              "valuation",
              "quality",
              "management",
              "moat",
              "risk",
              "advancedCheck",
              "financial",
              "ownership",
              "peers",
              "ai",
              "copilot",
              "explainability",
              "evidence",
              "timeline",
              "documents",
              "news",
              "export",
              "settings",
            ].includes(s.id),
          ).map((section) => (
            <li key={section.id}>
              <button
                type="button"
                onClick={() => setActiveSection(section.id)}
                aria-current={activeSection === section.id ? "page" : undefined}
                className={cn(
                  "flex w-full items-center justify-between rounded-[var(--radius-md)] px-2 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                  activeSection === section.id
                    ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
                )}
              >
                <span>{section.label}</span>
                <kbd className="font-mono text-[10px] opacity-70">
                  {section.shortcut}
                </kbd>
              </button>
            </li>
          ))}
        </ul>
        <p className="mb-2 mt-4 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Deep dive
        </p>
        <ul className="space-y-0.5">
          {ANALYSIS_SECTIONS.filter((s) =>
            [
              "ratings",
              "valuationTransparency",
              "research",
              "buffett",
              "compliance",
            ].includes(s.id),
          ).map((section) => (
            <li key={section.id}>
              <button
                type="button"
                onClick={() => setActiveSection(section.id)}
                aria-current={activeSection === section.id ? "page" : undefined}
                className={cn(
                  "flex w-full items-center justify-between rounded-[var(--radius-md)] px-2 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                  activeSection === section.id
                    ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
                )}
              >
                <span>{section.label}</span>
                <kbd className="font-mono text-[10px] opacity-70">
                  {section.shortcut}
                </kbd>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Recent companies
        </p>
        {recent.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1">
            {recent.slice(0, 6).map((entry) => (
              <li key={`${entry.ticker}-${entry.analysedAt}`}>
                <button
                  type="button"
                  className="w-full truncate rounded-[var(--radius-md)] px-2 py-1 text-left text-sm hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  onClick={() => onSelectSymbol(entry.ticker)}
                >
                  {entry.ticker}
                  <span className="ml-2 text-[var(--muted)]">{entry.company}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Pinned
        </p>
        {pinned.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="flex flex-wrap gap-1">
            {pinned.map((p) => (
              <li key={p.symbol}>
                <button type="button" onClick={() => onSelectSymbol(p.symbol)}>
                  <Badge variant="outline">{p.symbol}</Badge>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Search history
        </p>
        {recentSearches.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1">
            {recentSearches.slice(0, 5).map((s) => (
              <li key={`${s.query}-${s.at}`}>
                <button
                  type="button"
                  className="text-sm text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  onClick={() => onSelectSymbol(s.query)}
                >
                  {s.query}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-auto border-t border-[var(--border)] pt-3">
        <Link
          href="/research/institutional"
          className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Open institutional research dashboard
        </Link>
        <p className="mt-2 text-[10px] text-[var(--muted)]">
          Identity from official Security Master (ISIN + MIC)
        </p>
      </div>
    </div>
  );
}
