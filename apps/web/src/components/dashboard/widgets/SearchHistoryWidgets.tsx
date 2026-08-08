"use client";

import Link from "next/link";

import { Button } from "@/components/ds";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import {
  DashboardWidgetShell,
  WidgetUnavailable,
} from "../DashboardWidgetShell";

export function RecentSearchesWidget() {
  const recent = useDashboardPrefsStore((s) => s.recentSearches);
  const saveSearch = useDashboardPrefsStore((s) => s.saveSearch);

  return (
    <DashboardWidgetShell
      title="Recent Searches"
      description="Local search history — UI only"
    >
      {recent.length === 0 ? (
        <WidgetUnavailable
          description="Search a company symbol to populate recent searches."
          href="/analysis"
          actionLabel="Analyze Company"
        />
      ) : (
        <ul className="space-y-2" aria-label="Recent searches">
          {recent.map((entry) => (
            <li
              key={`${entry.query}-${entry.at}`}
              className="flex items-center justify-between gap-2 text-sm"
            >
              <Link
                href={`/analysis?symbol=${encodeURIComponent(entry.query)}`}
                className="text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                {entry.query}
              </Link>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => saveSearch(entry.query)}
              >
                Save
              </Button>
            </li>
          ))}
        </ul>
      )}
    </DashboardWidgetShell>
  );
}

export function SavedSearchesWidget() {
  const saved = useDashboardPrefsStore((s) => s.savedSearches);
  const removeSavedSearch = useDashboardPrefsStore((s) => s.removeSavedSearch);

  return (
    <DashboardWidgetShell
      title="Saved Searches"
      description="UI-only preferences — not synced to backend"
    >
      {saved.length === 0 ? (
        <WidgetUnavailable description="Save a recent search to pin it here." />
      ) : (
        <ul className="space-y-2" aria-label="Saved searches">
          {saved.map((entry) => (
            <li
              key={`saved-${entry.query}`}
              className="flex items-center justify-between gap-2 text-sm"
            >
              <Link
                href={`/analysis?symbol=${encodeURIComponent(entry.query)}`}
                className="text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                {entry.query}
              </Link>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => removeSavedSearch(entry.query)}
                aria-label={`Remove saved search ${entry.query}`}
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
    </DashboardWidgetShell>
  );
}
