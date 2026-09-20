"use client";

import type { ReactNode } from "react";

import { Button } from "@/components/ds";
import type { ResearchView } from "@/lib/research/mapResearchView";

function DataCard({ label, value, tone = "default" }: { label: string; value: string; tone?: "default" | "accent" | "muted" }) {
  return (
    <article className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[0_12px_35px_rgba(25,40,35,0.05)]">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">{label}</p>
      <p className={`mt-3 text-xl font-semibold tracking-tight ${tone === "accent" ? "text-[var(--accent)]" : tone === "muted" ? "text-[var(--muted)]" : "text-[var(--text)]"}`}>{value}</p>
    </article>
  );
}

function EvidenceRow({ label, value, children }: { label: string; value: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-b border-[var(--border)] py-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-sm text-[var(--muted)]">{label}</span>
      <span className="text-sm font-medium text-[var(--text)]">{children ?? value}</span>
    </div>
  );
}

export function ModernAnalysisResult({
  symbol,
  query,
  setQuery,
  onAnalyze,
  analyzing,
  view,
  error,
  disclaimerGate,
}: {
  symbol: string;
  query: string;
  setQuery: (value: string) => void;
  onAnalyze: () => void;
  analyzing: boolean;
  view: ResearchView | null;
  error?: string | null;
  disclaimerGate: ReactNode;
}) {
  const hasResult = Boolean(view);

  return (
    <main className="min-h-[calc(100vh-5rem)] bg-[var(--bg)] px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
      {disclaimerGate}
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="flex flex-col gap-6 border-b border-[var(--border)] pb-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">DSP AI Indicator / Research result</p>
            <h1 className="mt-3 text-balance text-4xl font-semibold tracking-[-0.04em] text-[var(--text)] sm:text-5xl">{view?.company || "Company analysis"}</h1>
            <p className="mt-3 max-w-2xl text-pretty text-base leading-7 text-[var(--muted)]">A source-led analysis surface for {view?.ticker || symbol || "the selected company"}. Every output below is presented as reported, calculated, or unavailable — never invented.</p>
          </div>
          <div className="flex w-full max-w-md gap-2 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-2 shadow-[0_12px_35px_rgba(25,40,35,0.05)]">
            <label className="sr-only" htmlFor="analysis-symbol">Company ticker</label>
            <input id="analysis-symbol" value={query} onChange={(event) => setQuery(event.target.value.toUpperCase())} className="min-w-0 flex-1 bg-transparent px-3 text-base text-[var(--text)] outline-none placeholder:text-[var(--muted)]" placeholder="Enter ticker" />
            <Button onClick={onAnalyze} disabled={analyzing || !query.trim()}>{analyzing ? "Loading…" : "Refresh analysis"}</Button>
          </div>
        </header>

        {error ? <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-900">{error}</div> : null}

        {!hasResult ? (
          <section className="rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-8 sm:p-12">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">No result loaded</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-[var(--text)]">Run a company analysis to begin.</h2>
            <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--muted)]">The result page is intentionally empty until an authenticated backend payload is available. This prevents stale or fabricated numbers from appearing as research.</p>
            <div className="mt-6"><Button onClick={onAnalyze} disabled={analyzing || !query.trim()}>{analyzing ? "Loading…" : `Analyze ${query || symbol}`}</Button></div>
          </section>
        ) : (
          <>
            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <DataCard label="Recommendation" value={view!.committee.finalRecommendation || "Unavailable"} tone="accent" />
              <DataCard label="Intrinsic value" value={view!.valuation.intrinsicValue} />
              <DataCard label="Margin of safety" value={view!.valuation.marginOfSafety} />
              <DataCard label="Confidence" value={view!.committee.confidence || "Unavailable"} />
            </section>

            <section className="grid gap-6 lg:grid-cols-[1.45fr_0.8fr]">
              <article className="rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8">
                <div className="flex flex-col gap-2 border-b border-[var(--border)] pb-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent)]">Evidence ledger</p><h2 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text)]">What the research says</h2></div><span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">Research mode</span></div>
                <div className="mt-2"><EvidenceRow label="Business quality" value={view!.businessQuality.label || "Unavailable"} /><EvidenceRow label="Growth outlook" value={view!.growth.label || "Unavailable"} /><EvidenceRow label="Financial strength" value={view!.financialStrength.label || "Unavailable"} /><EvidenceRow label="Recommendation stage" value={view!.recommendationStage.label || "Unavailable"} /></div>
              </article>
              <aside className="rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent)]">Decision context</p><h2 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text)]">Committee view</h2><p className="mt-5 text-sm leading-6 text-[var(--muted)]">{view!.committee.supportingReasons?.[0] || "Supporting evidence is unavailable."}</p><div className="mt-6 border-t border-[var(--border)] pt-5"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">Risks / opposing evidence</p><p className="mt-3 text-sm leading-6 text-[var(--text)]">{view!.committee.opposingReasons?.[0] || "No opposing evidence reported."}</p></div></aside>
            </section>

            <section className="rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8"><div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent)]">Audit trail</p><h2 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text)]">Data boundaries</h2></div><span className="text-xs text-[var(--muted)]">{view!.analysedAt ? `Updated ${new Date(view!.analysedAt).toLocaleString()}` : "Timestamp unavailable"}</span></div><div className="mt-5 grid gap-3 text-sm text-[var(--muted)] sm:grid-cols-3"><p className="rounded-2xl bg-[var(--bg)] p-4">Verified source outputs stay separate from interpretation.</p><p className="rounded-2xl bg-[var(--bg)] p-4">Calculated values are shown only when returned by the backend.</p><p className="rounded-2xl bg-[var(--bg)] p-4">Unavailable data blocks confidence rather than being filled in.</p></div></section>
          </>
        )}
      </div>
    </main>
    );
}
