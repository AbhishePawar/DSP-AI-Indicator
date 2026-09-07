"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge, Button, SearchBox } from "@/components/ds";
import { useWorkspacePrefsStore } from "@/lib/company-analysis";
import { visibleAnalysisSections } from "@/lib/company-analysis/sections";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import { useSecurityMasterSearch } from "@/lib/securities/useSecurityMasterSearch";
import { ordinaryClientShellEnabled } from "@/lib/shell/ordinaryClient";
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
  onSelectSymbol: (
    symbol: string,
    meta?: { exchange?: string; isin?: string },
  ) => void;
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

  const search = useSecurityMasterSearch(query);

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
              if (
                search.resolution === "EXACT" &&
                search.candidates.length === 1
              ) {
                const hit = search.candidates[0];
                onSelectSymbol(hit.trading_symbol, {
                  exchange: hit.exchange,
                  isin: hit.isin ?? undefined,
                });
              }
            }
          }}
          placeholder="Symbol or name"
          aria-label="Company search"
        />
        <div className="mt-2 flex flex-wrap gap-2">
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
        {query.trim() ? (
          <ul className="mt-2 space-y-1" aria-label="Search results">
            {search.loading ? (
              <li className="px-2 text-xs text-[var(--muted)]">Searching…</li>
            ) : !search.available ? (
              <li className="px-2 text-xs text-[var(--muted)]">
                {search.message || "Data unavailable."}
              </li>
            ) : (
              <>
                {search.candidates.map((c) => (
                  <li key={c.listing_id}>
                    <button
                      type="button"
                      className="w-full rounded-[var(--radius-md)] px-2 py-1.5 text-left text-sm hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                      onClick={() =>
                        onSelectSymbol(c.trading_symbol, {
                          exchange: c.exchange,
                          isin: c.isin ?? undefined,
                        })
                      }
                    >
                      <span className="font-medium">{c.trading_symbol}</span>
                      <span className="ml-2 text-[var(--muted)]">
                        {c.company_name} · {c.exchange}
                      </span>
                    </button>
                  </li>
                ))}
                {!search.candidates.length ? (
                  <li className="px-2 text-xs text-[var(--muted)]">
                    {search.message ||
                      "No exact security in the official universe."}
                  </li>
                ) : null}
              </>
            )}
          </ul>
        ) : null}
      </div>

      <nav aria-label="Analysis sections">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Report
        </p>
        <ul className="space-y-0.5">
          {visibleAnalysisSections().map((section) => (
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

      {ordinaryClientShellEnabled() ? null : (
        <div className="mt-auto border-t border-[var(--border)] pt-3">
          <Link
            href="/research/institutional"
            className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Open institutional research dashboard
          </Link>
        </div>
      )}
    </div>
  );
}
