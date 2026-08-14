"use client";

/**
 * EPIC-014 — Institutional Dashboard / Research Command Center.
 * Composes existing local data + navigation — no fabricated metrics.
 */

import Link from "next/link";
import { useMemo } from "react";

import { Button } from "@/components/ds";
import { loadRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import { useComparisonPrefsStore } from "@/lib/company-comparison";
import { featureFlags } from "@/lib/featureFlags";
import { usePortfolio } from "@/lib/portfolio/PortfolioProvider";
import { usePortfolioIntelPrefsStore } from "@/lib/portfolio-intelligence";
import { useResearchNotebookStore } from "@/lib/research-canvas";
import {
  DashboardWidgetShell,
  WidgetUnavailable,
} from "../DashboardWidgetShell";

export function ResearchCommandCenterWidget() {
  const { holdings } = usePortfolio();
  const watchlist = usePortfolioIntelPrefsStore((s) => s.watchlist);
  const notes = useResearchNotebookStore((s) => s.entries);
  const savedComparisons = useComparisonPrefsStore((s) => s.saved);
  const recent = useMemo(() => loadRecentAnalyses().slice(0, 5), []);

  return (
    <DashboardWidgetShell
      title="Research Command Center"
      description="Open research, portfolio status, coverage, comparisons, RI, committee, notes, watchlist — existing data only"
      span={2}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <section>
          <h3 className="text-sm font-medium">Open Research</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {featureFlags.researchCanvas ? (
              <Link href="/research/canvas">
                <Button size="sm" variant="secondary">
                  Research Canvas
                </Button>
              </Link>
            ) : null}
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
          {recent.length === 0 ? (
            <p className="mt-2 text-xs text-[var(--muted)]">Data unavailable.</p>
          ) : (
            <ul className="mt-2 space-y-1 text-sm">
              {recent.map((r) => (
                <li key={`${r.ticker}-${r.analysedAt}`}>
                  <Link
                    href={`/analysis?symbol=${encodeURIComponent(r.ticker)}`}
                    className="text-[var(--accent)] hover:underline"
                  >
                    {r.ticker}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h3 className="text-sm font-medium">Portfolio Status</h3>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Holdings: {holdings.length || "Data unavailable."} · Watchlist:{" "}
            {watchlist.length || "Data unavailable."}
          </p>
          <Link href="/portfolio" className="mt-2 inline-block">
            <Button size="sm" variant="secondary">
              Portfolio Intelligence
            </Button>
          </Link>
        </section>

        <section>
          <h3 className="text-sm font-medium">Coverage</h3>
          <p className="mt-2 text-sm text-[var(--muted)]">
            {holdings.length
              ? `${holdings.filter((h) => h.researchAvailable).length}/${holdings.length} research-available (session)`
              : "Data unavailable."}
          </p>
        </section>

        <section>
          <h3 className="text-sm font-medium">Recent Comparisons</h3>
          {savedComparisons.length === 0 ? (
            <WidgetUnavailable
              description="Data unavailable. Save a comparison in Company Comparison."
              href="/analysis/compare"
              actionLabel="Compare"
            />
          ) : (
            <ul className="mt-2 space-y-1 text-sm">
              {savedComparisons.slice(0, 4).map((c) => (
                <li key={c.id}>
                  <Link
                    href={`/analysis/compare?symbols=${encodeURIComponent(c.symbols.join(","))}`}
                    className="text-[var(--accent)] hover:underline"
                  >
                    {c.title}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h3 className="text-sm font-medium">Research Intelligence</h3>
          {featureFlags.researchIntelligence ? (
            <Link href="/research/intelligence" className="mt-2 inline-block">
              <Button size="sm" variant="secondary">
                Open RI
              </Button>
            </Link>
          ) : (
            <p className="mt-2 text-xs text-[var(--muted)]">
              Research Intelligence disabled.
            </p>
          )}
        </section>

        <section>
          <h3 className="text-sm font-medium">Committee Alerts</h3>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Data unavailable. Open Company Analysis AI Committee per ticker —
            no portfolio-level committee feed in v1.
          </p>
          <Link href="/analysis?section=ai" className="mt-2 inline-block">
            <Button size="sm" variant="ghost">
              Committee
            </Button>
          </Link>
        </section>

        <section>
          <h3 className="text-sm font-medium">Saved Notes</h3>
          {notes.length === 0 ? (
            <p className="mt-2 text-sm text-[var(--muted)]">Data unavailable.</p>
          ) : (
            <ul className="mt-2 space-y-1 text-sm">
              {notes.slice(0, 4).map((n) => (
                <li key={n.id} className="truncate">
                  {n.kind}: {n.text}
                </li>
              ))}
            </ul>
          )}
          {featureFlags.researchCanvas ? (
            <Link
              href="/research/canvas?tab=notes"
              className="mt-2 inline-block"
            >
              <Button size="sm" variant="ghost">
                Notebook
              </Button>
            </Link>
          ) : null}
        </section>

        <section>
          <h3 className="text-sm font-medium">Watchlist Activity</h3>
          {watchlist.length === 0 ? (
            <p className="mt-2 text-sm text-[var(--muted)]">Data unavailable.</p>
          ) : (
            <ul className="mt-2 space-y-1 text-sm">
              {watchlist.slice(0, 6).map((w) => (
                <li key={w.symbol}>
                  <Link
                    href={`/analysis?symbol=${encodeURIComponent(w.symbol)}`}
                    className="font-mono text-[var(--accent)] hover:underline"
                  >
                    {w.symbol}
                  </Link>
                  <span className="ml-2 text-xs text-[var(--muted)]">
                    {new Date(w.addedAt).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </DashboardWidgetShell>
  );
}
