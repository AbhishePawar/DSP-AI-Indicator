"use client";

import { ArrowRight, ChevronRight, Menu, Plus, Search, X } from "lucide-react";
import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

import { env } from "@/lib/env";
import { ANALYSIS_INTENTS } from "@/lib/analysis/intents";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import { useAuth } from "@/lib/auth/AuthProvider";

const researchExamples = [
  { ticker: "TCS", name: "Tata Consultancy Services", market: "NSE · TCS" },
  { ticker: "HDFCBANK", name: "HDFC Bank Limited", market: "NSE · HDFCBANK" },
  { ticker: "INFY", name: "Infosys Limited", market: "NSE · INFY" },
  { ticker: "RELIANCE", name: "Reliance Industries", market: "NSE · RELIANCE" },
];

const prompts = [
  "Analyze TCS",
  "Check valuation",
  "Find investment risks",
  "Review latest results",
];

export function MarketingLanding() {
  const recentSearches = useDashboardPrefsStore((s) => s.recentSearches);
  const recordSearch = useDashboardPrefsStore((s) => s.recordSearch);
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<(typeof researchExamples)[number] | null>(null);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  function selectCompany(company: (typeof researchExamples)[number]) {
    setSelected(company);
    setQuery(company.ticker);
    setSuggestionsOpen(false);
  }

  function runDspIndicatorAnalysis() {
    const ticker = selected?.ticker || query.trim();
    if (ticker) recordSearch(ticker);
    window.location.href = `/analysis?${ticker ? `symbol=${encodeURIComponent(ticker)}&` : ""}intent=${ANALYSIS_INTENTS.dspIndicator}`;
  }

  const matches = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return [];
    return researchExamples.filter((company) =>
      `${company.ticker} ${company.name} ${company.market}`.toLowerCase().includes(normalized),
    );
  }, [query]);

  function submitResearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const company = selected ?? matches[0];
    if (company) {
      recordSearch(company.ticker);
      window.location.href = `/analysis?symbol=${encodeURIComponent(company.ticker)}`;
    } else if (query.trim()) {
      window.location.href = `/search?q=${encodeURIComponent(query.trim())}`;
    }
  }

  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <div className="flex min-h-screen">
        <aside data-testid="landing-sidebar" className="hidden w-[220px] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] px-3.5 py-5 lg:flex">
          <div className="flex items-start justify-between">
            <Link href="/" className="group" aria-label={`${env.appName} home`}>
              <span className="block font-[family-name:var(--font-display)] text-2xl font-semibold tracking-[-0.04em]">DSP</span>
              <span className="mt-1 block text-[10px] font-medium uppercase tracking-[0.22em] text-[var(--muted)]">AI Research</span>
            </Link>
            <Link href="/dashboard" data-testid="landing-open-dashboard" className="dsp-interactive rounded-lg border border-transparent p-2 text-[var(--muted)] hover:border-[var(--border)] hover:bg-[var(--surface-2)]" aria-label="Open dashboard">
              <ChevronRight className="size-4" />
            </Link>
          </div>

          <button type="button" onClick={() => { setQuery(""); setSelected(null); setSuggestionsOpen(false); }} className="dsp-interactive mt-10 flex min-h-12 items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg)] px-4 text-left text-sm font-medium hover:bg-[var(--surface-2)]">
            <Plus className="size-4" />
            Start New Research
          </button>

          <div className="mt-9">
            <p className="font-mono text-[10px] uppercase tracking-wider text-[var(--muted)]">Recent searches</p>
            <nav className="mt-3 flex flex-col gap-1" aria-label="Recent research">
              {recentSearches.length ? recentSearches.slice(0, 3).map(({ query: recent }) => (
                <Link data-testid={`landing-recent-${recent}`} key={recent} href={`/analysis?symbol=${encodeURIComponent(recent)}`} className="dsp-interactive truncate rounded-lg px-2 py-2 text-xs text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]">{recent}</Link>
              )) : <p data-testid="landing-empty-history" className="px-2 py-2 text-xs text-[var(--muted)]">Your searches will appear here</p>}
            </nav>
          </div>

          <div className="mt-auto flex flex-col gap-4">
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg)] p-4">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Research workspace</span>
                <span className="text-[var(--muted)]">Ready</span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-[var(--muted)]">Evidence-first analysis for Indian listed companies.</p>
            </div>
            <Link data-testid="landing-account" href={user ? "/profile" : "/login"} className="dsp-interactive flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-3 text-left hover:bg-[var(--surface-2)]">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-xs font-semibold text-[var(--accent)]">{user ? user.displayName.slice(0, 2).toUpperCase() : "D"}</span>
              <span className="min-w-0 flex-1"><span className="block truncate text-xs font-medium">{user?.displayName || "Research account"}</span><span className="mt-1 block truncate text-[10px] text-[var(--muted)]">{user ? "View your profile" : "Sign in to save work"}</span></span>
              <ChevronRight className="size-4 shrink-0 text-[var(--muted)]" />
            </Link>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--bg)] px-5 py-4 lg:hidden">
            <Link href="/" className="font-[family-name:var(--font-display)] text-xl font-semibold tracking-[-0.04em]">DSP</Link>
            <button type="button" className="rounded-lg border border-[var(--border)] p-2" aria-label={mobileOpen ? "Close menu" : "Open menu"} onClick={() => setMobileOpen((value) => !value)}>
              {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </header>
          {mobileOpen ? <div className="border-b border-[var(--border)] bg-[var(--surface)] px-5 py-4 lg:hidden"><button type="button" onClick={() => { setMobileOpen(false); setQuery(""); setSelected(null); setSuggestionsOpen(false); }} className="flex min-h-11 items-center gap-3 text-sm font-medium"><Plus className="size-4" /> Start New Research</button></div> : null}

          <section className="flex flex-1 flex-col px-5 py-12 sm:px-8 lg:px-16 lg:py-16">
            <div className="mx-auto flex w-full max-w-[860px] flex-1 flex-col justify-center">
              <div className="mb-10 text-center">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--accent)]">DSP AI Research</p>
                <h1 className="mt-4 text-balance font-[family-name:var(--font-display)] text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">Research any Indian company</h1>
                <p className="mx-auto mt-4 max-w-[48ch] text-pretty text-sm leading-6 text-[var(--muted)] sm:text-base">DSP investigates the evidence, validates the data, and builds the investment case.</p>
              </div>

              <form onSubmit={submitResearch} className="relative rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)] sm:p-5">
                <label htmlFor="company-research" className="sr-only">Search company, ticker or ISIN</label>
                <div className="flex items-start gap-3">
                  <Search className="mt-1.5 size-5 shrink-0 text-[var(--muted)]" />
                  <input data-testid="landing-company-search" id="company-research" value={query} onFocus={() => setSuggestionsOpen(Boolean(query.trim()))} onChange={(event) => { setQuery(event.target.value); setSelected(null); setSuggestionsOpen(true); }} placeholder="Search company, ticker or ISIN" autoComplete="off" className="min-w-0 flex-1 bg-transparent text-lg text-[var(--fg)] outline-none placeholder:text-[var(--muted)]" aria-describedby="research-help" />
                </div>
                <div className="mt-8 flex items-center justify-between gap-3">
                  <p id="research-help" className="text-xs text-[var(--muted)]">Choose a security to confirm its identity before research begins.</p>
                  <button data-testid="landing-research-submit" type="submit" disabled={!query.trim()} className="dsp-interactive inline-flex min-h-11 shrink-0 items-center gap-2 rounded-xl bg-[var(--accent)] px-4 text-sm font-semibold text-[var(--accent-fg)] disabled:cursor-not-allowed disabled:opacity-45">Research <ArrowRight className="size-4" /></button>
                </div>
                {suggestionsOpen && !selected && query.trim() ? <div className="absolute left-4 right-4 top-full z-10 mt-2 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-md)] sm:left-5 sm:right-auto sm:w-1/2" role="listbox" aria-label="Company suggestions">
                  {matches.length ? matches.map((company) => <button key={company.ticker} type="button" role="option" aria-selected={false} onMouseDown={(event) => { event.preventDefault(); selectCompany(company); }} onClick={() => selectCompany(company)} className="flex w-full items-center justify-between gap-4 border-b border-[var(--border)] px-4 py-3 text-left last:border-b-0 hover:bg-[var(--surface-2)]"><span><span className="block text-sm font-medium">{company.name}</span><span className="mt-1 block text-xs text-[var(--muted)]">{company.market}</span></span><ChevronRight className="size-4 text-[var(--muted)]" /></button>) : <div className="px-4 py-4 text-sm text-[var(--muted)]">No matching company in the reference directory. Search another ticker; live source coverage is verified during analysis.</div>}
                </div> : null}
              </form>

              <div className="mt-10">
                <div className="flex items-center justify-between gap-4"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Suggested research</p><span className="text-xs text-[var(--muted)]">Start with a company</span></div>
                <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{researchExamples.map((company) => <button key={company.ticker} type="button" onClick={() => selectCompany(company)} className="dsp-interactive rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-left hover:bg-[var(--surface-2)]"><span className="block text-sm font-medium">{company.ticker}</span><span className="mt-1 block truncate text-xs text-[var(--muted)]">{company.name}</span></button>)}</div>
                <button type="button" onClick={runDspIndicatorAnalysis} className="dsp-interactive mt-3 flex w-full items-center justify-between gap-4 rounded-xl border border-[var(--accent)] bg-[var(--accent-soft)] px-4 py-4 text-left hover:bg-[var(--surface-2)]">
                  <span><span className="block text-sm font-semibold text-[var(--fg)]">DSP Indicator Analysis</span><span className="mt-1 block text-xs leading-5 text-[var(--muted)]">Evaluate a company using DSP&apos;s Buffett-style investment analysis framework.</span></span>
                  <ArrowRight className="size-4 shrink-0 text-[var(--accent)]" />
                </button>
              </div>

              <div className="mt-10 border-t border-[var(--border)] pt-6"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Research prompts</p><div className="mt-3 flex flex-wrap gap-2">{prompts.map((prompt) => <button key={prompt} type="button" onClick={() => setQuery(prompt.replace(/^\w+ /, ""))} className="rounded-full border border-[var(--border)] px-3 py-2 text-xs text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--fg)]">{prompt}</button>)}</div></div>
            </div>
            <footer className="mt-12 flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-center text-xs text-[var(--muted)]"><span>{env.appName} · Evidence before opinion</span><span aria-hidden="true">·</span><Link href="/docs/disclaimer" className="hover:text-[var(--fg)]">Research disclaimer</Link><span aria-hidden="true">·</span><Link href="/docs/privacy" className="hover:text-[var(--fg)]">Privacy</Link></footer>
          </section>
        </div>
      </div>
    </main>
  );
}
