"use client";

import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  BarChart3,
  BrainCircuit,
  Building2,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Button, SearchBox } from "@/components/ds";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { searchCatalogue, type CompanyEntry } from "@/lib/companies/catalogue";

const SEARCH_DELAY_MS = 180;

const analysisOptions = [
  {
    title: "DSP AI Indicator",
    description: "One intelligent view of business quality, valuation, growth, and risk.",
    action: "Analyze",
    intent: "dsp_indicator",
    icon: Sparkles,
    featured: true,
  },
  {
    title: "DSP Buffett-Style Analysis",
    description: "Business quality and intrinsic value for long-term fundamental research.",
    action: "Analyze",
    intent: "buffett",
    icon: ShieldCheck,
    featured: false,
  },
  {
    title: "Valuation",
    description: "Intrinsic value and relative valuation in one focused workspace.",
    action: "Explore",
    intent: "valuation",
    icon: BarChart3,
    featured: false,
  },
  {
    title: "Company Research",
    description: "Financials, growth, risks, and the fundamentals that matter.",
    action: "Research",
    intent: "company_research",
    icon: Building2,
    featured: false,
  },
] as const;

export function SearchFirstDashboard() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [settledQuery, setSettledQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const [selectedIntent, setSelectedIntent] = useState("dsp_indicator");
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

  function submit(symbol: string, intent = selectedIntent) {
    const ticker = symbol.trim().toUpperCase();
    if (!ticker) return;
    router.push(`/analysis?symbol=${encodeURIComponent(ticker)}&intent=${encodeURIComponent(intent)}`);
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
    <div className="dsp-page-enter mx-auto max-w-6xl space-y-12 pb-12">
      <section className="pt-4 text-center sm:pt-10">
        <p className="text-sm font-semibold tracking-[0.18em] text-[var(--accent)]">DSP AI INDICATOR</p>
        <h1 className="mx-auto mt-4 max-w-3xl font-[family-name:var(--font-display)] text-4xl leading-[1.05] tracking-tight sm:text-6xl">
          Research smarter.<br />Decide with clarity.
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-base leading-7 text-[var(--muted)] sm:text-lg">
          AI-powered equity research, valuation, and quality analysis.
        </p>

        <div className="relative mx-auto mt-8 max-w-2xl text-left">
          <SearchBox
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onSearchKeyDown}
            placeholder="Search company, e.g. HDFC Bank, TCS, Infosys"
            aria-label="Search a company or stock"
            aria-controls="company-results"
            aria-autocomplete="list"
          />
          {showResults ? (
            <div id="company-results" role="listbox" aria-label="Company search results" className="absolute z-10 mt-2 w-full overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-md)]">
              {matched.length === 0 ? (
                <p className="p-4 text-sm text-[var(--muted)]">No matching company. Try a ticker or company name.</p>
              ) : matched.map((company, index) => (
                <CompanyResult key={company.ticker} company={company} active={index === activeIndex} onSelect={() => submit(company.ticker)} />
              ))}
            </div>
          ) : null}
          <p className="mt-3 text-center text-xs text-[var(--muted)]">Search a company to begin your research.</p>
        </div>
      </section>

      <section aria-labelledby="analysis-heading">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">Your research path</p>
            <h2 id="analysis-heading" className="mt-2 text-2xl font-semibold tracking-tight">Choose your analysis</h2>
          </div>
          <p className="hidden text-sm text-[var(--muted)] sm:block">Search company → choose analysis → review</p>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {analysisOptions.map((option) => {
            const Icon = option.icon;
            const isSelected = selectedIntent === option.intent;
            return (
              <article key={option.title} className={`group flex min-h-48 flex-col rounded-[var(--radius-lg)] border p-6 transition-colors ${option.featured ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)]"}`}>
                <div className="flex items-start justify-between gap-4">
                  <span className={`flex h-10 w-10 items-center justify-center rounded-full ${option.featured ? "bg-[var(--accent)] text-[var(--accent-foreground)]" : "bg-[var(--surface-2)] text-[var(--accent)]"}`}>
                    <Icon size={20} aria-hidden="true" />
                  </span>
                  {option.featured ? <span className="text-xs font-semibold text-[var(--accent)]">Recommended</span> : null}
                </div>
                <h3 className="mt-5 text-lg font-semibold">{option.title}</h3>
                <p className="mt-2 max-w-sm text-sm leading-6 text-[var(--muted)]">{option.description}</p>
                <div className="mt-auto pt-5">
                  <Button type="button" variant={option.featured ? "primary" : "secondary"} size="sm" onClick={() => { setSelectedIntent(option.intent); if (query.trim()) submit(matched[activeIndex]?.ticker ?? query, option.intent); }}>
                    {isSelected && query.trim() ? "Open analysis" : option.action}
                    <ArrowRight size={16} aria-hidden="true" />
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {recent.length > 0 ? (
        <section aria-labelledby="recent-heading">
          <div className="flex items-center justify-between gap-4">
            <h2 id="recent-heading" className="text-xl font-semibold tracking-tight">Recent research</h2>
            <span className="text-sm text-[var(--muted)]">Your workspace</span>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            {recent.slice(0, 5).map((entry) => (
              <button key={`${entry.ticker}-${entry.analysedAt}`} type="button" onClick={() => submit(entry.ticker)} className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm font-medium transition-colors hover:border-[var(--accent)] hover:bg-[var(--accent-soft)]">
                <span>{entry.company || entry.ticker}</span>
                <span className="font-mono text-xs text-[var(--muted)]">{entry.ticker}</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <p className="text-center text-xs text-[var(--muted)]">Research framework only. Not investment advice.</p>
    </div>
  );
}

function CompanyResult({ company, active, onSelect }: { company: CompanyEntry; active: boolean; onSelect: () => void }) {
  return (
    <button type="button" role="option" aria-selected={active} onClick={onSelect} className={`flex w-full items-center justify-between gap-4 px-4 py-3 text-left ${active ? "bg-[var(--accent-soft)]" : "hover:bg-[var(--surface-2)]"}`}>
      <span>
        <span className="block font-medium">{company.name}</span>
        <span className="font-mono text-xs text-[var(--muted)]">{company.ticker}</span>
      </span>
      <span className="text-right text-xs text-[var(--muted)]">{company.exchange}</span>
    </button>
  );
}
