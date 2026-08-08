"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Badge, Button, Input } from "@/components/ds";
import { loadRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import {
  REPORT_SECTIONS,
  useInstitutionalReportsPrefsStore,
  type ReportSectionId,
} from "@/lib/institutional-reports";
import { cn } from "@/lib/utils";

export function ReportsLeftNav({
  symbol,
  query,
  onQueryChange,
  onSelectSymbol,
  onLoad,
  loading,
}: {
  symbol: string;
  query: string;
  onQueryChange: (value: string) => void;
  onSelectSymbol: (symbol: string) => void;
  onLoad: () => void;
  loading: boolean;
}) {
  const router = useRouter();
  const activeSection = useInstitutionalReportsPrefsStore(
    (s) => s.activeSection,
  );
  const setActiveSection = useInstitutionalReportsPrefsStore(
    (s) => s.setActiveSection,
  );
  const favourites = useInstitutionalReportsPrefsStore((s) => s.favourites);
  const toggleFavourite = useInstitutionalReportsPrefsStore(
    (s) => s.toggleFavourite,
  );
  const [recentTick] = useState(0);
  void recentTick;
  const recent = loadRecentAnalyses();

  function selectSection(id: ReportSectionId) {
    setActiveSection(id);
    router.replace(
      `/research/institutional?symbol=${encodeURIComponent(symbol)}&section=${id}`,
    );
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3 print:hidden">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Report ticker
        </p>
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            onSelectSymbol(query);
            onLoad();
          }}
        >
          <Input
            value={query}
            onChange={(e) => onQueryChange(e.target.value.toUpperCase())}
            placeholder="Ticker"
            aria-label="Report ticker"
            autoComplete="off"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              type="submit"
              disabled={loading}
              className="flex-1"
            >
              {loading ? "Loading…" : "Load report"}
            </Button>
            <Button
              size="sm"
              type="button"
              variant="ghost"
              aria-pressed={favourites.includes(symbol)}
              aria-label={
                favourites.includes(symbol)
                  ? "Remove favourite"
                  : "Add favourite"
              }
              onClick={() => toggleFavourite(symbol)}
            >
              ★
            </Button>
          </div>
        </form>
      </div>

      {favourites.length > 0 ? (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Favourites
          </p>
          <ul className="flex flex-wrap gap-1" aria-label="Favourite tickers">
            {favourites.map((fav) => (
              <li key={fav}>
                <button
                  type="button"
                  onClick={() => onSelectSymbol(fav)}
                  className={cn(
                    "rounded-[var(--radius-md)] border border-[var(--border)] px-2 py-1 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                    fav === symbol
                      ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                      : "hover:bg-[var(--surface-2)]",
                  )}
                >
                  {fav}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <nav aria-label="Report sections">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Report modules
        </p>
        <ul className="space-y-1">
          {REPORT_SECTIONS.map((section) => (
            <li key={section.id}>
              <button
                type="button"
                onClick={() => selectSection(section.id)}
                aria-current={
                  activeSection === section.id ? "true" : undefined
                }
                className={cn(
                  "flex w-full items-center justify-between rounded-[var(--radius-md)] px-2 py-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                  activeSection === section.id
                    ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "hover:bg-[var(--surface-2)]",
                )}
              >
                <span className="truncate">{section.label}</span>
                <Badge variant="outline" className="text-[10px]">
                  {section.shortcut}
                </Badge>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Recent reports
        </p>
        {recent.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1" aria-label="Recent local reports">
            {recent.slice(0, 8).map((entry) => (
              <li key={`${entry.ticker}-${entry.analysedAt}`}>
                <button
                  type="button"
                  onClick={() => onSelectSymbol(entry.ticker)}
                  className="w-full rounded-[var(--radius-md)] px-2 py-2 text-left text-xs hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                >
                  <span className="font-medium">{entry.ticker}</span>
                  <span className="mt-0.5 block truncate text-[var(--muted)]">
                    {entry.recommendation}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
