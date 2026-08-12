"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Badge, Button, SearchBox } from "@/components/ds";
import {
  RESEARCH_SECTIONS,
  libraryFromArchive,
  libraryFromRecent,
  libraryFromReports,
  mergeLibraryItems,
  useResearchWorkspacePrefsStore,
  type ResearchLibraryItem,
} from "@/lib/research-workspace";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { listArchivedSessions } from "@/lib/copilot/sessionArchive";
import { listRecentReports } from "@/lib/recentReports";
import { cn } from "@/lib/utils";

export function ResearchLeftNav({
  query,
  onQueryChange,
  onOpenTicker,
  onAnalyze,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  onOpenTicker: (ticker: string) => void;
  onAnalyze: () => void;
}) {
  const activeSection = useResearchWorkspacePrefsStore((s) => s.activeSection);
  const setActiveSection = useResearchWorkspacePrefsStore(
    (s) => s.setActiveSection,
  );
  const favourites = useResearchWorkspacePrefsStore((s) => s.favourites);
  const pinnedTickers = useResearchWorkspacePrefsStore((s) => s.pinnedTickers);
  const selectedTicker = useResearchWorkspacePrefsStore((s) => s.selectedTicker);

  const [recent, setRecent] = useState<RecentAnalysisEntry[]>([]);
  const [library, setLibrary] = useState<ResearchLibraryItem[]>([]);

  useEffect(() => {
    const recentEntries = loadRecentAnalyses();
    setRecent(recentEntries);
    setLibrary(
      mergeLibraryItems([
        ...libraryFromRecent(recentEntries),
        ...libraryFromArchive(listArchivedSessions()),
        ...libraryFromReports(listRecentReports()),
      ]),
    );
  }, [selectedTicker]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return library.slice(0, 12);
    return library
      .filter(
        (item) =>
          item.ticker.toLowerCase().includes(q) ||
          item.company.toLowerCase().includes(q),
      )
      .slice(0, 12);
  }, [library, query]);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Search research
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
          placeholder="Ticker"
          aria-label="Search research by ticker"
        />
        <div className="mt-2 flex flex-wrap gap-2">
          <Button size="sm" onClick={onAnalyze}>
            Open / Load
          </Button>
        </div>
      </div>

      <nav aria-label="Research sections">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Sections
        </p>
        <ul className="space-y-0.5">
          {RESEARCH_SECTIONS.map((section) => (
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
          Research list
        </p>
        {filtered.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1" aria-label="Research library results">
            {filtered.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onOpenTicker(item.ticker)}
                  className={cn(
                    "w-full rounded-[var(--radius-md)] px-2 py-1.5 text-left text-sm hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                    selectedTicker === item.ticker && "bg-[var(--accent-soft)]",
                  )}
                >
                  <span className="font-medium">{item.ticker}</span>
                  <span className="ml-2 text-[var(--muted)]">{item.company}</span>
                  <Badge variant="outline" className="ml-2 text-[10px]">
                    {item.source}
                  </Badge>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Recent
        </p>
        {recent.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {recent.slice(0, 5).map((e) => (
              <li key={`${e.ticker}-${e.analysedAt}`}>
                <button
                  type="button"
                  className="text-[var(--accent)] hover:underline"
                  onClick={() => onOpenTicker(e.ticker)}
                >
                  {e.ticker}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Favourites
        </p>
        {favourites.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="flex flex-wrap gap-1">
            {favourites.map((f) => (
              <li key={f.ticker}>
                <button type="button" onClick={() => onOpenTicker(f.ticker)}>
                  <Badge variant="accent">{f.ticker}</Badge>
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
        {pinnedTickers.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="flex flex-wrap gap-1">
            {pinnedTickers.map((t) => (
              <li key={t}>
                <button type="button" onClick={() => onOpenTicker(t)}>
                  <Badge variant="outline">{t}</Badge>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-auto space-y-2 border-t border-[var(--border)] pt-3">
        <Link
          href="/research/institutional"
          className="block text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Institutional research dashboard
        </Link>
        <Link
          href="/analysis"
          className="block text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Company Analysis Workspace
        </Link>
      </div>
    </div>
  );
}
