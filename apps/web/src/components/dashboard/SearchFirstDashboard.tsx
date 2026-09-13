"use client";

import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";

import { Button, SearchBox } from "@/components/ds";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { searchCatalogue, type CompanyEntry } from "@/lib/companies/catalogue";

const SEARCH_DELAY_MS = 180;

export function SearchFirstDashboard() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [settledQuery, setSettledQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const [recent] = useState<RecentAnalysisEntry[]>(loadRecentAnalyses);
  const matched = useMemo(
    () => searchCatalogue(settledQuery).slice(0, 8),
    [settledQuery],
  );
  const showResults = settledQuery.trim().length > 0;

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSettledQuery(query);
      setActiveIndex(0);
    }, SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  function submit(symbol: string) {
    const ticker = symbol.trim().toUpperCase();
    if (!ticker) return;
    router.push(`/analysis?symbol=${encodeURIComponent(ticker)}&intent=dsp_indicator`);
  }

  function onSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
    if (event.key === "ArrowDown" && matched.length > 0) {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % matched.length);
    } else if (event.key === "ArrowUp" && matched.length > 0) {
      event.preventDefault();
      setActiveIndex((index) => (index - 1 + matched.length) % matched.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      submit(showResults ? (matched[activeIndex]?.ticker ?? query) : query);
    } else if (event.key === "Escape") {
      setQuery("");
    }
  }

  return (
    <div className="dsp-page-enter">
      <section className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--accent)]">
            DSP AI INDICATOR
          </p>
          <h1 className="mt-4 max-w-3xl font-[family-name:var(--font-display)] text-5xl leading-[1.02] tracking-tight sm:text-7xl">
            Research any company.
          </h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-[var(--muted)] sm:text-lg">
            Evidence first. AI research. DSP judgment. Start with a security identity,
            then follow the evidence through to an investment snapshot.
          </p>
        </div>
        <div className="border-l-2 border-[var(--accent)] pl-5 text-sm leading-6 text-[var(--muted)]">
          <p className="font-medium text-[var(--fg)]">One governed research path</p>
          <p className="mt-2">
            Find → verify → challenge → review. No client-side valuation or fabricated
            progress.
          </p>
        </div>
      </section>

      <section className="mt-12 max-w-3xl" aria-labelledby="search-heading">
        <h2 id="search-heading" className="text-sm font-semibold">
          Search a company or stock
        </h2>
        <div className="relative mt-3">
          <SearchBox
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onSearchKeyDown}
            placeholder="Try TCS, Infosys, or HDFC Bank"
            aria-label="Search a company or stock"
            aria-controls="company-results"
            aria-autocomplete="list"
          />
          {showResults ? (
            <div
              id="company-results"
              role="listbox"
              aria-label="Company search results"
              className="mt-2 overflow-hidden rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-md)]"
            >
              {matched.length === 0 ? (
                <p className="p-4 text-sm text-[var(--muted)]">
                  No matching security. Try a ticker or company name.
                </p>
              ) : (
                matched.map((company, index) => (
                  <CompanyResult
                    key={company.ticker}
                    company={company}
                    active={index === activeIndex}
                    onSelect={() => submit(company.ticker)}
                  />
                ))
              )}
            </div>
          ) : null}
        </div>
        <Button
          type="button"
          className="mt-3 w-full sm:w-auto"
          onClick={() => submit(matched[activeIndex]?.ticker ?? query)}
          disabled={!query.trim()}
        >
          Start DSP Indicator Research
        </Button>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Use ↑ ↓ to choose a result, Enter to open, or Esc to clear.
        </p>
      </section>

      <section className="mt-16 grid gap-4 sm:grid-cols-3" aria-label="Research method">
        {[
          {
            label: "Security identity",
            text: "Ticker, exchange, and coverage before analysis.",
          },
          {
            label: "Evidence chain",
            text: "Sources, as-of dates, and verification status.",
          },
          {
            label: "DSP judgment",
            text: "Quality, moat, valuation, risks, and verdict.",
          },
        ].map((item) => (
          <div key={item.label} className="border-t border-[var(--border)] pt-4">
            <p className="text-sm font-semibold">{item.label}</p>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{item.text}</p>
          </div>
        ))}
      </section>

      {!showResults && recent.length > 0 ? (
        <section className="mt-16 max-w-3xl" aria-labelledby="recent-heading">
          <h2 id="recent-heading" className="text-sm font-semibold">
            Recent research
          </h2>
          <div className="mt-3 divide-y divide-[var(--border)] border-y border-[var(--border)]">
            {recent.slice(0, 5).map((entry) => (
              <button
                key={`${entry.ticker}-${entry.analysedAt}`}
                type="button"
                onClick={() => submit(entry.ticker)}
                className="flex w-full items-center justify-between gap-4 py-4 text-left hover:bg-[var(--surface-2)]"
              >
                <span>
                  <span className="block font-medium">
                    {entry.company || entry.ticker}
                  </span>
                  <span className="font-mono text-xs text-[var(--muted)]">
                    {entry.ticker}
                  </span>
                </span>
                <span className="text-xs text-[var(--muted)]">Open research</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function CompanyResult({
  company,
  active,
  onSelect,
}: {
  company: CompanyEntry;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={active}
      onClick={onSelect}
      className={`flex w-full items-center justify-between gap-4 px-4 py-3 text-left ${active ? "bg-[var(--accent-soft)]" : "hover:bg-[var(--surface-2)]"}`}
    >
      <span>
        <span className="block font-medium">{company.name}</span>
        <span className="font-mono text-xs text-[var(--muted)]">{company.ticker}</span>
      </span>
      <span className="text-right text-xs text-[var(--muted)]">
        <span className="block">{company.exchange}</span>
        <span>{company.sector}</span>
      </span>
    </button>
  );
}
