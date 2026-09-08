"use client";

/**
 * EquityResearchHeader — Professional Indian equity-research-terminal header.
 *
 * Inspired by Finology Ticker's information density.
 * Data sources (existing only — never invented):
 *   - view.snapshot   → company name, ticker, exchange, sector, market cap, CMP, 52W range
 *   - view.conclusion → intrinsic value, margin of safety
 *   - view.dashboard  → research conclusion, confidence, scores
 *   - useMarketQuote  → live price, daily change, market cap (supplemental)
 *
 * Rules:
 *   - Unavailable fields render "—" in muted colour
 *   - Live market data is supplemental; snapshot data is primary
 *   - No mock values, no invented metrics
 */

import { useMarketQuote } from "@/providers/MarketDataProvider";
import {
  formatChange,
  formatMarketCap,
  formatMarketPrice,
} from "@/lib/market";
import { Badge } from "@/components/ui/Badge";
import { RefreshButton } from "@/components/market/RefreshButton";
import { DeterministicAnalysisLabel } from "@/components/market/MarketStatusIndicator";
import type { AnalysisWorkspaceView, DisplayField } from "@/lib/analysis/types";

/* ─── Helpers ────────────────────────────────────────────────────── */

function dv(field: DisplayField<string | string[] | number>): string {
  if (field.presence === "unavailable" || field.value == null) return "—";
  if (Array.isArray(field.value)) return field.value.join(" · ");
  return String(field.value);
}

function isAvail(field: DisplayField<unknown>): boolean {
  return field.presence === "available" && field.value != null;
}

/* ─── Pill badge ─────────────────────────────────────────────────── */

function ExchangePill({ exchange }: { exchange: string }) {
  if (exchange === "—") return null;
  return (
    <span className="inline-flex items-center border border-[var(--border)] px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
      {exchange}
    </span>
  );
}

/* ─── Stat cell ──────────────────────────────────────────────────── */

interface StatCellProps {
  label: string;
  value: string;
  available?: boolean;
  accent?: boolean;
  positive?: boolean | null;
  negative?: boolean | null;
}

function StatCell({ label, value, available = true, accent, positive, negative }: StatCellProps) {
  const valueClass = [
    "font-mono text-sm font-semibold leading-tight tabular-nums",
    !available || value === "—" ? "text-[var(--muted)]"
      : accent
        ? "text-[var(--accent)]"
        : positive
          ? "text-emerald-700"
          : negative
            ? "text-red-700" : "text-[var(--fg)]",
  ].join(" ");

  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] truncate">
        {label}
      </span>
      <span className={valueClass}>{value}</span>
    </div>
  );
}

/* ─── Score pill ─────────────────────────────────────────────────── */

function ScorePill({ label, value }: { label: string; value: string }) {
  const isAvail = value !== "—";

  return (
    <div className="flex items-center gap-2 py-1.5 border-b border-[var(--border)] last:border-0 w-full sm:w-auto sm:border-0 sm:py-0">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] w-20 sm:w-auto shrink-0">
        {label}
      </span>
      <span
        className={[
          "font-mono text-sm font-semibold tabular-nums",
          isAvail ? "text-[var(--fg)]" : "text-[var(--muted)]",
        ].join(" ")}
      >
        {value}
      </span>
    </div>
  );
}

/* ─── Conclusion badge ───────────────────────────────────────────── */

function ConclusionBadge({ conclusion }: { conclusion: string }) {
  if (conclusion === "—") {
    return <Badge tone="neutral" className="font-mono text-xs">No Conclusion</Badge>;
  }
  const upper = conclusion.toUpperCase();
  const tone =
    upper.includes("STRONG") && upper.includes("BUY")
      ? "success" : upper.includes("BUY") || upper.includes("ACCUMULATE")
        ? "success" : upper.includes("SELL") || upper.includes("AVOID") || upper.includes("REDUCE")
          ? "danger" : upper.includes("HOLD") || upper.includes("NEUTRAL") || upper.includes("WATCH")
            ? "warning" :"neutral";
  return (
    <Badge tone={tone} className="font-mono text-xs font-bold tracking-wide">
      {conclusion}
    </Badge>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

export function EquityResearchHeader({
  view,
  onRefresh,
}: {
  view: AnalysisWorkspaceView;
  onRefresh: () => void;
}) {
  const { snapshot, conclusion, dashboard } = view;
  const ticker = dv(snapshot.ticker);
  const { quote, refresh, isRefreshing } = useMarketQuote(ticker === "—" ? "" : ticker);

  /* Identity */
  const companyName = dv(snapshot.companyName);
  const exchange = dv(snapshot.exchange);
  const sector = dv(snapshot.sector);
  const industry = dv(snapshot.industry);

  /* Price — prefer live quote, fall back to snapshot */
  const livePrice =
    quote != null
      ? formatMarketPrice(quote.currentPrice, quote.currency)
      : dv(snapshot.currentMarketPrice);
  const livePriceAvail = quote != null || isAvail(snapshot.currentMarketPrice);

  const dailyChange =
    quote != null
      ? formatChange(quote.dailyChange, quote.dailyChangePercent)
      : "—";
  const isPositive = quote != null ? quote.dailyChange >= 0 : null;
  const isNegative = quote != null ? quote.dailyChange < 0 : null;

  /* Market cap — prefer live, fall back to snapshot */
  const marketCapStr =
    quote?.marketCap != null
      ? formatMarketCap(quote.marketCap)
      : dv(snapshot.marketCap);
  const marketCapAvail = quote?.marketCap != null || isAvail(snapshot.marketCap);

  /* 52W range */
  const week52High =
    quote?.week52High != null
      ? formatMarketPrice(quote.week52High, quote.currency ?? "INR")
      : dv(snapshot.week52High);
  const week52Low =
    quote?.week52Low != null
      ? formatMarketPrice(quote.week52Low, quote.currency ?? "INR")
      : dv(snapshot.week52Low);

  /* Research */
  const researchConclusion = dv(dashboard.researchConclusion);
  const confidence = dv(dashboard.researchConfidence);
  const intrinsicValue = dv(conclusion.intrinsicValueRange);
  const marginOfSafety = dv(conclusion.marginOfSafety);

  /* Scores */
  const businessScore = dv(dashboard.businessScore);
  const financialScore = dv(dashboard.financialScore);
  const valuationScore = dv(dashboard.valuationScore);
  const riskScore = dv(dashboard.riskScore);
  const managementScore = dv(dashboard.managementScore);
  const growthScore = dv(dashboard.growthScore);

  return (
    <div className="border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      {/* ── Top bar: identity + price ─────────────────────────── */}
      <div className="flex flex-col gap-3 border-b border-[var(--border)] bg-[var(--surface-2)] px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        {/* Left: company identity */}
        <div className="flex flex-col gap-1 min-w-0">
          <h1 className="font-[family-name:var(--font-display)] text-xl font-semibold leading-tight text-[var(--fg)] break-words max-w-full sm:max-w-[420px]">
            {companyName !== "—" ? companyName : ticker}
          </h1>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
              {ticker}
            </span>
            <ExchangePill exchange={exchange} />
            <DeterministicAnalysisLabel />
          </div>
          {(sector !== "—" || industry !== "—") && (
            <p className="text-xs text-[var(--muted)] break-words">
              {[sector, industry !== sector ? industry : null]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </div>

        {/* Right: live price block */}
        <div className="flex flex-row items-start justify-between gap-2 sm:flex-col sm:items-end sm:gap-1">
          <div className="flex items-baseline gap-2 flex-wrap">
            <span
              className={[
                "font-mono text-2xl font-bold tabular-nums leading-none",
                livePriceAvail ? "text-[var(--fg)]" : "text-[var(--muted)]",
              ].join(" ")}
            >
              {livePrice}
            </span>
            {dailyChange !== "—" && (
              <span
                className={[
                  "font-mono text-sm font-semibold tabular-nums",
                  isPositive ? "text-emerald-700" : isNegative ? "text-red-700" : "text-[var(--muted)]",
                ].join(" ")}
              >
                {isPositive ? "+" : ""}{dailyChange}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <ConclusionBadge conclusion={researchConclusion} />
            <RefreshButton
              onRefresh={() => { refresh(); onRefresh(); }}
              isRefreshing={isRefreshing}
            />
          </div>
        </div>
      </div>

      {/* ── Middle row: key market stats ─────────────────────── */}
      <div className="grid grid-cols-2 gap-px bg-[var(--border)] sm:grid-cols-3 lg:grid-cols-6 border-b border-[var(--border)]">
        {[
          { label: "Mkt Cap", value: marketCapStr, available: marketCapAvail },
          { label: "52W High", value: week52High, available: week52High !== "—" },
          { label: "52W Low", value: week52Low, available: week52Low !== "—" },
          { label: "Intrinsic Val", value: intrinsicValue, available: intrinsicValue !== "—", accent: true },
          { label: "Margin of Safety", value: marginOfSafety, available: marginOfSafety !== "—", accent: true },
          { label: "Confidence", value: confidence, available: confidence !== "—" },
        ].map(({ label, value, available, accent }) => (
          <div
            key={label}
            className="flex flex-col gap-0.5 bg-[var(--surface)] px-3 py-2.5"
          >
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] truncate">
              {label}
            </span>
            <span
              className={[
                "font-mono text-xs font-semibold tabular-nums leading-tight break-words",
                !available || value === "—" ? "text-[var(--muted)]"
                  : accent
                    ? "text-[var(--accent)]"
                    : "text-[var(--fg)]",
              ].join(" ")}
            >
              {value}
            </span>
          </div>
        ))}
      </div>

      {/* ── Bottom row: quality scores ────────────────────────── */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-0 px-4 py-2.5 border-t border-[var(--border)]">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mr-2 shrink-0">
          Scores
        </span>
        <div className="flex flex-wrap gap-x-5 gap-y-1">
          {[
            { label: "Business", value: businessScore },
            { label: "Financial", value: financialScore },
            { label: "Valuation", value: valuationScore },
            { label: "Risk", value: riskScore },
            { label: "Mgmt", value: managementScore },
            { label: "Growth", value: growthScore },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center gap-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                {label}
              </span>
              <span
                className={[
                  "font-mono text-xs font-semibold tabular-nums",
                  value !== "—" ? "text-[var(--fg)]" : "text-[var(--muted)]",
                ].join(" ")}
              >
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
