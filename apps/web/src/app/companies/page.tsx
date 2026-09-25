"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";

export default function CompaniesPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [recent, setRecent] = useState<RecentAnalysisEntry[]>([]);

  useEffect(() => {
    setRecent(loadRecentAnalyses());
  }, []);

  function openResearch(event: FormEvent) {
    event.preventDefault();
    const symbol = query.trim().toUpperCase();
    if (!symbol) return;
    router.push(`/analysis?symbol=${encodeURIComponent(symbol)}`);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Companies"
        description="Identity search only — open certified research. Directory metrics are not fabricated."
      />

      <form onSubmit={openResearch} className="dsp-card">
        <p className="section-label">Lookup</p>
        <label className="sr-only" htmlFor="company-directory-query">
          Company or ticker
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="company-directory-query"
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Enter company name or ticker"
            className="min-h-11 flex-1 rounded-[10px] border border-[var(--border)] bg-[var(--surface-2)] px-4 text-sm text-[var(--fg)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          />
          <button
            type="submit"
            className="min-h-11 rounded-[10px] bg-[var(--accent)] px-5 text-sm font-medium text-[var(--accent-fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Open research
          </button>
        </div>
      </form>

      <section className="dsp-card">
        <p className="section-label">Recent research</p>
        {recent.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            No recent research in this session.
          </p>
        ) : (
          <ul className="space-y-1">
            {recent.map((entry) => (
              <li key={`${entry.ticker}-${entry.analysedAt}`}>
                <button
                  type="button"
                  onClick={() =>
                    router.push(
                      `/analysis?symbol=${encodeURIComponent(entry.ticker)}`,
                    )
                  }
                  className="w-full rounded-lg px-2 py-2 text-left text-sm text-[var(--fg)] hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                >
                  <span className="font-mono text-xs text-[var(--accent)]">
                    {entry.ticker}
                  </span>
                  {entry.company ? (
                    <span className="ml-2 text-[var(--muted)]">
                      {entry.company}
                    </span>
                  ) : null}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
