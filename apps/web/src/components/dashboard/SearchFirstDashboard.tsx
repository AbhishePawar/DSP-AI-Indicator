"use client";

import { useState } from "react";

import { Button, SearchBox } from "@/components/ds";
import { useRouter } from "next/navigation";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import {
  analysisHref,
  useSecurityMasterSearch,
} from "@/lib/securities/useSecurityMasterSearch";

export function SearchFirstDashboard() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [recent] = useState<RecentAnalysisEntry[]>(loadRecentAnalyses);
  const search = useSecurityMasterSearch(query);

  const showResults = query.trim().length > 0;

  function submitSelected() {
    if (search.resolution === "EXACT" && search.candidates.length === 1) {
      router.push(analysisHref(search.candidates[0]));
      return;
    }
  }

  return (
    <div className="px-4 py-16 sm:py-20">
      <div className="mx-auto flex max-w-2xl flex-col items-center">
        <h1 className="text-center font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">
          What company would you like to research?
        </h1>
        <p className="mt-3 text-center text-lg text-[var(--muted)]">
          Search by company name, ticker, ISIN, or security code, then select
          the exact security.
        </p>

        <div className="mt-8 w-full space-y-3">
          <SearchBox
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
            }}
            placeholder="Search a company or stock — e.g. ticker, name, or ISIN"
            aria-label="Search a company or stock"
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                submitSelected();
              }
            }}
          />
          <Button
            type="button"
            className="w-full"
            onClick={submitSelected}
            disabled={
              !query.trim() ||
              search.loading ||
              search.resolution !== "EXACT" ||
              search.candidates.length !== 1
            }
          >
            Research
          </Button>
        </div>

        {showResults && (
          <div className="mt-4 w-full">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Results
            </p>
            {search.loading ? (
              <p className="text-sm text-[var(--muted)]">Searching…</p>
            ) : !search.available ? (
              <p className="text-sm text-[var(--muted)]">
                {search.message || "Data unavailable."}
              </p>
            ) : search.candidates.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">
                {search.message ||
                  "No exact security in the official universe."}
              </p>
            ) : (
              <>
                {search.resolution === "AMBIGUOUS" ||
                search.resolution === "DUAL_LISTING_CANDIDATES" ? (
                  <p className="mb-2 text-sm text-[var(--muted)]">
                    {search.message}
                  </p>
                ) : null}
                <ul className="space-y-1">
                  {search.candidates.map((company) => (
                    <li key={company.listing_id}>
                      <Button
                        type="button"
                        variant="ghost"
                        className="w-full justify-start"
                        onClick={() => router.push(analysisHref(company))}
                      >
                        <span className="flex flex-col items-start gap-0.5 text-left">
                          <span className="font-medium">
                            {company.company_name}{" "}
                            <span className="font-mono text-xs text-[var(--muted)]">
                              {company.trading_symbol}
                            </span>
                          </span>
                          <span className="text-xs text-[var(--muted)]">
                            {company.exchange} · {company.mic}
                            {company.isin ? ` · ${company.isin}` : ""}
                            {` · ${company.security_type}`}
                          </span>
                        </span>
                      </Button>
                    </li>
                  ))}
                </ul>
              </>
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
    </div>
  );
}
