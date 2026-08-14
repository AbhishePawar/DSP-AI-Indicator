"use client";

import Link from "next/link";

import { Button, Input } from "@/components/ds";
import { loadRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import {
  useResearchNotebookStore,
  type SavedResearchSession,
} from "@/lib/research-canvas";
import { useComparisonPrefsStore } from "@/lib/company-comparison";
import { usePortfolioIntelPrefsStore } from "@/lib/portfolio-intelligence";
import { SectionCard } from "./Primitives";

export function CanvasLeftNav({
  symbol,
  onSelectSymbol,
  searchQuery,
  onSearchChange,
}: {
  symbol: string | null;
  onSelectSymbol: (symbol: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}) {
  const savedSessions = useResearchNotebookStore((s) => s.savedSessions);
  const bookmarks = useResearchNotebookStore((s) => s.bookmarks);
  const watch = useComparisonPrefsStore((s) => s.watch);
  const portfolioWatch = usePortfolioIntelPrefsStore((s) => s.watchlist);
  const recent = loadRecentAnalyses().slice(0, 8);

  return (
    <nav
      aria-label="Research Navigator"
      className="flex h-full flex-col gap-3 overflow-y-auto p-3"
    >
      <SectionCard
        title="Research Navigator"
        description="Jump to company research surfaces"
      >
        <label className="block text-xs text-[var(--muted)]" htmlFor="canvas-symbol">
          Symbol
        </label>
        <div className="mt-1 flex gap-2">
          <Input
            id="canvas-symbol"
            value={symbol ?? ""}
            onChange={(e) => onSelectSymbol(e.target.value.toUpperCase())}
            placeholder="e.g. AAPL"
            aria-label="Active research symbol"
            className="min-h-11"
          />
        </div>
        <label
          className="mt-3 block text-xs text-[var(--muted)]"
          htmlFor="canvas-search"
        >
          Workspace search
        </label>
        <Input
          id="canvas-search"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Evidence, notes, reports…"
          aria-label="Search research workspace"
          className="mt-1 min-h-11"
        />
        <div className="mt-3 flex flex-wrap gap-2">
          <Link href="/analysis">
            <Button size="sm" variant="secondary">
              Company Analysis
            </Button>
          </Link>
          <Link href="/research">
            <Button size="sm" variant="ghost">
              Library
            </Button>
          </Link>
        </div>
      </SectionCard>

      <SectionCard title="Recent Research">
        {recent.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {recent.map((r) => (
              <li key={`${r.ticker}-${r.analysedAt}`}>
                <button
                  type="button"
                  className="text-left text-[var(--accent)] hover:underline"
                  onClick={() => onSelectSymbol(r.ticker)}
                >
                  {r.ticker} · {r.company}
                </button>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Saved Research">
        {savedSessions.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {savedSessions.slice(0, 8).map((s: SavedResearchSession) => (
              <li key={s.id}>
                <Link
                  href={
                    s.symbol
                      ? `/research/canvas?symbol=${encodeURIComponent(s.symbol)}&tab=${s.tab}`
                      : `/research/canvas?tab=${s.tab}`
                  }
                  className="text-[var(--accent)] hover:underline"
                >
                  {s.title}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Watchlists">
        {watch.length === 0 && portfolioWatch.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {watch.slice(0, 10).map((w) => (
              <li key={w.id}>
                <button
                  type="button"
                  className="font-mono text-[var(--accent)] hover:underline"
                  onClick={() => onSelectSymbol(w.symbol)}
                >
                  {w.symbol}
                </button>
              </li>
            ))}
            {portfolioWatch.slice(0, 10).map((w) => (
              <li key={`pw-${w.symbol}`}>
                <button
                  type="button"
                  className="font-mono text-[var(--accent)] hover:underline"
                  onClick={() => onSelectSymbol(w.symbol)}
                >
                  {w.symbol}
                </button>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Bookmarks">
        {bookmarks.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {bookmarks.slice(0, 8).map((b) => (
              <li key={b.id}>
                <Link href={b.href} className="text-[var(--accent)] hover:underline">
                  {b.label}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="History">
        <p className="text-xs text-[var(--muted)]">
          Session history is local. Institutional timeline requires authenticated
          Research Intelligence feeds when available.
        </p>
        <Link href="/research" className="mt-2 inline-block">
          <Button size="sm" variant="ghost">
            Open research library
          </Button>
        </Link>
      </SectionCard>
    </nav>
  );
}
