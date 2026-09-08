"use client";

import { useState } from "react";

import { Button, SearchBox } from "@/components/ds";
import { useRouter } from "next/navigation";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";

function analysisHref(ticker: string, exchange?: string) {
  const params = new URLSearchParams({
    symbol: ticker.trim().toUpperCase(),
  });
  if (exchange) params.set("exchange", exchange);
  return `/analysis?${params.toString()}`;
}

export function SearchFirstDashboard() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [exchange, setExchange] = useState("");
  const [recent] = useState<RecentAnalysisEntry[]>(loadRecentAnalyses);

  function submit() {
    const trimmed = query.trim().toUpperCase();
    if (!trimmed) return;
    router.push(analysisHref(trimmed, exchange || undefined));
  }

  return (
    <div className="px-4 py-10 sm:py-16">
      <div className="mx-auto flex max-w-2xl flex-col items-center">
        <h1 className="text-center font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">
          DSP AI INDICATOR
        </h1>
        <p className="mt-3 text-center text-lg text-[var(--muted)]">
          What would you like to research?
        </p>

        <div className="mt-8 w-full space-y-3">
          <SearchBox
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
            }}
            placeholder="Search a company or stock"
            aria-label="Search a company or stock"
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                submit();
              }
            }}
          />
          <label className="block text-sm text-[var(--muted)]">
            <span className="sr-only">Exchange</span>
            <select
              className="mt-1 min-h-11 w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              value={exchange}
              onChange={(event) => setExchange(event.target.value)}
              aria-label="Exchange"
            >
              <option value="">Exchange (optional — required if dual-listed)</option>
              <option value="NSE">NSE</option>
              <option value="BSE">BSE</option>
            </select>
          </label>
          <Button
            type="button"
            className="w-full"
            onClick={() => submit()}
            disabled={!query.trim()}
          >
            Research
          </Button>
        </div>

        {recent.length > 0 ? (
          <div className="mt-12 w-full">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Recent research
            </p>
            <ul className="space-y-1">
              {recent.slice(0, 5).map((entry) => (
                <li key={`${entry.ticker}-${entry.analysedAt}`}>
                  <Button
                    type="button"
                    variant="ghost"
                    className="w-full justify-start"
                    onClick={() =>
                      router.push(
                        analysisHref(entry.ticker, entry.exchange || undefined),
                      )
                    }
                  >
                    <span className="flex flex-col items-start gap-0.5 text-left">
                      <span className="font-medium">
                        {entry.company || entry.ticker}{" "}
                        <span className="font-mono text-xs text-[var(--muted)]">
                          {entry.ticker}
                        </span>
                      </span>
                      {entry.company ? (
                        <span className="text-xs text-[var(--muted)]">
                          {new Date(entry.analysedAt).toLocaleString()}
                        </span>
                      ) : null}
                    </span>
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="mt-12 text-sm text-[var(--muted)]">
            No recent research yet. Search for a company above to get started.
          </p>
        )}
      </div>
    </div>
  );
}
