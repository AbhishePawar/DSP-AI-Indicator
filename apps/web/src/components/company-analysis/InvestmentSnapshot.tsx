"use client";

import { Badge } from "@/components/ds";
import { formatPct } from "@/lib/intelligence/mapResponse";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { cn } from "@/lib/utils";
import { SectionCard, FieldRow } from "./WorkspacePrimitives";

function available(value: string | null | undefined) {
  return Boolean(value && value !== "Unavailable" && value !== "—");
}

function tone(value: string) {
  const normalized = value.toLowerCase();
  if (normalized.includes("buy") || normalized.includes("strong"))
    return "accent" as const;
  if (normalized.includes("sell") || normalized.includes("risk"))
    return "danger" as const;
  return "outline" as const;
}

export function InvestmentSnapshot({ view }: { view: ResearchView }) {
  const recommendation = view.recommendation || "Data unavailable.";
  const confidence = formatPct(view.recommendationConfidence);
  const price = view.valuation.currentPrice;
  const intrinsic = view.valuation.intrinsicValue;
  const coverage = view.transparency.qualityBadges.length
    ? "Evidence linked"
    : view.ok
      ? "Research returned"
      : "Evidence unavailable";

  return (
    <section
      aria-labelledby="investment-snapshot-title"
      className="dsp-page-enter overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-md)]"
    >
      <div className="border-b border-[var(--border)] bg-[var(--surface-2)]/50 px-5 py-4 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--accent)]">
              Investment snapshot
            </p>
            <h2
              id="investment-snapshot-title"
              className="font-[var(--font-display)] text-2xl font-semibold tracking-tight sm:text-3xl"
            >
              {view.company}
            </h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {view.ticker} · {view.exchange} · server-returned research view
            </p>
          </div>
          <Badge variant={tone(recommendation)}>{recommendation}</Badge>
        </div>
      </div>
      <div className="grid gap-px bg-[var(--border)] sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-[var(--surface)] px-5 py-4">
          <p className="text-xs text-[var(--muted)]">DSP view</p>
          <p className="mt-1 text-lg font-semibold">{recommendation}</p>
          <p className="mt-1 text-xs text-[var(--muted)]">Recommendation, not advice</p>
        </div>
        <div className="bg-[var(--surface)] px-5 py-4">
          <p className="text-xs text-[var(--muted)]">Confidence</p>
          <p className="mt-1 text-lg font-semibold">
            {confidence || "Data unavailable."}
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">As returned by the API</p>
        </div>
        <div className="bg-[var(--surface)] px-5 py-4">
          <p className="text-xs text-[var(--muted)]">Current price</p>
          <p className="mt-1 text-lg font-semibold">{price}</p>
          <p className="mt-1 text-xs text-[var(--muted)]">Authenticated quote only</p>
        </div>
        <div className="bg-[var(--surface)] px-5 py-4">
          <p className="text-xs text-[var(--muted)]">Intrinsic value</p>
          <p className="mt-1 text-lg font-semibold">{intrinsic}</p>
          <p className="mt-1 text-xs text-[var(--muted)]">Server valuation only</p>
        </div>
      </div>
      <div className="grid gap-4 px-5 py-4 sm:grid-cols-3 sm:px-6">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Why it matters
          </p>
          <p className="mt-1 text-sm leading-6">
            {available(view.committeeDecision)
              ? view.committeeDecision
              : "Committee rationale is unavailable."}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Primary opportunity
          </p>
          <p className="mt-1 text-sm leading-6">
            {view.strengths[0] || "Data unavailable."}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Primary risk
          </p>
          <p className="mt-1 text-sm leading-6">
            {view.risks[0] || "Data unavailable."}
          </p>
        </div>
      </div>
      <div className="border-t border-[var(--border)] px-5 py-3 sm:px-6">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-[var(--muted)]">
          <span>
            <span className="terminal-dot mr-2" aria-hidden="true" />
            {coverage}
          </span>
          <span>Badges: {view.transparency.qualityBadges.length}</span>
          <span>Updated: {view.analysedAt || "Data unavailable."}</span>
        </div>
      </div>
    </section>
  );
}

export function SnapshotSignals({ view }: { view: ResearchView }) {
  return (
    <SectionCard
      title="Signal summary"
      description="Display-only stage signals from the research response."
    >
      <dl>
        <FieldRow label="Business quality" value={view.businessQualityLabel} />
        <FieldRow label="Economic moat" value={view.moat.label} />
        <FieldRow label="Margin of safety" value={view.valuation.marginOfSafety} />
        <FieldRow
          label="Research confidence"
          value={formatPct(view.recommendationConfidence)}
        />
      </dl>
    </SectionCard>
  );
}

export const snapshotClassNames = cn;
