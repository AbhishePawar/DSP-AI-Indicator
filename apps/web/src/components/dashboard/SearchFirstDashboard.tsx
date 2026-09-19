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
    <div className="dsp-page-enter space-y-8 pb-8">
      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]">
        <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-[1.25fr_0.75fr] lg:p-10">
          <div>
            <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">
              <span className="h-2 w-2 rounded-full bg-[var(--accent)]" aria-hidden="true" />
              DSP AI Indicator
            </div>
            <h1 className="mt-5 max-w-3xl font-[family-name:var(--font-display)] text-5xl leading-[0.98] tracking-tight sm:text-7xl">
              Research any company.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-[var(--muted)] sm:text-lg">
              A focused workspace for turning company evidence into a clear, reviewable DSP judgment.
            </p>
          </div>
          <div className="flex flex-col justify-between gap-8 rounded-[var(--radius-lg)] bg-[var(--accent-soft)] p-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent)]">
                Today&apos;s research path
              </p>
              <p className="mt-3 text-lg font-semibold leading-7">Find. Verify. Challenge. Review.</p>
            </div>
            <p className="text-sm leading-6 text-[var(--muted)]">
              Every snapshot starts with a security identity and keeps sources, dates, and uncertainty visible.
            </p>
          </div>
        </div>

        <div className="border-t border-[var(--border)] bg-[var(--surface-2)] p-5 sm:p-6" aria-labelledby="search-heading">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="w-full max-w-3xl">
              <div className="flex items-center justify-between gap-4">
                <h2 id="search-heading" className="text-sm font-semibold">Search a company or stock</h2>
                <span className="font-mono text-xs text-[var(--muted)]">⌘ K</span>
              </div>
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
                  <div id="company-results" role="listbox" aria-label="Company search results" className="absolute z-10 mt-2 w-full overflow-hidden rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-md)]">
                    {matched.length === 0 ? (
                      <p className="p-4 text-sm text-[var(--muted)]">No matching security. Try a ticker or company name.</p>
                    ) : matched.map((company, index) => (
                      <CompanyResult key={company.ticker} company={company} active={index === activeIndex} onSelect={() => submit(company.ticker)} />
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
            <Button type="button" className="w-full lg:w-auto" onClick={() => submit(matched[activeIndex]?.ticker ?? query)} disabled={!query.trim()}>
              Start research
            </Button>
          </div>
          <p className="mt-3 text-xs text-[var(--muted)]">Use ↑ ↓ to choose a result, Enter to open, or Esc to clear.</p>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3" aria-label="Research method">
        {[
          { label: "01 / Identify", text: "Ticker, exchange, and coverage before analysis." },
          { label: "02 / Evidence", text: "Sources, as-of dates, and verification status." },
          { label: "03 / Decide", text: "Quality, moat, valuation, risks, and verdict." },
        ].map((item) => (
          <div key={item.label} className="rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]">
            <p className="font-mono text-xs font-semibold text-[var(--accent)]">{item.label}</p>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{item.text}</p>
          </div>
        ))}
      </section>

      {!showResults && recent.length > 0 ? (
        <section className="rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)]" aria-labelledby="recent-heading">
          <div className="flex items-center justify-between border-b border-[var(--border)] p-5">
            <h2 id="recent-heading" className="text-sm font-semibold">Recent research</h2>
            <span className="text-xs text-[var(--muted)]">Your workspace</span>
          </div>
          <div className="divide-y divide-[var(--border)]">
            {recent.slice(0, 5).map((entry) => (
              <button key={`${entry.ticker}-${entry.analysedAt}`} type="button" onClick={() => submit(entry.ticker)} className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left hover:bg-[var(--surface-2)]">
                <span><span className="block font-medium">{entry.company || entry.ticker}</span><span className="font-mono text-xs text-[var(--muted)]">{entry.ticker}</span></span>
                <span className="text-xs text-[var(--muted)]">Open research →</span>
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
