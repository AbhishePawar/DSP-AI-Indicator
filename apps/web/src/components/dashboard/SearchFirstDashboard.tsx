"use client";

import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpRight, BarChart3, Building2, GitCompareArrows, ShieldCheck, Sparkles } from "lucide-react";
import { SearchBox } from "@/components/ds";
import { loadRecentAnalyses, type RecentAnalysisEntry } from "@/lib/analysis/recentAnalyses";
import { searchCatalogue, type CompanyEntry } from "@/lib/companies/catalogue";

const SEARCH_DELAY_MS = 180;

const researchPaths = [
  { title: "Company Research", description: "Understand the business, financials, and key risks.", intent: "company_research", icon: Building2, featured: false },
  { title: "DSP Indicator", description: "Buffett-style quality, value, and business analysis.", intent: "dsp_indicator", icon: ShieldCheck, featured: true },
  { title: "Compare Companies", description: "Compare businesses across fundamentals and valuation.", intent: "compare", icon: GitCompareArrows, featured: false },
  { title: "Deep Research", description: "Investigate filings, reports, and supporting evidence.", intent: "deep_research", icon: BarChart3, featured: false },
] as const;

const suggestions = [
  { label: "Analyse HDFC Bank using the DSP Indicator", query: "HDFC Bank", intent: "dsp_indicator" },
  { label: "Compare TCS and Infosys", query: "TCS", intent: "compare" },
  { label: "Find companies with strong ROE and low debt", query: "", intent: "company_research" },
  { label: "Is this company financially strong?", query: "", intent: "deep_research" },
] as const;

export function SearchFirstDashboard() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [settledQuery, setSettledQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const [selectedIntent, setSelectedIntent] = useState("dsp_indicator");
  const [recent] = useState<RecentAnalysisEntry[]>(loadRecentAnalyses);
  const matched = useMemo(() => searchCatalogue(settledQuery).slice(0, 8), [settledQuery]);
  const showResults = settledQuery.trim().length > 0;

  useEffect(() => {
    const timer = window.setTimeout(() => { setSettledQuery(query); setActiveIndex(0); }, SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  function submit(symbol: string, intent = selectedIntent) {
    const ticker = symbol.trim().toUpperCase();
    if (!ticker) return;
    router.push(`/analysis?symbol=${encodeURIComponent(ticker)}&intent=${encodeURIComponent(intent)}`);
  }

  function onSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
    if (event.key === "ArrowDown" && matched.length > 0) { event.preventDefault(); setActiveIndex((index) => (index + 1) % matched.length); }
    else if (event.key === "ArrowUp" && matched.length > 0) { event.preventDefault(); setActiveIndex((index) => (index - 1 + matched.length) % matched.length); }
    else if (event.key === "Enter") { event.preventDefault(); submit(showResults ? (matched[activeIndex]?.ticker ?? query) : query); }
    else if (event.key === "Escape") setQuery("");
  }

  function choosePath(intent: string) {
    setSelectedIntent(intent);
    if (query.trim()) submit(matched[activeIndex]?.ticker ?? query, intent);
  }

  return (
    <div className="dsp-page-enter mx-auto max-w-5xl space-y-12 pb-12">
      <section className="pt-4 text-center sm:pt-10">
        <div className="mx-auto max-w-2xl">
          <p className="text-sm font-semibold tracking-[0.16em] text-[var(--accent)]">AI-POWERED EQUITY RESEARCH</p>
          <h1 className="mt-4 font-[family-name:var(--font-display)] text-4xl leading-[1.08] tracking-tight sm:text-5xl">Research smarter.</h1>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-[var(--muted)] sm:text-lg">Analyse companies, compare businesses, and uncover value with evidence-driven research.</p>
        </div>
        <div className="relative mx-auto mt-8 max-w-3xl text-left">
          <SearchBox value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={onSearchKeyDown} placeholder="Search a company or ask a research question..." aria-label="Search a company or ask a research question" aria-controls="company-results" aria-autocomplete="list" />
          {showResults ? <div id="company-results" role="listbox" aria-label="Company search results" className="absolute z-10 mt-2 w-full overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-md)]">
            {matched.length === 0 ? <p className="p-4 text-sm text-[var(--muted)]">No matching company. Try a ticker or company name.</p> : matched.map((company, index) => <CompanyResult key={company.ticker} company={company} active={index === activeIndex} onSelect={() => submit(company.ticker)} />)}
          </div> : null}
          <p className="mt-3 text-xs text-[var(--muted)]">Search a company, then choose the research path that fits your question.</p>
        </div>
      </section>

      <section aria-labelledby="paths-heading">
        <h2 id="paths-heading" className="text-xl font-semibold tracking-tight">Start with a research path</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">Focused workflows for faster, clearer research.</p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {researchPaths.map((path) => { const Icon = path.icon; return <button key={path.title} type="button" onClick={() => choosePath(path.intent)} className={`group flex min-h-44 flex-col rounded-[var(--radius-lg)] border p-5 text-left transition-colors ${path.featured ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)]"}`}>
            <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${path.featured ? "bg-[var(--accent)] text-[var(--accent-foreground)]" : "bg-[var(--surface-2)] text-[var(--accent)]"}`}><Icon size={18} aria-hidden="true" /></span>
            <span className="mt-5 text-base font-semibold">{path.title}</span>
            <span className="mt-2 text-sm leading-5 text-[var(--muted)]">{path.description}</span>
            {path.featured ? <span className="mt-auto flex items-center gap-1 pt-4 text-xs font-semibold text-[var(--accent)]">Run DSP Indicator <ArrowUpRight size={14} aria-hidden="true" /></span> : null}
          </button>; })}
        </div>
      </section>

      <section aria-labelledby="suggested-heading">
        <div className="flex items-center gap-2"><Sparkles size={17} className="text-[var(--accent)]" aria-hidden="true" /><h2 id="suggested-heading" className="text-xl font-semibold tracking-tight">Suggested research</h2></div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {suggestions.map((suggestion) => <button key={suggestion.label} type="button" onClick={() => { setSelectedIntent(suggestion.intent); if (suggestion.query) { setQuery(suggestion.query); submit(suggestion.query, suggestion.intent); } }} className="flex items-center justify-between gap-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-left text-sm transition-colors hover:border-[var(--accent)] hover:bg-[var(--accent-soft)]"><span>{suggestion.label}</span><ArrowUpRight size={16} className="shrink-0 text-[var(--accent)]" aria-hidden="true" /></button>)}
        </div>
      </section>

      {recent.length > 0 ? <section aria-labelledby="recent-heading"><h2 id="recent-heading" className="text-xl font-semibold tracking-tight">Recent research</h2><div className="mt-4 flex flex-wrap gap-3">{recent.slice(0, 5).map((entry) => <button key={`${entry.ticker}-${entry.analysedAt}`} type="button" onClick={() => submit(entry.ticker)} className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm font-medium transition-colors hover:border-[var(--accent)] hover:bg-[var(--accent-soft)]"><span>{entry.company || entry.ticker}</span><span className="font-mono text-xs text-[var(--muted)]">{entry.ticker}</span></button>)}</div></section> : null}
      <p className="text-center text-xs text-[var(--muted)]">Research tools only — not investment advice.</p>
    </div>
  );
}

function CompanyResult({ company, active, onSelect }: { company: CompanyEntry; active: boolean; onSelect: () => void }) {
  return <button type="button" role="option" aria-selected={active} onClick={onSelect} className={`flex w-full items-center justify-between gap-4 px-4 py-3 text-left ${active ? "bg-[var(--accent-soft)]" : "hover:bg-[var(--surface-2)]"}`}><span><span className="block font-medium">{company.name}</span><span className="font-mono text-xs text-[var(--muted)]">{company.ticker}</span></span><span className="text-right text-xs text-[var(--muted)]">{company.exchange}</span></button>;
}

