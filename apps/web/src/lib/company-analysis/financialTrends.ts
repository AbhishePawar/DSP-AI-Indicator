/**
 * Figma `CompanyAnalysis` five-year trend charts (Revenue, Net Profit, Free
 * Cash Flow, Net Margin) — view-model over the authenticated
 * `GET /api/v1/fundamentals/statements` payload.
 *
 * Source decision (§4 historical charts):
 * - `/historical/series` is a vendor-neutral HTTP adapter whose `fundamentals`
 *   snapshot keys are provider-defined and is not backed by the canonical
 *   authenticated statements source, so it cannot safely supply these metrics.
 * - `/fundamentals/statements` (canonical, authenticated) already returns
 *   per-period `income_statement.revenue`, `income_statement.net_income`,
 *   `cash_flow.free_cash_flow`, and provider-reported `ratios.net_margin`.
 *
 * Every point is a provider line item copied as-is. Nothing is computed here —
 * no margins, growth rates, or CAGR. Missing values stay null and the chart
 * renders the Figma-compatible "Data unavailable." state.
 */

import type { FinancialStatementsPayload } from "@/lib/institutional-dashboard/mapInstitutionalDashboard";

export type FinancialTrendId = "revenue" | "net_income" | "free_cash_flow" | "net_margin";

export type FinancialTrendPoint = {
  /** Fiscal label, e.g. "FY2024". */
  label: string;
  periodEnd: string;
  value: number | null;
};

export type FinancialTrendSeries = {
  id: FinancialTrendId;
  /** Figma card label. */
  title: string;
  /** Figma semantic colour token. */
  colorVar: string;
  /** "currency" → reporting currency amounts; "ratio" → provider ratio (0–1). */
  unit: "currency" | "ratio";
  currency: string | null;
  points: FinancialTrendPoint[];
  /** True when at least two periods carry a value (chartable). */
  available: boolean;
  /** False when the statements payload itself was not authenticated/available. */
  authenticated: boolean;
  /** Provenance for the card footer. */
  source: string;
};

export type FinancialTrendsView = {
  authenticated: boolean;
  periodType: string | null;
  series: Record<FinancialTrendId, FinancialTrendSeries>;
};

type Period = NonNullable<FinancialStatementsPayload["periods"]>[number];

const SERIES_META: readonly {
  id: FinancialTrendId;
  title: string;
  colorVar: string;
  unit: FinancialTrendSeries["unit"];
  read: (p: Period) => unknown;
}[] = [
  {
    id: "revenue",
    title: "Revenue trend",
    colorVar: "var(--c-revenue)",
    unit: "currency",
    read: (p) => p.income_statement?.revenue,
  },
  {
    id: "net_income",
    title: "Net profit trend",
    colorVar: "var(--c-profit)",
    unit: "currency",
    read: (p) => p.income_statement?.net_income,
  },
  {
    id: "free_cash_flow",
    title: "Free cash flow trend",
    colorVar: "var(--c-cashflow)",
    unit: "currency",
    read: (p) => p.cash_flow?.free_cash_flow,
  },
  {
    id: "net_margin",
    title: "Net margin trend",
    colorVar: "var(--c-cashflow)",
    unit: "ratio",
    read: (p) => p.ratios?.net_margin,
  },
];

function finite(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function periodLabel(period: Period): string {
  if (typeof period.fiscal_year === "number" && Number.isFinite(period.fiscal_year)) {
    const fy = `FY${period.fiscal_year}`;
    return period.period_type === "quarterly" && period.fiscal_quarter
      ? `${fy} Q${period.fiscal_quarter}`
      : fy;
  }
  return period.period_end?.slice(0, 4) || "—";
}

/** Oldest → newest annual periods, capped at `maxPeriods` (Figma shows 5). */
function orderedPeriods(payload: FinancialStatementsPayload, maxPeriods: number): Period[] {
  const periods = (payload.periods ?? []).filter(
    (p): p is Period => Boolean(p && p.period_end),
  );
  const annual = periods.filter((p) => p.period_type === "annual");
  const chosen = (annual.length ? annual : periods)
    .slice()
    .sort((a, b) => a.period_end.localeCompare(b.period_end));
  return chosen.slice(Math.max(0, chosen.length - maxPeriods));
}

export function mapFinancialTrends(
  payload: FinancialStatementsPayload | null | undefined,
  options?: { maxPeriods?: number },
): FinancialTrendsView {
  const maxPeriods = options?.maxPeriods ?? 5;
  const authenticated = Boolean(payload?.available && payload?.authenticated);
  const periods = authenticated && payload ? orderedPeriods(payload, maxPeriods) : [];
  const currency =
    (payload?.reporting_currency ?? payload?.identity?.currency ?? null)?.toString().toUpperCase() ||
    null;
  const provider = payload?.provenance?.provider_name || payload?.provenance?.provider_id;
  const source = authenticated
    ? `Source: ${provider ?? "authenticated statements"} · GET /api/v1/fundamentals/statements`
    : "Data unavailable.";

  const series = {} as Record<FinancialTrendId, FinancialTrendSeries>;
  for (const meta of SERIES_META) {
    const points: FinancialTrendPoint[] = periods.map((p) => ({
      label: periodLabel(p),
      periodEnd: p.period_end,
      value: finite(meta.read(p)),
    }));
    const valued = points.filter((pt) => pt.value != null).length;
    series[meta.id] = {
      id: meta.id,
      title: meta.title,
      colorVar: meta.colorVar,
      unit: meta.unit,
      currency: meta.unit === "currency" ? currency : null,
      points,
      available: valued >= 2,
      authenticated,
      source,
    };
  }

  return {
    authenticated,
    periodType: periods[0]?.period_type ?? null,
    series,
  };
}

/** Compact display for chart axes / tooltips — formatting only. */
export function formatTrendValue(series: FinancialTrendSeries, value: number | null): string {
  if (value == null) return "Data unavailable.";
  if (series.unit === "ratio") {
    return `${(value * 100).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
  }
  const abs = Math.abs(value);
  const [scaled, suffix] =
    abs >= 1e12
      ? [value / 1e12, "T"]
      : abs >= 1e9
        ? [value / 1e9, "B"]
        : abs >= 1e6
          ? [value / 1e6, "M"]
          : abs >= 1e3
            ? [value / 1e3, "K"]
            : [value, ""];
  const number = scaled.toLocaleString(undefined, { maximumFractionDigits: 1 });
  return series.currency ? `${series.currency} ${number}${suffix}` : `${number}${suffix}`;
}
