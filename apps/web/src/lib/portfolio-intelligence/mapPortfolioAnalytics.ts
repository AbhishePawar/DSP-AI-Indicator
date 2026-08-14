/**
 * Presentation mapper for the Portfolio Intelligence Analytics module
 * (POST /api/v1/portfolio/analytics/*). Display only — every quantitative
 * value is computed server-side (packages/portfolio_analytics); the client
 * never recalculates ratios, correlations, or simulations.
 */

import type {
  AllocationBreakdownPayload,
  PortfolioAnalyticsAllocationPayload,
  PortfolioAnalyticsConstraintsPayload,
  PortfolioAnalyticsHolding,
  PortfolioAnalyticsPerformancePayload,
  PortfolioAnalyticsPortfolio,
  PortfolioAnalyticsRiskPayload,
  PortfolioAnalyticsSimulationPayload,
  PortfolioAnalyticsStressPayload,
  PortfolioAnalyticsTaxPayload,
} from "@/lib/api/client";
import type { PortfolioHolding } from "@/lib/portfolio/model";

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Data unavailable.";
  }
  return String(value);
}

function pct(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "Data unavailable.";
  }
  return `${(value * 100).toFixed(digits)}%`;
}

function ratio(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "Data unavailable.";
  }
  return value.toFixed(digits);
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

/**
 * Build the `{ holdings: [...] }` request body from session holdings.
 * Best-effort: the session `PortfolioHolding` model only carries
 * `allocationPercent` and `sector` — `units`/`cost_basis_per_unit`/
 * `purchase_date`/`country`/`exchange` stay absent (never invented), so
 * server-side fields that need them (Tax Optimization, Country Allocation)
 * honestly report unavailable until those inputs exist.
 */
export function buildPortfolioAnalyticsPortfolio(
  holdings: PortfolioHolding[],
): PortfolioAnalyticsPortfolio {
  const rows: PortfolioAnalyticsHolding[] = holdings
    .filter((h) => h.ticker)
    .map((h) => ({
      symbol: h.ticker,
      weight:
        typeof h.allocationPercent === "number" &&
        Number.isFinite(h.allocationPercent)
          ? h.allocationPercent / 100
          : 0,
      sector: h.sector || null,
    }));
  return { holdings: rows };
}

export type PerformanceView = {
  available: boolean;
  message: string;
  status: string;
  sharpeRatio: string;
  sortinoRatio: string;
  treynorRatio: string;
  jensenAlpha: string;
  beta: string;
  trackingError: string;
  informationRatio: string;
  maxDrawdown: string;
  annualizedReturn: string;
  annualizedVolatility: string;
  windowDays: string;
  benchmarkSymbol: string;
  limitations: string[];
};

export function mapPerformanceView(
  payload: PortfolioAnalyticsPerformancePayload | null | undefined,
): PerformanceView {
  const result = payload?.result ?? null;
  return {
    available: Boolean(payload?.available),
    message: display(payload?.message ?? (payload?.available ? null : "Data unavailable.")),
    status: display(result?.status),
    sharpeRatio: ratio(result?.sharpe_ratio),
    sortinoRatio: ratio(result?.sortino_ratio),
    treynorRatio: ratio(result?.treynor_ratio),
    jensenAlpha: pct(result?.jensen_alpha),
    beta: ratio(result?.beta),
    trackingError: pct(result?.tracking_error),
    informationRatio: ratio(result?.information_ratio),
    maxDrawdown: pct(result?.max_drawdown),
    annualizedReturn: pct(result?.annualized_return),
    annualizedVolatility: pct(result?.annualized_volatility),
    windowDays: display(result?.window_days),
    benchmarkSymbol: display(payload?.benchmark_symbol),
    limitations: result?.limitations ?? payload?.limitations ?? [],
  };
}

export type RiskAttributionRowView = {
  symbol: string;
  weight: string;
  volatility: string;
  correlationToPortfolio: string;
  riskContributionPct: string;
};

export type FactorExposureView = {
  factorName: string;
  exposureValue: string;
  coverage: string;
};

export type RiskView = {
  available: boolean;
  status: string;
  rows: RiskAttributionRowView[];
  heatmap: Array<{
    symbol: string;
    sector: string;
    weight: string;
    volatility: string;
    riskContributionPct: string;
  }>;
  correlationSymbols: string[];
  correlationMatrix: (number | null)[][];
  factors: FactorExposureView[];
  factorStatus: string;
  limitations: string[];
};

export function mapRiskView(
  payload: PortfolioAnalyticsRiskPayload | null | undefined,
): RiskView {
  const attribution = payload?.risk_attribution ?? null;
  const factorExposure = payload?.factor_exposure ?? null;
  return {
    available: Boolean(payload?.available),
    status: display(attribution?.status),
    rows: (attribution?.rows ?? []).map((r) => ({
      symbol: r.symbol,
      weight: pct(r.weight),
      volatility: pct(r.volatility),
      correlationToPortfolio: ratio(r.correlation_to_portfolio),
      riskContributionPct: pct(r.risk_contribution_pct),
    })),
    heatmap: (attribution?.heatmap ?? []).map((c) => ({
      symbol: c.symbol,
      sector: display(c.sector),
      weight: pct(c.weight),
      volatility: pct(c.volatility),
      riskContributionPct: pct(c.risk_contribution_pct),
    })),
    correlationSymbols: attribution?.correlation_matrix?.symbols ?? [],
    correlationMatrix: attribution?.correlation_matrix?.matrix ?? [],
    factors: (factorExposure?.factors ?? []).map((f) => ({
      factorName: f.factor_name,
      exposureValue: ratio(f.exposure_value),
      coverage: `${f.contributing_positions}/${f.total_positions} positions`,
    })),
    factorStatus: display(factorExposure?.status),
    limitations: [
      ...(attribution?.limitations ?? []),
      ...(factorExposure?.limitations ?? []),
    ],
  };
}

export type AllocationBucketView = { label: string; weight: string; symbols: string[] };

export type AllocationDimensionView = {
  status: string;
  buckets: AllocationBucketView[];
  unclassifiedWeight: string;
  limitations: string[];
};

export type AllocationView = {
  available: boolean;
  sector: AllocationDimensionView;
  country: AllocationDimensionView;
};

function mapAllocationDimension(
  breakdown: AllocationBreakdownPayload | null | undefined,
): AllocationDimensionView {
  return {
    status: display(breakdown?.status),
    buckets: (breakdown?.buckets ?? []).map((b) => ({
      label: b.label,
      weight: pct(b.weight),
      symbols: b.symbols,
    })),
    unclassifiedWeight: pct(breakdown?.unclassified_weight),
    limitations: breakdown?.limitations ?? [],
  };
}

export function mapAllocationView(
  payload: PortfolioAnalyticsAllocationPayload | null | undefined,
): AllocationView {
  return {
    available: Boolean(payload?.available),
    sector: mapAllocationDimension(payload?.sector_allocation),
    country: mapAllocationDimension(payload?.country_allocation),
  };
}

export type SimulationView = {
  available: boolean;
  monteCarloStatus: string;
  monteCarloPaths: string;
  monteCarloHorizonDays: string;
  percentiles: Array<{ label: string; value: string }>;
  meanTerminalReturn: string;
  monteCarloLimitations: string[];
  frontierStatus: string;
  frontierPoints: Array<{ expectedReturn: string; volatility: string }>;
  currentPortfolioPoint: { expectedReturn: string; volatility: string } | null;
  frontierLimitations: string[];
};

export function mapSimulationView(
  payload: PortfolioAnalyticsSimulationPayload | null | undefined,
): SimulationView {
  const mc = payload?.monte_carlo ?? null;
  const ef = payload?.efficient_frontier ?? null;
  const percentileEntries = Object.entries(mc?.percentiles ?? {}).sort(
    ([a], [b]) => a.localeCompare(b),
  );
  return {
    available: Boolean(payload?.available),
    monteCarloStatus: display(mc?.status),
    monteCarloPaths: display(mc?.paths),
    monteCarloHorizonDays: display(mc?.horizon_days),
    percentiles: percentileEntries.map(([label, value]) => ({
      label,
      value: pct(value),
    })),
    meanTerminalReturn: pct(mc?.mean_terminal_return),
    monteCarloLimitations: mc?.limitations ?? [],
    frontierStatus: display(ef?.status),
    frontierPoints: (ef?.points ?? []).map((p) => ({
      expectedReturn: pct(p.expected_return),
      volatility: pct(p.volatility),
    })),
    currentPortfolioPoint: ef?.current_portfolio_point
      ? {
          expectedReturn: pct(ef.current_portfolio_point.expected_return),
          volatility: pct(ef.current_portfolio_point.volatility),
        }
      : null,
    frontierLimitations: ef?.limitations ?? [],
  };
}

export type StressView = {
  available: boolean;
  scenarios: Array<{ name: string; shockPct: string; portfolioImpactPct: string }>;
  stressTests: Array<{
    scenarioId: string;
    available: boolean;
    description: string;
    portfolioReturnPct: string;
    positionsWithHistory: string;
    positionsBetaScaled: string;
    message: string;
  }>;
  catalog: Array<{ id: string; start: string; end: string; description: string }>;
};

export function mapStressView(
  payload: PortfolioAnalyticsStressPayload | null | undefined,
): StressView {
  const catalog = asRecord(payload?.stress_window_catalog);
  return {
    available: Boolean(payload?.available),
    scenarios: (payload?.scenarios ?? []).map((s) => ({
      name: s.scenario_name,
      shockPct: pct(s.shock_pct),
      portfolioImpactPct: pct(s.portfolio_impact_pct),
    })),
    stressTests: (payload?.stress_tests ?? []).map((s) => ({
      scenarioId: s.scenario_id,
      available: s.available !== false,
      description: display(s.description),
      portfolioReturnPct: pct(s.portfolio_return_pct),
      positionsWithHistory: display(s.positions_with_history),
      positionsBetaScaled: display(s.positions_beta_scaled),
      message: display(s.message),
    })),
    catalog: Object.entries(catalog).map(([id, value]) => {
      const v = asRecord(value);
      return {
        id,
        start: display(v.start),
        end: display(v.end),
        description: display(v.description),
      };
    }),
  };
}

export type ConstraintsView = {
  available: boolean;
  limitsStatus: string;
  breaches: Array<{ label: string; limitType: string; limit: string; actual: string }>;
  checks: Array<{
    label: string;
    limitType: string;
    limit: string;
    actual: string;
    breached: boolean;
  }>;
  rebalancingStatus: string;
  trades: Array<{
    symbol: string;
    current: string;
    target: string;
    drift: string;
    action: string;
    delta: string;
  }>;
  disclaimer: string;
};

export function mapConstraintsView(
  payload: PortfolioAnalyticsConstraintsPayload | null | undefined,
): ConstraintsView {
  const limits = payload?.position_limits ?? null;
  const rebalancing = payload?.rebalancing ?? null;
  return {
    available: Boolean(payload?.available),
    limitsStatus: display(limits?.status),
    breaches: (limits?.breaches ?? []).map((b) => ({
      label: b.label,
      limitType: b.limit_type,
      limit: pct(b.limit_value),
      actual: pct(b.actual_value),
    })),
    checks: (limits?.checks ?? []).map((c) => ({
      label: c.label,
      limitType: c.limit_type,
      limit: pct(c.limit_value),
      actual: pct(c.actual_value),
      breached: c.breached,
    })),
    rebalancingStatus: display(rebalancing?.status),
    trades: (rebalancing?.trades ?? []).map((t) => ({
      symbol: t.symbol,
      current: pct(t.current_weight),
      target: pct(t.target_weight),
      drift: pct(t.drift),
      action: t.suggested_action,
      delta: pct(t.suggested_delta_weight),
    })),
    disclaimer: display(
      rebalancing?.disclaimer ??
        "Analysis only — not a trade recommendation or order instruction.",
    ),
  };
}

export type TaxLotView = {
  symbol: string;
  available: boolean;
  gainLossPct: string;
  holdingPeriodDays: string;
  term: string;
  harvestingCandidate: boolean;
  reasonUnavailable: string;
};

export type TaxView = {
  available: boolean;
  status: string;
  lots: TaxLotView[];
  harvestingCandidates: string[];
  limitations: string[];
};

export function mapTaxView(
  payload: PortfolioAnalyticsTaxPayload | null | undefined,
): TaxView {
  const result = payload?.result ?? null;
  return {
    available: Boolean(payload?.available),
    status: display(result?.status),
    lots: (result?.lots ?? []).map((l) => ({
      symbol: l.symbol,
      available: l.available,
      gainLossPct: pct(l.unrealized_gain_loss_pct),
      holdingPeriodDays: display(l.holding_period_days),
      term: display(l.term),
      harvestingCandidate: l.harvesting_candidate,
      reasonUnavailable: display(l.reason_unavailable),
    })),
    harvestingCandidates: result?.harvesting_candidates ?? [],
    limitations: result?.limitations ?? [],
  };
}
