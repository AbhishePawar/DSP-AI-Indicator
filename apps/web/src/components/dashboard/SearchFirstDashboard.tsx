"use client";

import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowUpRight,
  BarChart3,
  Building2,
  Clock,
  GitCompareArrows,
  History,
  Loader2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { SearchBox } from "@/components/ds";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { loadRecentAnalyses, type RecentAnalysisEntry } from "@/lib/analysis/recentAnalyses";
import { searchCatalogue, type CompanyEntry } from "@/lib/companies/catalogue";

const SEARCH_DELAY_MS = 180;

export interface ResearchPath {
  title: string;
  description: string;
  intent: string;
  icon: typeof ShieldCheck;
  featured: boolean;
  statusBadge?: string;
}

export const RESEARCH_PATHS: readonly ResearchPath[] = [
  {
    title: "DSP Indicator",
    description: "Buffett-style quality, valuation multiples, and intrinsic value analysis.",
    intent: "dsp_indicator",
    icon: ShieldCheck,
    featured: true,
  },
  {
    title: "Company Research",
    description: "Comprehensive financial statements, margin trends, and business risks.",
    intent: "company_research",
    icon: Building2,
    featured: false,
  },
  {
    title: "Compare Companies",
    description: "Side-by-side fundamentals, valuation benchmarks, and capital efficiency.",
    intent: "compare",
    icon: GitCompareArrows,
    featured: false,
  },
  {
    title: "Deep Research",
    description: "Governed evidence synthesis and multi-source document investigation.",
    intent: "deep_research",
    icon: BarChart3,
    featured: false,
    statusBadge: "Governed / Subject to provider availability",
  },
] as const;

export const SUGGESTED_WORKFLOWS = [
  {
    label: "Analyse HDFC Bank using the DSP Indicator",
    query: "HDFC Bank",
    intent: "dsp_indicator",
    description: "Buffett quality score, loan book fundamentals, and valuation",
  },
  {
    label: "Compare TCS and Infosys",
    query: "TCS",
    intent: "compare",
    description: "Peer benchmark across ROE, operating margin, and multiple",
  },
  {
    label: "Evaluate Reliance Industries business quality",
    query: "RELIANCE",
    intent: "company_research",
    description: "Conglomerate balance sheet, capital allocation, and debt",
  },
  {
    label: "Assess valuation & balance sheet for Titan",
    query: "TITAN",
    intent: "dsp_indicator",
    description: "Consumer discretionary growth runway and multiples",
  },
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
  const isDebouncing = query.trim() !== settledQuery.trim();

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
    if (query.trim()) {
      submit(showResults ? (matched[activeIndex]?.ticker ?? query) : query, intent);
    }
  }

  return (
    <div className="dsp-page-enter mx-auto w-full max-w-5xl space-y-12 pb-16">
      {/* Hero section */}
      <section className="pt-4 text-center sm:pt-10" aria-label="Dashboard overview">
        <div className="mx-auto w-full max-w-2xl">
          <Badge tone="accent" className="mb-4">
            AI-POWERED EQUITY RESEARCH
          </Badge>
          <h1 className="font-[family-name:var(--font-heading)] text-4xl font-medium leading-[1.08] tracking-tight text-[var(--foreground)] sm:text-5xl">
            Research smarter.
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-[var(--muted-foreground)] sm:text-lg">
            Institutional-grade equity analysis, deterministic valuation models, and evidence-driven investment research.
          </p>
        </div>

        {/* Primary Search Container */}
        <div className="relative mx-auto mt-8 max-w-3xl text-left">
          <Card className="border-[var(--border)] bg-[var(--card)] p-2.5 shadow-[var(--shadow-card)]">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <div className="relative flex-1">
                <SearchBox
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={onSearchKeyDown}
                  placeholder="Search a company or ask a research question..."
                  aria-label="Search a company or ask a research question"
                  aria-controls="company-results"
                  aria-autocomplete="list"
                />
                {isDebouncing ? (
                  <span
                    aria-hidden="true"
                    className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]"
                  >
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </span>
                ) : null}
              </div>
              <Button
                variant="primary"
                size="md"
                className="h-11 shrink-0 font-medium sm:h-10"
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
              className="mt-2 max-h-72 w-full divide-y divide-[var(--border)] overflow-y-auto rounded-[var(--card-radius,14px)] border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-lg)]"
            >
              {matched.length === 0 ? (
                <div className="p-5 text-center text-sm text-[var(--muted-foreground)]" role="status">
                  <p className="font-medium text-[var(--foreground)]">No matching securities found</p>
                  <p className="mt-1 text-xs">
                    No listed companies matched &ldquo;{settledQuery}&rdquo;.
                  </p>
                  <p className="mt-2 text-xs opacity-75">
                    Try searching by ticker (e.g. TCS, HDFCBANK, INFY, RELIANCE) or company name.
                  </p>
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

      {/* Research Workflows */}
      <section aria-labelledby="paths-heading">
        <SectionHeader
          title="Start with a research path"
          description="Focused workflows for faster, clearer research."
          as="h2"
          className="mb-5"
        />
        <div className="grid gap-4 sm:grid-cols-2">
          {RESEARCH_PATHS.map((path) => {
            const Icon = path.icon;
            const isSelected = selectedIntent === path.intent;
            return (
              <button
                key={path.title}
                type="button"
                onClick={() => choosePath(path.intent)}
                aria-pressed={isSelected} aria-label={path.title}
                className={`group relative flex min-h-[160px] flex-col rounded-[var(--card-radius,14px)] border p-6 text-left transition-all ${
                  isSelected
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] shadow-[var(--shadow-card)] ring-1 ring-[var(--accent)]"
                    : "border-[var(--border)] bg-[var(--card)] hover:border-[var(--accent)]/50 hover:bg-[var(--surface-2)]"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <span
                    className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                      isSelected
                        ? "bg-[var(--accent)] text-white shadow-sm"
                        : "border border-[var(--border)] bg-[var(--surface-2)] text-[var(--accent)]"
                    }`}
                  >
                    <Icon size={19} aria-hidden="true" />
                  </span>
                  {path.statusBadge ? (
                    <Badge tone="neutral" className="text-[10px]">
                      {path.statusBadge}
                    </Badge>
                  ) : path.featured ? (
                    <Badge tone="accent" className="text-[10px]">
                      Primary
                    </Badge>
                  ) : null}
                </div>

                <span className="mt-4 font-[family-name:var(--font-heading)] text-lg font-medium text-[var(--foreground)]">
                  {path.title}
                </span>
                <span className="mt-1.5 text-sm leading-relaxed text-[var(--muted-foreground)]">
                  {path.description}
                </span>

                <span className="mt-auto flex items-center gap-1.5 pt-4 font-mono text-xs font-medium text-[var(--accent)]">
                  {isSelected ? "Selected workflow" : "Select workflow"} <ArrowUpRight size={14} aria-hidden="true" />
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Suggested Research */}
      <section aria-labelledby="suggested-heading">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles size={17} className="text-[var(--accent)]" aria-hidden="true" />
          <h2
            id="suggested-heading"
            className="font-[family-name:var(--font-heading)] text-xl font-medium tracking-tight text-[var(--foreground)]"
          >
            Suggested research
          </h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {SUGGESTED_WORKFLOWS.map((suggestion) => (
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
              className="group flex min-h-[56px] flex-col justify-between gap-2 rounded-[var(--radius-md,10px)] border border-[var(--border)] bg-[var(--card)] p-4 text-left transition-all hover:border-[var(--accent)] hover:bg-[var(--surface-2)] sm:flex-row sm:items-center"
            >
              <div className="min-w-0 flex-1">
                <span className="block text-sm font-medium text-[var(--foreground)] group-hover:text-[var(--accent)]">
                  {suggestion.label}
                </span>
                <span className="mt-0.5 block truncate text-xs text-[var(--muted-foreground)]">
                  {suggestion.description}
                </span>
              </div>
              <ArrowUpRight
                size={16}
                className="shrink-0 text-[var(--muted-foreground)] transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-[var(--accent)]"
                aria-hidden="true"
              />
            </button>
          ))}
        </div>
      </section>

      {/* Recent Analyses */}
      <section aria-labelledby="recent-heading" className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History size={17} className="text-[var(--accent)]" aria-hidden="true" />
            <h2
              id="recent-heading"
              className="font-[family-name:var(--font-heading)] text-xl font-medium tracking-tight text-[var(--foreground)]"
            >
              Recent research
            </h2>
          </div>
          {recent.length > 0 ? (
            <span className="font-mono text-xs text-[var(--muted-foreground)]">
              {recent.length} {recent.length === 1 ? "session" : "sessions"} recorded
            </span>
          ) : null}
        </div>

        {recent.length === 0 ? (
          <Card className="border-dashed border-[var(--border)] bg-[var(--card)]/40 p-6 text-center">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface-2)] text-[var(--muted-foreground)]">
              <Clock size={18} aria-hidden="true" />
            </div>
            <h3 className="mt-3 text-sm font-medium text-[var(--foreground)]">
              No recent analyses yet
            </h3>
            <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-[var(--muted-foreground)]">
              Securities you analyze will appear here with timestamps and quick shortcuts to resume your research.
            </p>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {recent.slice(0, 6).map((entry) => {
              const formattedDate = entry.analysedAt
                ? new Date(entry.analysedAt).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "Recent session";
              return (
                <Card
                  key={`${entry.ticker}-${entry.analysedAt}`}
                  className="flex flex-col justify-between border-[var(--border)] bg-[var(--card)] p-4 transition-all hover:border-[var(--accent)]/50 hover:shadow-[var(--shadow-card)]"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <span className="truncate font-medium text-[var(--foreground)]">
                        {entry.company || entry.ticker}
                      </span>
                      {entry.exchange ? (
                        <Badge tone="neutral" className="shrink-0 font-mono text-[10px]">
                          {entry.exchange}
                        </Badge>
                      ) : null}
                    </div>
                    <div className="mt-1 flex items-center gap-2 font-mono text-xs">
                      <span className="font-semibold text-[var(--accent)]">{entry.ticker}</span>
                      {entry.recommendation ? (
                        <span className="text-[var(--muted-foreground)]">
                          · {entry.recommendation}
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between border-t border-[var(--border)] pt-3 text-xs">
                    <span className="flex items-center gap-1 text-[var(--muted-foreground)]">
                      <Clock size={12} aria-hidden="true" />
                      <span>{formattedDate}</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => submit(entry.ticker)}
                      className="inline-flex min-h-[44px] items-center gap-1 font-medium text-[var(--accent)] hover:underline"
                      aria-label={`Resume analysis for ${entry.company || entry.ticker}`}
                    >
                      Resume <ArrowUpRight size={13} aria-hidden="true" />
                    </button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </section>

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
      className={`group flex min-h-[48px] w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm transition-colors ${
        active ? "bg-[var(--surface-2)] text-[var(--foreground)]" : "hover:bg-[var(--surface-2)]/50"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate font-medium text-[var(--foreground)]">{company.name}</span>
          <span className="shrink-0 font-mono text-xs font-semibold text-[var(--accent)]">{company.ticker}</span>
        </div>
        {(company.sector || company.industry) ? (
          <p className="mt-0.5 truncate text-xs text-[var(--muted-foreground)]">
            {[company.sector, company.industry].filter(Boolean).join(" · ")}
          </p>
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {company.marketCap ? (
          <span className="hidden font-mono text-[11px] text-[var(--muted-foreground)] sm:inline">
            {company.marketCap}
          </span>
        ) : null}
        <Badge tone="neutral" className="shrink-0 font-mono text-[11px]">
          {company.exchange}
        </Badge>
        <ArrowUpRight
          size={14}
          className="text-[var(--muted-foreground)] transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-[var(--accent)]"
          aria-hidden="true"
        />
      </div>
    </button>
  );
}
