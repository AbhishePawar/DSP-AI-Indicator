"use client";

import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowUpRight,
  BarChart3,
  Building2,
  GitCompareArrows,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import { SearchBox } from "@/components/ds";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { loadRecentAnalyses, type RecentAnalysisEntry } from "@/lib/analysis/recentAnalyses";
import { searchCatalogue, type CompanyEntry } from "@/lib/companies/catalogue";

const SEARCH_DELAY_MS = 180;

const researchPaths = [
  {
    title: "Company Research",
    description: "Understand the business, financials, and key risks.",
    intent: "company_research",
    icon: Building2,
    featured: false,
  },
  {
    title: "DSP Indicator",
    description: "Buffett-style quality, value, and business analysis.",
    intent: "dsp_indicator",
    icon: ShieldCheck,
    featured: true,
  },
  {
    title: "Compare Companies",
    description: "Compare businesses across fundamentals and valuation.",
    intent: "compare",
    icon: GitCompareArrows,
    featured: false,
  },
  {
    title: "Deep Research",
    description: "Investigate filings, reports, and supporting evidence.",
    intent: "deep_research",
    icon: BarChart3,
    featured: false,
  },
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

  function choosePath(intent: string) {
    setSelectedIntent(intent);
    if (query.trim()) submit(matched[activeIndex]?.ticker ?? query, intent);
  }

  return (
    <div className="dsp-page-enter mx-auto w-full max-w-5xl space-y-12 pb-16">
      {/* Hero section */}
      <section className="pt-4 text-center sm:pt-10">
        <div className="mx-auto w-full max-w-2xl">
          <Badge tone="accent" className="mb-4">
            AI-POWERED EQUITY RESEARCH
          </Badge>
          <h1 className="font-[family-name:var(--font-heading)] text-4xl font-medium leading-[1.08] tracking-tight text-[var(--foreground)] sm:text-5xl">
            Research smarter.
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-[var(--muted-foreground)] sm:text-lg">
            Analyse companies, compare businesses, and uncover value with evidence-driven research.
          </p>
        </div>

        {/* Search Bar Container */}
        <div className="relative mx-auto mt-8 max-w-3xl text-left">
          <Card className="border-[var(--border)] bg-[var(--card)] p-2 shadow-[var(--shadow-card)]">
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <SearchBox
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={onSearchKeyDown}
                  placeholder="Search a company or ask a research question..."
                  aria-label="Search a company or ask a research question"
                  aria-controls="company-results"
                  aria-autocomplete="list"
                />
              </div>
              <Button
                variant="primary"
                size="md"
                className="hidden shrink-0 font-medium sm:inline-flex"
                onClick={() => submit(showResults ? (matched[activeIndex]?.ticker ?? query) : query)}
              >
                Analyze
              </Button>
            </div>
          </Card>

          {/* Search Dropdown Results */}
          {showResults ? (
            <div
              id="company-results"
              role="listbox"
              aria-label="Company search results"
              className="mt-2 max-h-56 w-full divide-y divide-[var(--border)] overflow-y-auto rounded-[var(--card-radius,14px)] border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-lg)]"
            >
              {matched.length === 0 ? (
                <div className="p-4 text-center text-sm text-[var(--muted-foreground)]">
                  <p>No matching company found.</p>
                  <p className="mt-1 text-xs opacity-75">Try searching by ticker (e.g. TCS, HDFCBANK) or company name.</p>
                </div>
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

          <p className="mt-3 text-xs text-[var(--muted-foreground)]">
            Search a company, then choose the research path that fits your question.
          </p>
        </div>
      </section>

      {/* Research Paths */}
      <section aria-labelledby="paths-heading">
        <SectionHeader
          title="Start with a research path"
          description="Focused workflows for faster, clearer research."
          as="h2"
          className="mb-5"
        />
        <div className="grid gap-4 sm:grid-cols-2">
          {researchPaths.map((path) => {
            const Icon = path.icon;
            return (
              <button
                key={path.title}
                type="button"
                onClick={() => choosePath(path.intent)}
                className={`group flex min-h-44 flex-col rounded-[var(--card-radius,14px)] border p-6 text-left transition-all ${
                  path.featured
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] shadow-[var(--shadow-card)]"
                    : "border-[var(--border)] bg-[var(--card)] hover:border-[var(--accent)]/50 hover:bg-[var(--surface-2)]"
                }`}
              >
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                    path.featured
                      ? "bg-[var(--accent)] text-white shadow-sm"
                      : "border border-[var(--border)] bg-[var(--surface-2)] text-[var(--accent)]"
                  }`}
                >
                  <Icon size={19} aria-hidden="true" />
                </span>
                <span className="mt-5 font-[family-name:var(--font-heading)] text-lg font-medium text-[var(--foreground)]">
                  {path.title}
                </span>
                <span className="mt-1.5 text-sm leading-5 text-[var(--muted-foreground)]">
                  {path.description}
                </span>
                {path.featured ? (
                  <span className="mt-auto flex items-center gap-1.5 pt-4 font-mono text-xs font-medium text-[var(--accent)]">
                    Run DSP Indicator <ArrowUpRight size={14} aria-hidden="true" />
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      </section>

      {/* Suggested Research */}
      <section aria-labelledby="suggested-heading">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles size={17} className="text-[var(--accent)]" aria-hidden="true" />
          <h2 id="suggested-heading" className="font-[family-name:var(--font-heading)] text-xl font-medium tracking-tight text-[var(--foreground)]">
            Suggested research
          </h2>
        </div>
        <div className="grid gap-2.5 sm:grid-cols-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion.label}
              type="button"
              onClick={() => {
                setSelectedIntent(suggestion.intent);
                if (suggestion.query) {
                  setQuery(suggestion.query);
                  submit(suggestion.query, suggestion.intent);
                }
              }}
              className="flex items-center justify-between gap-4 rounded-[var(--radius-md,10px)] border border-[var(--border)] bg-[var(--card)] px-4 py-3.5 text-left text-sm text-[var(--foreground)] transition-colors hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"
            >
              <span>{suggestion.label}</span>
              <ArrowUpRight size={16} className="shrink-0 text-[var(--accent)]" aria-hidden="true" />
            </button>
          ))}
        </div>
      </section>

      {/* Recent Research */}
      {recent.length > 0 ? (
        <section aria-labelledby="recent-heading">
          <h2 id="recent-heading" className="mb-3 font-[family-name:var(--font-heading)] text-xl font-medium tracking-tight text-[var(--foreground)]">
            Recent research
          </h2>
          <div className="flex flex-wrap gap-2.5">
            {recent.slice(0, 5).map((entry) => (
              <button
                key={`${entry.ticker}-${entry.analysedAt}`}
                type="button"
                onClick={() => submit(entry.ticker)}
                className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--card)] px-3.5 py-1.5 text-sm font-medium text-[var(--foreground)] transition-colors hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"
              >
                <span>{entry.company || entry.ticker}</span>
                <span className="font-mono text-xs text-[var(--muted-foreground)]">{entry.ticker}</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <p className="text-center font-mono text-xs text-[var(--muted-foreground)]">
        Research tools only — not investment advice.
      </p>
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
      className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm transition-colors ${
        active ? "bg-[var(--surface-2)] text-[var(--foreground)]" : "hover:bg-[var(--surface-2)]/50"
      }`}
    >
      <div>
        <span className="block font-medium text-[var(--foreground)]">{company.name}</span>
        <span className="font-mono text-xs text-[var(--muted-foreground)]">{company.ticker}</span>
      </div>
      <Badge tone="neutral" className="shrink-0">
        {company.exchange}
      </Badge>
    </button>
  );
}
