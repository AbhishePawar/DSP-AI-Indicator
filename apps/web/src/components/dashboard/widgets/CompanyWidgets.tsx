"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ds";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import {
  DashboardWidgetShell,
  WidgetUnavailable,
} from "../DashboardWidgetShell";

export function RecentlyViewedCompaniesWidget() {
  const [entries, setEntries] = useState<RecentAnalysisEntry[]>([]);
  const pinCompany = useDashboardPrefsStore((s) => s.pinCompany);
  const isPinned = useDashboardPrefsStore((s) => s.isPinned);

  useEffect(() => {
    setEntries(loadRecentAnalyses());
  }, []);

  return (
    <DashboardWidgetShell
      title="Recently Viewed Companies"
      description="From local analysis history in this browser"
      action={
        <Link
          href="/analysis"
          className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Analyze
        </Link>
      }
    >
      {entries.length === 0 ? (
        <WidgetUnavailable
          description="Run Company Analysis to populate recent companies. Nothing is invented here."
          href="/analysis"
          actionLabel="Analyze Company"
        />
      ) : (
        <ul className="space-y-2" aria-label="Recently viewed companies">
          {entries.slice(0, 6).map((entry) => (
            <li
              key={`${entry.ticker}-${entry.analysedAt}`}
              className="flex items-center justify-between gap-2 text-sm"
            >
              <Link
                href={`/analysis?symbol=${encodeURIComponent(entry.ticker)}`}
                className="min-w-0 truncate font-medium text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                {entry.ticker}
                {entry.company ? (
                  <span className="ml-2 font-normal text-[var(--muted)]">
                    {entry.company}
                  </span>
                ) : null}
              </Link>
              <Button
                size="sm"
                variant="ghost"
                disabled={isPinned(entry.ticker)}
                onClick={() => pinCompany(entry.ticker, entry.company)}
                aria-label={`Pin ${entry.ticker}`}
              >
                Pin
              </Button>
            </li>
          ))}
        </ul>
      )}
    </DashboardWidgetShell>
  );
}

export function PinnedCompaniesWidget() {
  const pinned = useDashboardPrefsStore((s) => s.pinnedCompanies);
  const unpinCompany = useDashboardPrefsStore((s) => s.unpinCompany);

  return (
    <DashboardWidgetShell
      title="Pinned Companies"
      description="Local pins — preferences only"
    >
      {pinned.length === 0 ? (
        <WidgetUnavailable
          description="Pin a symbol from Quick Company Search or recent companies."
          href="/analysis"
          actionLabel="Analyze Company"
        />
      ) : (
        <ul className="space-y-2" aria-label="Pinned companies">
          {pinned.map((item) => (
            <li
              key={item.symbol}
              className="flex items-center justify-between gap-2 text-sm"
            >
              <Link
                href={`/analysis?symbol=${encodeURIComponent(item.symbol)}`}
                className="font-medium text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                {item.symbol}
                {item.label ? (
                  <span className="ml-2 font-normal text-[var(--muted)]">
                    {item.label}
                  </span>
                ) : null}
              </Link>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => unpinCompany(item.symbol)}
                aria-label={`Unpin ${item.symbol}`}
              >
                Unpin
              </Button>
            </li>
          ))}
        </ul>
      )}
    </DashboardWidgetShell>
  );
}

export function RecentResearchWidget() {
  const [entries, setEntries] = useState<RecentAnalysisEntry[]>([]);

  useEffect(() => {
    setEntries(loadRecentAnalyses());
  }, []);

  return (
    <DashboardWidgetShell
      title="Recent Research"
      description="Local research history — open Research Workspace for more"
      action={
        <Link
          href="/research"
          className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Workspace
        </Link>
      }
    >
      {entries.length === 0 ? (
        <WidgetUnavailable
          description="Data unavailable. Analyze a company or open Research Workspace."
          href="/research"
          actionLabel="Open Research"
        />
      ) : (
        <ul className="space-y-2 text-sm" aria-label="Recent research">
          {entries.slice(0, 5).map((entry) => (
            <li key={`${entry.ticker}-r-${entry.analysedAt}`}>
              <Link
                href={`/research/${encodeURIComponent(entry.ticker)}`}
                className="text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                {entry.ticker}
              </Link>
              <span className="ml-2 text-xs text-[var(--muted)]">
                {new Date(entry.analysedAt).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </DashboardWidgetShell>
  );
}
