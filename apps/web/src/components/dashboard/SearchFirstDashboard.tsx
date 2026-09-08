"use client";

import { useState } from "react";

import { Button, SearchBox } from "@/components/ds";
import { useRouter } from "next/navigation";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import type { SecuritySearchCandidate } from "@/lib/api/client";
import {
  analysisHref,
  useSecurityMasterSearch,
} from "@/lib/securities/useSecurityMasterSearch";

function recentHref(entry: RecentAnalysisEntry) {
  const params = new URLSearchParams({
    symbol: entry.ticker.trim().toUpperCase(),
  });
  if (entry.exchange && entry.exchange !== "—") {
    params.set("exchange", entry.exchange);
  }
  if (entry.isin) params.set("isin", entry.isin);
  return `/analysis?${params.toString()}`;
}

export function SearchFirstDashboard() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<SecuritySearchCandidate | null>(
    null,
  );
  const [recent] = useState<RecentAnalysisEntry[]>(loadRecentAnalyses);
  const search = useSecurityMasterSearch(query);
  const typed = query.trim().length > 0;
  const canResearch = Boolean(
    selected && selected.dsp_eligible && selected.identity_ok,
  );

  function choose(candidate: SecuritySearchCandidate) {
    if (!candidate.dsp_eligible || !candidate.identity_ok) return;
    setSelected(candidate);
  }

  function submit() {
    if (!selected || !selected.dsp_eligible || !selected.identity_ok) return;
    router.push(analysisHref(selected));
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
              setSelected(null);
            }}
            placeholder="Search a company or stock"
            aria-label="Search a company or stock"
            aria-controls="security-search-results"
            aria-expanded={typed}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                submit();
              }
            }}
          />
          <Button
            type="button"
            className="w-full"
            onClick={submit}
            disabled={!canResearch || search.loading}
          >
            Research
          </Button>
        </div>

        <div id="security-search-results" className="mt-4 w-full" role="region" aria-live="polite">
          {!typed ? (
            <p className="text-sm text-[var(--muted)]">
              Start typing a company or stock.
            </p>
          ) : search.loading ? (
            <p className="text-sm text-[var(--muted)]">Searching…</p>
          ) : !search.available ? (
            <p className="text-sm text-[var(--muted)]">{search.message}</p>
          ) : search.candidates.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">
              {search.message || "No supported security found."}
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
                {search.candidates.map((company) => {
                  const unsupported =
                    !company.dsp_eligible || !company.identity_ok;
                  const active =
                    selected?.listing_id === company.listing_id;
                  return (
                    <li key={company.listing_id}>
                      <Button
                        type="button"
                        variant={active ? "secondary" : "ghost"}
                        className="w-full justify-start"
                        aria-pressed={active}
                        disabled={unsupported}
                        onClick={() => choose(company)}
                      >
                        <span className="flex flex-col items-start gap-0.5 text-left">
                          <span className="font-medium">
                            {company.company_name}{" "}
                            <span className="font-mono text-xs text-[var(--muted)]">
                              {company.trading_symbol}
                            </span>
                          </span>
                          <span className="text-xs text-[var(--muted)]">
                            {company.exchange}
                            {company.mic ? ` · ${company.mic}` : ""}
                            {company.isin ? ` · ISIN ${company.isin}` : ""}
                            {` · ${company.security_type}`}
                          </span>
                          {unsupported ? (
                            <span className="text-xs text-[var(--muted)]">
                              This security is not currently supported for DSP
                              analysis.
                            </span>
                          ) : null}
                        </span>
                      </Button>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </div>

        {recent.length > 0 && !typed ? (
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
                    onClick={() => router.push(recentHref(entry))}
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
        ) : null}

        {recent.length === 0 && !typed ? (
          <p className="mt-8 text-sm text-[var(--muted)]">
            No recent research yet. Search for a company above to get started.
          </p>
        ) : null}
      </div>
    </div>
  );
}
