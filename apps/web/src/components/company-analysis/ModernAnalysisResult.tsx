"use client";

import type { ReactNode } from "react";

import { Button } from "@/components/ds";
import type { ResearchView } from "@/lib/research/mapResearchView";

function DataCard({ label, value, tone = "default" }: { label: string; value: string; tone?: "default" | "accent" | "muted" }) {
  return (
    <article className="rounded-[10px] border border-[var(--border)] bg-[var(--surface)] px-4 py-3.5">
      <p className="font-mono text-[10px] uppercase tracking-wider text-[var(--muted)]">{label}</p>
      <p className={`mt-3 font-mono text-lg font-medium tracking-tight ${tone === "accent" ? "text-[var(--accent)]" : tone === "muted" ? "text-[var(--muted)]" : "text-[var(--text)]"}`}>{value}</p>
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
  navigation,
  activeSection = "summary",
  detail,
  simpleMode = false,
  onModeChange,
}: {
  symbol: string;
  query: string;
  setQuery: (value: string) => void;
  onAnalyze: () => void;
  analyzing: boolean;
  view: ResearchView | null;
  error?: string | null;
  disclaimerGate: ReactNode;
  navigation?: ReactNode;
  activeSection?: string;
  detail?: ReactNode;
  simpleMode?: boolean;
  onModeChange?: () => void;
}) {
  const hasResult = Boolean(view);

  return (
    <div data-testid="company-analysis" className="min-h-[calc(100vh-8rem)] bg-[var(--bg)]">
      {disclaimerGate}
      <div className="mx-auto max-w-6xl space-y-8">
        <header data-testid="page-header" className="flex flex-col gap-4 border-b border-[var(--border)] pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-[10px] font-mono uppercase tracking-wider text-[var(--muted)]">DSP AI Indicator / Company analysis</p>
            <h1 data-testid="analysis-title" className="mt-3 font-[family-name:var(--font-display)] text-3xl font-medium tracking-tight text-[var(--fg)]">{view?.company || "Research a company"}</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">Business quality, financial strength, valuation, and evidence — brought together by the DSP research framework.</p>
          </div>
          <form onSubmit={(event) => { event.preventDefault(); onAnalyze(); }} data-testid="analysis-search-form" className="flex w-full max-w-md gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-2">
            <label className="sr-only" htmlFor="analysis-symbol">Company ticker</label>
            <input data-testid="analysis-symbol" id="analysis-symbol" value={query} onChange={(event) => setQuery(event.target.value.toUpperCase())} className="min-w-0 flex-1 bg-transparent px-3 text-sm text-[var(--text)] outline-none placeholder:text-[var(--muted)]" placeholder="Enter company ticker" required />
            <Button data-testid="analysis-submit" type="submit" disabled={analyzing || !query.trim()}>{analyzing ? "Loading…" : hasResult ? "Refresh analysis" : "Analyze"}</Button>
          </form>
        </header>

        {onModeChange && <div className="flex flex-wrap items-center justify-between gap-3 font-mono text-[11px] text-[var(--muted)]"><span data-testid="analysis-research-mode">{simpleMode ? "SIMPLE RESEARCH" : "DSP BUFFETT ANALYSIS"}</span><button data-testid="analysis-switch-mode" onClick={onModeChange} className="rounded-lg border border-[var(--border)] px-3 py-2 text-[var(--accent)] transition-colors hover:border-[var(--accent)]">{simpleMode ? "Open full analysis →" : "Switch to simple research"}</button></div>}

        {error ? <div data-testid="analysis-error" role="alert" className="rounded-xl border border-[var(--danger-border)] bg-[var(--danger-bg)] px-5 py-4 text-sm text-[var(--danger-fg)]">{error}</div> : null}

        {analyzing ? <section data-testid="analysis-loading" role="status" aria-live="polite" className="space-y-4 rounded-[14px] border border-[var(--border)] bg-[var(--surface)] p-8"><p className="text-sm">Preparing your analysis…</p><p className="text-xs text-[var(--muted)]">Checking company evidence and available financial data.</p><div className="h-3 w-2/3 animate-pulse rounded bg-[var(--surface-2)]" /><div className="h-24 animate-pulse rounded-lg bg-[var(--surface-2)]" /></section> : !hasResult ? (
          <section data-testid="analysis-empty" className="mx-auto max-w-[660px] rounded-[14px] border border-[var(--accent)]/30 bg-[var(--surface)] p-7 sm:my-12">
            <p className="font-mono text-[10px] tracking-wider text-[var(--accent)]">{simpleMode ? "QUICK OVERVIEW" : "FLAGSHIP RESEARCH"}</p>
            <h2 className="mt-3 font-[family-name:var(--font-display)] text-lg font-medium text-[var(--fg)]">{simpleMode ? "Simple Company Research" : "DSP Buffett Indicator Analysis"}</h2>
            <p className="mt-3 text-[13px] leading-6 text-[var(--muted)]">Complete evidence-driven analysis — business quality, economic moat, management, earnings, growth, valuation, and margin of safety.</p>
            <p className="mt-4 text-xs text-[var(--muted)]">Enter a company ticker to begin. Results appear only when verified source data is available.</p>
            <div className="mt-6"><Button data-testid="analysis-empty-submit" onClick={onAnalyze} disabled={!query.trim()}>Analyze {query || symbol || "company"}</Button></div>
          </section>
        ) : (
          <div className={`grid items-start gap-5 ${simpleMode ? "" : "lg:grid-cols-[176px_minmax(0,1fr)]"}`}>
            {!simpleMode && navigation}
            <div data-testid="analysis-detail-content" className="min-w-0 space-y-5">
            {!simpleMode && activeSection !== "summary" ? detail : <>
            <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <DataCard label="Recommendation" value={view!.committee.finalRecommendation || "Unavailable"} tone="accent" />
              <DataCard label="Intrinsic value" value={view!.valuation.intrinsicValue} />
              <DataCard label="Margin of safety" value={view!.valuation.marginOfSafety} />
              <DataCard label="Confidence" value={view!.committee.confidence || "Unavailable"} />
            </section>

            <section className="grid gap-6 lg:grid-cols-[1.45fr_0.8fr]">
              <article className="rounded-[14px] border border-[var(--border)] bg-[var(--surface)] p-5">
                <div className="flex flex-col gap-2 border-b border-[var(--border)] pb-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent)]">Evidence ledger</p><h2 className="mt-2 font-[family-name:var(--font-display)] text-lg font-medium text-[var(--text)]">What the research says</h2></div><span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">Research mode</span></div>
                <div className="mt-2"><EvidenceRow label="Business quality" value={view!.businessQuality.label || "Unavailable"} /><EvidenceRow label="Growth outlook" value={view!.growth.label || "Unavailable"} /><EvidenceRow label="Financial strength" value={view!.financialStrength.label || "Unavailable"} /><EvidenceRow label="Recommendation stage" value={view!.recommendationStage.label || "Unavailable"} /></div>
              </article>
              <aside className="rounded-[14px] border border-[var(--border)] bg-[var(--surface)] p-5"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent)]">Decision context</p><h2 className="mt-2 font-[family-name:var(--font-display)] text-lg font-medium text-[var(--text)]">DSP conclusion</h2><p className="mt-5 text-sm leading-6 text-[var(--muted)]">{view!.committee.supportingReasons?.[0] || "Supporting evidence is unavailable."}</p><div className="mt-6 border-t border-[var(--border)] pt-5"><p className="font-mono text-[10px] uppercase tracking-wider text-[var(--muted)]">Risks and limitations</p><p className="mt-3 text-sm leading-6 text-[var(--text)]">{view!.committee.opposingReasons?.[0] || "Risk evidence is unavailable."}</p></div></aside>
            </section>

            <section className="rounded-[14px] border border-[var(--border)] bg-[var(--surface)] p-5"><div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent)]">Audit trail</p><h2 className="mt-2 font-[family-name:var(--font-display)] text-lg font-medium text-[var(--text)]">Data boundaries</h2></div><span className="text-xs text-[var(--muted)]">{view!.analysedAt ? `Updated ${new Date(view!.analysedAt).toLocaleString()}` : "Timestamp unavailable"}</span></div><div className="mt-5 grid gap-3 text-sm text-[var(--muted)] sm:grid-cols-3"><p className="rounded-2xl bg-[var(--bg)] p-4">Verified source outputs stay separate from interpretation.</p><p className="rounded-2xl bg-[var(--bg)] p-4">Calculated values are shown only when returned by the backend.</p><p className="rounded-2xl bg-[var(--bg)] p-4">Unavailable data blocks confidence rather than being filled in.</p></div></section>
          </>}
            </div>
          </div>
        )}
      </div>
    </div>
    );
}
