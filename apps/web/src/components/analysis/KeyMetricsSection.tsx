"use client";

/**
 * KeyMetricsSection — compact terminal-style card grid for the Analysis Page.
 *
 * Data sources (all existing, no mock data):
 *   - view.snapshot   → company name, ticker, exchange, sector, market cap, price
 *   - view.conclusion → research conclusion, margin of safety, intrinsic value, confidence
 *   - view.valuation  → valuation summary
 *   - view.dashboard  → scores, top opportunity, biggest risk
 *
 * Rendering rules:
 *   - Available fields: show value with accent colour
 *   - Unavailable fields: show "—" in muted colour (never invent values)
 *   - Terminal aesthetic: monospace values, subtle borders, compact rows
 */

import type { AnalysisWorkspaceView, DisplayField } from "@/lib/analysis/types";

/* ─── Helpers ────────────────────────────────────────────────────── */

function displayValue(
  field: DisplayField<string | string[] | number>,
): string {
  if (field.presence === "unavailable" || field.value == null) return "—";
  if (Array.isArray(field.value)) return field.value.join(" · ");
  return String(field.value);
}

function isAvailable(field: DisplayField<unknown>): boolean {
  return field.presence === "available" && field.value != null;
}

/* ─── Terminal metric cell ───────────────────────────────────────── */

interface MetricCellProps {
  label: string;
  value: string;
  available: boolean;
  /** Optional sub-label shown below the value */
  sub?: string;
  /** Span 2 columns on wider grids */
  wide?: boolean;
}

function MetricCell({ label, value, available: avail, sub, wide }: MetricCellProps) {
  return (
    <div
      className={[
        "flex flex-col gap-1 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2.5",
        wide ? "sm:col-span-2" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </span>
      <span
        className={[
          "font-mono text-sm font-semibold leading-tight",
          avail ? "text-[var(--accent)]" : "text-[var(--muted)]",
        ].join(" ")}
      >
        {value}
      </span>
      {sub ? (
        <span className="text-[10px] text-[var(--muted)]">{sub}</span>
      ) : null}
    </div>
  );
}

/* ─── Section divider row ────────────────────────────────────────── */

function GroupLabel({ label }: { label: string }) {
  return (
    <div className="col-span-full flex items-center gap-2 pt-1">
      <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </span>
      <div className="h-px flex-1 bg-[var(--border)]" />
    </div>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

export function KeyMetricsSection({ view }: { view: AnalysisWorkspaceView }) {
  const { snapshot, conclusion, valuation, dashboard } = view;

  /* Company identity */
  const companyName = displayValue(snapshot.companyName);
  const ticker = displayValue(snapshot.ticker);
  const exchange = displayValue(snapshot.exchange);
  const sector = displayValue(snapshot.sector);
  const industry = displayValue(snapshot.industry);

  /* Price & market */
  const cmp = displayValue(snapshot.currentMarketPrice);
  const marketCap = displayValue(snapshot.marketCap);
  const week52High = displayValue(snapshot.week52High);
  const week52Low = displayValue(snapshot.week52Low);

  /* Research output */
  const researchConclusion = displayValue(dashboard.researchConclusion);
  const researchConfidence = displayValue(dashboard.researchConfidence);
  const intrinsicValue = displayValue(conclusion.intrinsicValueRange);
  const marginOfSafety = displayValue(conclusion.marginOfSafety);
  const valuationSummary = displayValue(valuation.summary);
  const topOpportunity = displayValue(dashboard.topOpportunity);
  const biggestRisk = displayValue(dashboard.biggestRisk);

  /* Scores */
  const businessScore = displayValue(dashboard.businessScore);
  const financialScore = displayValue(dashboard.financialScore);
  const valuationScore = displayValue(dashboard.valuationScore);
  const riskScore = displayValue(dashboard.riskScore);
  const managementScore = displayValue(dashboard.managementScore);
  const growthScore = displayValue(dashboard.growthScore);

  return (
    <div className="space-y-3">
      {/* Header bar */}
      <div className="flex items-center justify-between rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-base font-bold text-[var(--accent)]">
            {ticker}
          </span>
          {exchange !== "—" && (
            <span className="rounded bg-[var(--surface)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--muted)]">
              {exchange}
            </span>
          )}
          {companyName !== ticker && companyName !== "—" && (
            <span className="text-sm text-[var(--fg)]">{companyName}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {sector !== "—" && (
            <span className="text-[10px] text-[var(--muted)]">{sector}</span>
          )}
          {industry !== "—" && sector !== industry && (
            <span className="text-[10px] text-[var(--muted)]">· {industry}</span>
          )}
        </div>
      </div>

      {/* Metric grid */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">

        {/* ── Market data ── */}
        <GroupLabel label="Market" />

        <MetricCell
          label="CMP"
          value={cmp}
          available={isAvailable(snapshot.currentMarketPrice)}
          sub="Current Market Price"
        />
        <MetricCell
          label="Market Cap"
          value={marketCap}
          available={isAvailable(snapshot.marketCap)}
        />
        <MetricCell
          label="52W High"
          value={week52High}
          available={isAvailable(snapshot.week52High)}
        />
        <MetricCell
          label="52W Low"
          value={week52Low}
          available={isAvailable(snapshot.week52Low)}
        />

        {/* ── Research output ── */}
        <GroupLabel label="Research Output" />

        <MetricCell
          label="Conclusion"
          value={researchConclusion}
          available={isAvailable(dashboard.researchConclusion)}
        />
        <MetricCell
          label="Confidence"
          value={researchConfidence}
          available={isAvailable(dashboard.researchConfidence)}
        />
        <MetricCell
          label="Intrinsic Value"
          value={intrinsicValue}
          available={isAvailable(conclusion.intrinsicValueRange)}
          sub="Range estimate"
        />
        <MetricCell
          label="Margin of Safety"
          value={marginOfSafety}
          available={isAvailable(conclusion.marginOfSafety)}
        />

        {/* ── Scores ── */}
        <GroupLabel label="Scores" />

        <MetricCell
          label="Business"
          value={businessScore}
          available={isAvailable(dashboard.businessScore)}
        />
        <MetricCell
          label="Financial"
          value={financialScore}
          available={isAvailable(dashboard.financialScore)}
        />
        <MetricCell
          label="Valuation"
          value={valuationScore}
          available={isAvailable(dashboard.valuationScore)}
        />
        <MetricCell
          label="Risk"
          value={riskScore}
          available={isAvailable(dashboard.riskScore)}
        />
        <MetricCell
          label="Management"
          value={managementScore}
          available={isAvailable(dashboard.managementScore)}
        />
        <MetricCell
          label="Growth"
          value={growthScore}
          available={isAvailable(dashboard.growthScore)}
        />

        {/* ── Qualitative signals ── */}
        {(topOpportunity !== "—" || biggestRisk !== "—" || valuationSummary !== "—") && (
          <>
            <GroupLabel label="Signals" />

            {topOpportunity !== "—" && (
              <MetricCell
                label="Top Opportunity"
                value={topOpportunity}
                available={isAvailable(dashboard.topOpportunity)}
                wide
              />
            )}
            {biggestRisk !== "—" && (
              <MetricCell
                label="Biggest Risk"
                value={biggestRisk}
                available={isAvailable(dashboard.biggestRisk)}
                wide
              />
            )}
            {valuationSummary !== "—" && (
              <MetricCell
                label="Valuation Summary"
                value={valuationSummary}
                available={isAvailable(valuation.summary)}
                wide
              />
            )}
          </>
        )}
      </div>

      {/* Data provenance note */}
      <p className="text-[10px] text-[var(--muted)]">
        Values sourced from{" "}
        <span className="font-mono">POST /api/v1/analyze/company</span> envelope.
        Market price, cap, and 52W range require live market data endpoint.
        Scores populate when the analysis engine returns them.
        &ldquo;—&rdquo; means not yet available — never invented.
      </p>
    </div>
  );
}
