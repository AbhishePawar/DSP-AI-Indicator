"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge, Button, SearchBox } from "@/components/ds";
import { ANALYSIS_SECTIONS, useWorkspacePrefsStore } from "@/lib/company-analysis";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import { COMPANY_CATALOGUE, searchCatalogue } from "@/lib/companies/catalogue";
import { cn } from "@/lib/utils";

export function WorkspaceLeftNav({
  symbol,
  query,
  onQueryChange,
  onSelectSymbol,
  onAnalyze,
  analyzing,
}: {
  symbol: string;
  query: string;
  onQueryChange: (value: string) => void;
  onSelectSymbol: (symbol: string) => void;
  onAnalyze: () => void;
  analyzing: boolean;
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

  const matches = searchCatalogue(query).slice(0, 8);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Company search
        </p>
        <SearchBox
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              onAnalyze();
            }
          }}
          placeholder="Symbol or name"
          aria-label="Company search"
        />
        <div className="mt-2 flex flex-wrap gap-2">
          <Button size="sm" onClick={onAnalyze} disabled={analyzing}>
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
        {query.trim() ? (
          <ul className="mt-2 space-y-1" aria-label="Search results">
            {matches.map((c) => (
              <li key={c.ticker}>
                <button
                  type="button"
                  className="w-full rounded-[var(--radius-md)] px-2 py-1.5 text-left text-sm hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  onClick={() => onSelectSymbol(c.ticker)}
                >
                  <span className="font-medium">{c.ticker}</span>
                  <span className="ml-2 text-[var(--muted)]">{c.name}</span>
                </button>
              </li>
            ))}
            {!matches.length ? (
              <li className="px-2 text-xs text-[var(--muted)]">
                No catalogue match — Analyze still runs against the API.
              </li>
            ) : null}
          </ul>
        ) : null}
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
              "financial",
              "ai",
              "explainability",
              "evidence",
              "timeline",
              "export",
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
          Catalogue size: {COMPANY_CATALOGUE.length} (local directory only)
        </p>
      </div>
    </div>
  );
}
