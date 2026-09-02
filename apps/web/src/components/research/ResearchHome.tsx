"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

/** RC3-003 — section labels only; navigation requires an explicit ticker. */
const CATEGORIES = [
  { label: "Valuation", hash: "valuation" },
  { label: "Business Quality", hash: "business-quality" },
  { label: "Financial Strength", hash: "financial-strength" },
  { label: "Management Quality", hash: "management" },
  { label: "Earnings Quality", hash: "earnings" },
  { label: "Growth Quality", hash: "growth" },
  { label: "Investment Committee", hash: "committee" },
] as const;

export function ResearchHome() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function onSearch(e: FormEvent) {
    e.preventDefault();
    const ticker = query.trim().toUpperCase();
    if (!ticker) return;
    router.push(`/research/${encodeURIComponent(ticker)}`);
  }

  const ticker = query.trim().toUpperCase();

  return (
    <div className="space-y-12">
      {/* Page header — document style */}
      <div className="border-b border-[var(--border)] pb-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">
          DSP AI Indicator
        </p>
        <h1 className="font-[family-name:var(--font-display)] text-3xl sm:text-4xl tracking-tight text-[var(--fg)]">
          Company Research
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)] max-w-xl leading-relaxed">
          Structured research views over composition pipeline results. Analyse once, review all intelligence.
        </p>
      </div>

      {/* Search section — document style, no card */}
      <section aria-label="Open research report">
        <div className="mb-4 border-b border-[var(--border)] pb-3">
          <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
            Open Research Report
          </h2>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            Enter a ticker symbol to open its research report.
          </p>
        </div>
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:gap-8">
          <div className="flex-1 max-w-md">
            <form onSubmit={onSearch} className="flex flex-wrap gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ticker symbol (e.g. TCS, INFY)"
                aria-label="Ticker search"
                className="min-w-[10rem] flex-1"
              />
              <Button type="submit" disabled={!ticker}>
                Open Research
              </Button>
            </form>
            <p className="mt-3 text-xs text-[var(--muted)]">
              Run analysis in{" "}
              <Link href="/analysis" className="underline hover:text-[var(--fg)] transition-colors">
                Company Analysis
              </Link>{" "}
              first, then open the research report for that ticker.
            </p>
          </div>

          {/* Primary journey — inline, no card */}
          <div className="shrink-0 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">
              Primary Journey
            </p>
            <Link href="/analysis">
              <Button variant="secondary" className="w-full sm:w-auto">
                Company Analysis
              </Button>
            </Link>
            <Link href="/research/institutional">
              <Button variant="ghost" className="w-full sm:w-auto">
                Research Reports
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Research activity — document style */}
      <section aria-label="Your research activity">
        <div className="mb-4 border-b border-[var(--border)] pb-3">
          <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
            Your Research Activity
          </h2>
        </div>
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-3">
          <EmptyStateItem
            title="Recent Analyses"
            description="Your recently analysed companies will appear here after you run an analysis."
          />
          <EmptyStateItem
            title="Pinned Companies"
            description="Companies you pin from a research report will appear here for quick access."
          />
          <EmptyStateItem
            title="Recently Viewed"
            description="Research reports you have opened will appear here."
          />
        </div>
      </section>

      {/* Research categories — document style */}
      <section aria-label="Research categories">
        <div className="mb-4 border-b border-[var(--border)] pb-3">
          <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
            {ticker
              ? `Jump into ${ticker} research sections`
              : "Research Sections"}
          </h2>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            {ticker
              ? `Navigate directly to a section of the ${ticker} research report.`
              : "Enter a ticker above, then jump directly to any research section."}
          </p>
        </div>
        <ul className="grid gap-2 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {CATEGORIES.map((cat, i) => (
            <li key={cat.label}>
              {ticker ? (
                <Link
                  href={`/research/${encodeURIComponent(ticker)}#${cat.hash}`}
                  className="flex items-center gap-3 py-2.5 pr-3 text-sm transition-colors hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-sm group"
                >
                  <span
                    className="font-mono text-xs text-[var(--accent)] shrink-0 w-5 text-right"
                    aria-hidden
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="inline-block h-px flex-1 bg-[var(--border)] group-hover:bg-[var(--accent)] transition-colors" aria-hidden />
                  <span className="text-[var(--fg)]">{cat.label}</span>
                </Link>
              ) : (
                <span className="flex items-center gap-3 py-2.5 pr-3 text-sm text-[var(--muted)] cursor-default select-none">
                  <span
                    className="font-mono text-xs text-[var(--border)] shrink-0 w-5 text-right"
                    aria-hidden
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="inline-block h-px flex-1 bg-[var(--border)]" aria-hidden />
                  <span>{cat.label}</span>
                </span>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function EmptyStateItem({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="border-l-2 border-[var(--border)] pl-4 py-1">
      <h3 className="text-sm font-semibold text-[var(--fg)] mb-1">{title}</h3>
      <p className="text-sm text-[var(--muted)] leading-relaxed">{description}</p>
    </div>
  );
}
