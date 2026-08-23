"use client";

import { useMemo, useState } from "react";

import { Button, SearchBox } from "@/components/ds";
import { useRouter } from "next/navigation";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { searchCatalogue } from "@/lib/companies/catalogue";

export function SearchFirstDashboard() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [recent] = useState<RecentAnalysisEntry[]>(loadRecentAnalyses);

  const showResults = query.trim().length > 0;
  const matched = useMemo(() => searchCatalogue(query), [query]);

  function submit(symbol: string) {
    const trimmed = symbol.trim().toUpperCase();
    if (!trimmed) return;
    router.push(`/analysis?symbol=${encodeURIComponent(trimmed)}`);
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center px-4 py-16 sm:py-24">
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
          placeholder="Search a company or stock — e.g. TCS, Infosys, HDFC Bank"
          aria-label="Search a company or stock"
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              submit(query);
            }
          }}
        />
        <Button
          type="button"
          className="w-full"
          onClick={() => submit(query)}
          disabled={!query.trim()}
        >
          Research
        </Button>
      </div>

      {showResults && (
        <div className="mt-4 w-full">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Results
          </p>
          {matched.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">
              No companies match your search. Try a different name or ticker.
            </p>
          ) : (
            <ul className="space-y-1">
              {matched.slice(0, 8).map((company) => (
                <li key={company.ticker}>
                  <Button
                    type="button"
                    variant="ghost"
                    className="w-full justify-start"
                    onClick={() => submit(company.ticker)}
                  >
                    <span className="flex flex-col items-start gap-0.5 text-left">
                      <span className="font-medium">
                        {company.name}{" "}
                        <span className="font-mono text-xs text-[var(--muted)]">
                          {company.ticker}
                        </span>
                      </span>
                      <span className="text-xs text-[var(--muted)]">
                        {company.exchange} · {company.sector}
                      </span>
                    </span>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {recent.length > 0 && !showResults && (
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
                      `/analysis?symbol=${encodeURIComponent(entry.ticker)}`,
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
      )}

      {recent.length === 0 && !showResults && (
        <p className="mt-12 text-sm text-[var(--muted)]">
          No recent research yet. Search for a company above to get started.
        </p>
      )}
    </div>
  );
}
