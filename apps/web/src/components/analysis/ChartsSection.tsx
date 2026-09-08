"use client";

/**
 * ChartsSection — compact equity-research price/market chart block.
 *
 * Data sources (existing, no mock data):
 *   - useMarketQuote(ticker)  → live MarketQuote from /api/v1/market/quote
 *   - view.snapshot           → CMP, 52W High/Low, marketCap (fallback labels)
 *
 * Chart: Recharts BarChart showing key price levels (52W Low, Prev Close,
 * Current Price, 52W High) as a horizontal range bar — research-terminal style.
 * Time-range tabs control the visible metric context (1D / 52W).
 *
 * Rules:
 *   - Never invents values; shows "—" when unavailable.
 *   - No new backend endpoints.
 *   - Reuses existing design tokens, useMarketQuote, formatMarketPrice.
 */

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useMarketQuote } from "@/providers/MarketDataProvider";
import { RefreshButton } from "@/components/market/RefreshButton";
import { MarketStatusIndicator } from "@/components/market/MarketStatusIndicator";
import { formatMarketPrice, formatChange } from "@/lib/market";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";

/* ─── Time-range tabs ────────────────────────────────────────────── */

type TimeRange = "1D" | "52W";

const TIME_RANGES: { id: TimeRange; label: string }[] = [
  { id: "1D", label: "1D" },
  { id: "52W", label: "52W Range" },
];

/* ─── Helpers ────────────────────────────────────────────────────── */

function fmt(value: number | null | undefined, currency: string): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return formatMarketPrice(value, currency);
}

function pct(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

/* ─── Metric pill ────────────────────────────────────────────────── */

interface MetricPillProps {
  label: string;
  value: string;
  highlight?: "positive" | "negative" | "neutral" | "accent";
}

function MetricPill({ label, value, highlight = "neutral" }: MetricPillProps) {
  const valueColour =
    highlight === "positive" ?"text-emerald-400"
      : highlight === "negative" ?"text-red-400"
        : highlight === "accent" ?"text-[var(--accent)]" :"text-[var(--fg)]";

  return (
    <div className="flex flex-col gap-0.5 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </span>
      <span className={`font-mono text-sm font-bold leading-tight ${valueColour}`}>
        {value}
      </span>
    </div>
  );
}

/* ─── Custom tooltip ─────────────────────────────────────────────── */

interface TooltipPayloadItem {
  name: string;
  value: number;
  payload: { currency: string };
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-2 shadow-lg">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        {item.name}
      </p>
      <p className="font-mono text-sm font-bold text-[var(--accent)]">
        {fmt(item.value, item.payload.currency)}
      </p>
    </div>
  );
}

/* ─── 52W Range bar chart ────────────────────────────────────────── */

interface RangeChartProps {
  currency: string;
  week52Low: number | null;
  previousClose: number | null;
  currentPrice: number;
  week52High: number | null;
}

function RangeBarChart({
  currency,
  week52Low,
  previousClose,
  currentPrice,
  week52High,
}: RangeChartProps) {
  const data = [
    {
      name: "52W Low",
      value: week52Low ?? currentPrice * 0.72,
      currency,
      available: week52Low != null,
    },
    {
      name: "Prev Close",
      value: previousClose ?? currentPrice,
      currency,
      available: previousClose != null,
    },
    {
      name: "Current",
      value: currentPrice,
      currency,
      available: true,
    },
    {
      name: "52W High",
      value: week52High ?? currentPrice * 1.28,
      currency,
      available: week52High != null,
    },
  ].filter((d) => d.available);

  const allValues = data.map((d) => d.value);
  const minVal = Math.min(...allValues);
  const maxVal = Math.max(...allValues);
  const padding = (maxVal - minVal) * 0.1 || currentPrice * 0.05;

  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart
        data={data}
        margin={{ top: 8, right: 8, left: 8, bottom: 4 }}
        barCategoryGap="30%"
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--border)"
          vertical={false}
        />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 10, fill: "var(--muted)", fontFamily: "monospace" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[minVal - padding, maxVal + padding]}
          tick={{ fontSize: 10, fill: "var(--muted)", fontFamily: "monospace" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => fmt(v, currency)}
          width={72}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--surface-2)" }} />
        <ReferenceLine
          y={currentPrice}
          stroke="var(--accent)"
          strokeDasharray="4 2"
          strokeWidth={1}
        />
        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={
                entry.name === "Current" ?"var(--accent)"
                  : entry.name === "52W High" ?"rgb(52 211 153 / 0.6)"
                    : entry.name === "52W Low" ?"rgb(248 113 113 / 0.6)" :"rgb(148 163 184 / 0.4)"
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ─── 1D change chart ────────────────────────────────────────────── */

interface DayChartProps {
  currency: string;
  previousClose: number;
  currentPrice: number;
}

function DayBarChart({ currency, previousClose, currentPrice }: DayChartProps) {
  const isUp = currentPrice >= previousClose;
  const data = [
    { name: "Prev Close", value: previousClose, currency },
    { name: "Current", value: currentPrice, currency },
  ];
  const minVal = Math.min(previousClose, currentPrice);
  const maxVal = Math.max(previousClose, currentPrice);
  const padding = (maxVal - minVal) * 0.5 || currentPrice * 0.02;

  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart
        data={data}
        margin={{ top: 8, right: 8, left: 8, bottom: 4 }}
        barCategoryGap="40%"
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--border)"
          vertical={false}
        />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 10, fill: "var(--muted)", fontFamily: "monospace" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[minVal - padding, maxVal + padding]}
          tick={{ fontSize: 10, fill: "var(--muted)", fontFamily: "monospace" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => fmt(v, currency)}
          width={72}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--surface-2)" }} />
        <ReferenceLine
          y={previousClose}
          stroke="rgb(148 163 184 / 0.6)"
          strokeDasharray="4 2"
          strokeWidth={1}
        />
        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
          <Cell key="prev" fill="rgb(148 163 184 / 0.4)" />
          <Cell
            key="current"
            fill={isUp ? "rgb(52 211 153 / 0.75)" : "rgb(248 113 113 / 0.75)"}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

export function ChartsSection({
  view,
  ticker,
}: {
  view: AnalysisWorkspaceView;
  ticker: string;
}) {
  const [range, setRange] = useState<TimeRange>("52W");
  const { quote, status, refresh, isRefreshing } = useMarketQuote(ticker);

  /* Fallback labels from snapshot when live quote unavailable */
  const snapshotCmp =
    view.snapshot.currentMarketPrice?.presence === "available" ? String(view.snapshot.currentMarketPrice.value ??"")
      : null;

  const currency = quote?.currency ?? "INR";
  const currentPrice = quote?.currentPrice ?? null;
  const previousClose = quote?.previousClose ?? null;
  const dailyChange = quote?.dailyChange ?? null;
  const dailyChangePct = quote?.dailyChangePercent ?? null;
  const week52High = quote?.week52High ?? null;
  const week52Low = quote?.week52Low ?? null;
  const marketCap = quote?.marketCap ?? null;
  const volume = quote?.volume ?? null;

  const isUp = (dailyChange ?? 0) >= 0;
  const changeHighlight: "positive" | "negative" = isUp ?"positive" : "negative";

  const hasQuote = quote != null;

  return (
    <div className="space-y-4">
      {/* ── Header row ── */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
            {ticker}
          </span>
          <MarketStatusIndicator status={status} />
        </div>
        <div className="flex items-center gap-2">
          {/* Time-range tabs */}
          <div
            role="tablist"
            aria-label="Chart time range"
            className="flex rounded border border-[var(--border)] bg-[var(--surface-2)] p-0.5"
          >
            {TIME_RANGES.map((tr) => (
              <button
                key={tr.id}
                role="tab"
                aria-selected={range === tr.id}
                type="button"
                onClick={() => setRange(tr.id)}
                className={[
                  "rounded px-2.5 py-1 text-xs font-semibold transition-colors",
                  range === tr.id
                    ? "bg-[var(--accent)] text-white"
                    : "text-[var(--muted)] hover:text-[var(--fg)]",
                ].join(" ")}
              >
                {tr.label}
              </button>
            ))}
          </div>
          <RefreshButton onRefresh={refresh} isRefreshing={isRefreshing} />
        </div>
      </div>

      {/* ── Metric pills ── */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        <MetricPill
          label="CMP"
          value={
            currentPrice != null
              ? fmt(currentPrice, currency)
              : snapshotCmp ?? "—"
          }
          highlight="accent"
        />
        <MetricPill
          label="Day Change"
          value={
            dailyChange != null && dailyChangePct != null
              ? formatChange(dailyChange, dailyChangePct)
              : "—"
          }
          highlight={hasQuote ? changeHighlight : "neutral"}
        />
        <MetricPill
          label="Prev Close"
          value={fmt(previousClose, currency)}
        />
        <MetricPill
          label="52W High"
          value={fmt(week52High, currency)}
          highlight={week52High != null ? "positive" : "neutral"}
        />
        <MetricPill
          label="52W Low"
          value={fmt(week52Low, currency)}
          highlight={week52Low != null ? "negative" : "neutral"}
        />
        <MetricPill
          label="Mkt Cap"
          value={
            marketCap != null
              ? marketCap >= 1e12
                ? `₹${(marketCap / 1e12).toFixed(2)}T`
                : marketCap >= 1e9
                  ? `₹${(marketCap / 1e9).toFixed(2)}B`
                  : `₹${(marketCap / 1e6).toFixed(0)}M`
              : "—"
          }
        />
      </div>

      {/* ── Chart area ── */}
      {!hasQuote ? (
        <div className="flex h-40 items-center justify-center rounded border border-dashed border-[var(--border)] bg-[var(--surface-2)]">
          <p className="text-sm text-[var(--muted)]">
            {status === "loading" ?"Loading market data…" :"Market data unavailable — chart requires live quote."}
          </p>
        </div>
      ) : range === "1D" ? (
        <DayBarChart
          currency={currency}
          previousClose={previousClose ?? currentPrice!}
          currentPrice={currentPrice!}
        />
      ) : (
        <RangeBarChart
          currency={currency}
          week52Low={week52Low}
          previousClose={previousClose}
          currentPrice={currentPrice!}
          week52High={week52High}
        />
      )}

      {/* ── Volume row ── */}
      {hasQuote && volume != null ? (
        <div className="flex items-center gap-2 border-t border-[var(--border)] pt-2">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
            Volume
          </span>
          <span className="font-mono text-xs text-[var(--fg)]">
            {volume.toLocaleString()}
          </span>
          <span className="ml-auto text-[10px] text-[var(--muted)]">
            Source: /api/v1/market/quote · supplemental, does not affect scoring
          </span>
        </div>
      ) : null}
    </div>
  );
}
