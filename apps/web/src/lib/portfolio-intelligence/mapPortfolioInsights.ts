/**
 * Presentation mapper for the Portfolio Intelligence Engine (RC1 Milestone 4,
 * POST /api/v1/portfolio/insights). Display only — every score/classification/
 * ranking value is computed server-side by orchestrating Portfolio Analytics
 * and linked-research valuation/quality/committee signals
 * (packages/portfolio_intelligence_engine + dsp_platform façade). The client
 * never recalculates a score, classification, or ranking.
 */

import type {
  ConcentrationAnalysisPayload,
  DiversificationScorePayload,
  DriftAnalysisPayload,
  HealthScorePayload,
  OpportunityRankingPayload,
  PortfolioInsightsPayload,
  PortfolioRecommendationPayload,
  PortfolioRiskSummaryPayload,
  PortfolioScenarioSummaryPayload,
  ValuationHeatmapPayload,
} from "@/lib/api/client";

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Data unavailable.";
  }
  return String(value);
}

function pct(value: number | null | undefined, digits = 1): string {
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

function score100(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "Data unavailable.";
  }
  return `${Math.round(value)}/100`;
}

export type HealthScoreView = {
  available: boolean;
  status: string;
  score: number | null;
  scoreLabel: string;
  components: Array<{
    name: string;
    available: boolean;
    score: string;
    weightPct: string;
    contribution: string;
    explanation: string;
  }>;
  limitations: string[];
};

export function mapHealthScoreView(
  payload: HealthScorePayload | null | undefined,
): HealthScoreView {
  return {
    available: Boolean(payload && payload.score !== null),
    status: display(payload?.status),
    score: payload?.score ?? null,
    scoreLabel: score100(payload?.score),
    components: (payload?.components ?? []).map((c) => ({
      name: c.name,
      available: c.available,
      score: c.available ? score100(c.score) : "Data unavailable.",
      weightPct: pct(c.weight, 0),
      contribution: c.available ? ratio(c.contribution) : "Data unavailable.",
      explanation: c.explanation,
    })),
    limitations: payload?.limitations ?? [],
  };
}

export type ConcentrationView = {
  available: boolean;
  status: string;
  largestHoldings: Array<{ symbol: string; weight: string }>;
  sector: Array<{ label: string; weight: string; symbols: string[] }>;
  industry: Array<{ label: string; weight: string; symbols: string[] }>;
  style: Array<{ label: string; weight: string; symbols: string[] }>;
  country: Array<{ label: string; weight: string; symbols: string[] }>;
  herfindahlIndex: string;
  flags: Array<{ kind: string; label: string; weight: string; threshold: string }>;
  limitations: string[];
};

export function mapConcentrationView(
  payload: ConcentrationAnalysisPayload | null | undefined,
): ConcentrationView {
  return {
    available: Boolean(payload && payload.status !== "unavailable"),
    status: display(payload?.status),
    largestHoldings: (payload?.largest_holdings ?? []).map((h) => ({
      symbol: h.symbol,
      weight: pct(h.weight_pct_of_portfolio),
    })),
    sector: (payload?.sector_concentration ?? []).map((b) => ({
      label: b.label,
      weight: pct(b.weight),
      symbols: b.symbols,
    })),
    industry: (payload?.industry_concentration ?? []).map((b) => ({
      label: b.label,
      weight: pct(b.weight),
      symbols: b.symbols,
    })),
    style: (payload?.style_concentration ?? []).map((b) => ({
      label: b.label,
      weight: pct(b.weight),
      symbols: b.symbols,
    })),
    country: (payload?.country_concentration ?? []).map((b) => ({
      label: b.label,
      weight: pct(b.weight),
      symbols: b.symbols,
    })),
    herfindahlIndex: ratio(payload?.herfindahl_index, 3),
    flags: (payload?.flags ?? []).map((f) => ({
      kind: f.kind,
      label: f.label,
      weight: pct(f.weight),
      threshold: pct(f.threshold),
    })),
    limitations: payload?.limitations ?? [],
  };
}

export type ValuationHeatmapView = {
  available: boolean;
  status: string;
  rows: Array<{
    symbol: string;
    weight: string;
    valuationClass: string;
    marginOfSafety: string;
    confidence: string;
    message: string | null;
  }>;
  undervaluedWeight: string;
  fairlyValuedWeight: string;
  overvaluedWeight: string;
  unavailableWeight: string;
  limitations: string[];
};

const VALUATION_LABELS: Record<string, string> = {
  undervalued: "Undervalued",
  fairly_valued: "Fairly Valued",
  overvalued: "Overvalued",
  unavailable: "Data unavailable.",
};

export function mapValuationHeatmapView(
  payload: ValuationHeatmapPayload | null | undefined,
): ValuationHeatmapView {
  return {
    available: Boolean(payload && payload.status !== "unavailable"),
    status: display(payload?.status),
    rows: (payload?.rows ?? []).map((r) => ({
      symbol: r.symbol,
      weight: pct(r.weight),
      valuationClass: VALUATION_LABELS[r.valuation_class] ?? display(r.valuation_class),
      marginOfSafety: pct(r.margin_of_safety),
      confidence: pct(r.confidence),
      message: r.message,
    })),
    undervaluedWeight: pct(payload?.undervalued_weight),
    fairlyValuedWeight: pct(payload?.fairly_valued_weight),
    overvaluedWeight: pct(payload?.overvalued_weight),
    unavailableWeight: pct(payload?.unavailable_weight),
    limitations: payload?.limitations ?? [],
  };
}

export type RiskSummaryView = {
  available: boolean;
  status: string;
  beta: string;
  annualizedVolatility: string;
  maxDrawdown: string;
  trackingError: string;
  valueAtRisk95: string;
  valueAtRiskMethod: string | null;
  conditionalValueAtRisk95: string;
  stressTestCount: number;
  monteCarloAvailable: boolean;
  highestRiskHoldings: Array<{
    symbol: string;
    weight: string;
    volatility: string;
    riskContributionPct: string;
  }>;
  limitations: string[];
};

export function mapRiskSummaryView(
  payload: PortfolioRiskSummaryPayload | null | undefined,
): RiskSummaryView {
  return {
    available: Boolean(payload && payload.status !== "unavailable"),
    status: display(payload?.status),
    beta: ratio(payload?.beta),
    annualizedVolatility: pct(payload?.annualized_volatility),
    maxDrawdown: pct(payload?.max_drawdown),
    trackingError: pct(payload?.tracking_error),
    valueAtRisk95: pct(payload?.value_at_risk_95),
    valueAtRiskMethod: payload?.value_at_risk_method ?? null,
    conditionalValueAtRisk95: "Data unavailable.",
    stressTestCount: payload?.stress_test_count ?? 0,
    monteCarloAvailable: Boolean(payload?.monte_carlo_available),
    highestRiskHoldings: (payload?.highest_risk_holdings ?? []).map((h) => ({
      symbol: h.symbol,
      weight: pct(h.weight),
      volatility: pct(h.volatility),
      riskContributionPct: pct(h.risk_contribution_pct, 1),
    })),
    limitations: payload?.limitations ?? [],
  };
}

export type RecommendationView = {
  symbol: string;
  action: string;
  actionLabel: string;
  reason: string;
  confidence: string;
};

const ACTION_LABELS: Record<string, string> = {
  increase: "Increase",
  reduce: "Reduce",
  hold: "Hold",
  review: "Review",
  watch: "Watch",
};

export function mapRecommendations(
  payload: PortfolioRecommendationPayload[] | null | undefined,
): RecommendationView[] {
  return (payload ?? []).map((r) => ({
    symbol: r.symbol,
    action: r.action,
    actionLabel: ACTION_LABELS[r.action] ?? r.action,
    reason: r.reason,
    confidence: pct(r.confidence),
  }));
}

export type DriftView = {
  available: boolean;
  status: string;
  sectorDrift: Array<{ label: string; weight: string; baseline: string; direction: string }>;
  missingSectors: string[];
  styleDrift: Array<{ label: string; weight: string; baseline: string; direction: string }>;
  capDrift: Array<{ label: string; weight: string; baseline: string; direction: string }>;
  limitations: string[];
};

const DRIFT_LABELS: Record<string, string> = {
  overweight: "Overweight",
  underweight: "Underweight",
  missing: "Missing",
  in_line: "In line",
};

export function mapDriftView(payload: DriftAnalysisPayload | null | undefined): DriftView {
  const mapRow = (row: { label: string; weight: number; baseline_weight: number; direction: string }) => ({
    label: row.label,
    weight: pct(row.weight),
    baseline: pct(row.baseline_weight),
    direction: DRIFT_LABELS[row.direction] ?? row.direction,
  });
  return {
    available: Boolean(payload && payload.status !== "unavailable"),
    status: display(payload?.status),
    sectorDrift: (payload?.sector_drift ?? []).map(mapRow),
    missingSectors: payload?.missing_sectors ?? [],
    styleDrift: (payload?.style_drift ?? []).map(mapRow),
    capDrift: (payload?.cap_drift ?? []).map(mapRow),
    limitations: payload?.limitations ?? [],
  };
}

export type DiversificationView = {
  available: boolean;
  status: string;
  score: string;
  holdingCount: number;
  sectorCount: number;
  averagePairwiseCorrelation: string;
  largestPositionWeight: string;
  positionHerfindahlIndex: string;
  riskHerfindahlIndex: string;
  explanation: string[];
  limitations: string[];
};

export function mapDiversificationView(
  payload: DiversificationScorePayload | null | undefined,
): DiversificationView {
  return {
    available: Boolean(payload && payload.score !== null),
    status: display(payload?.status),
    score: score100(payload?.score),
    holdingCount: payload?.holding_count ?? 0,
    sectorCount: payload?.sector_count ?? 0,
    averagePairwiseCorrelation: ratio(payload?.average_pairwise_correlation),
    largestPositionWeight: pct(payload?.largest_position_weight),
    positionHerfindahlIndex: ratio(payload?.position_herfindahl_index, 3),
    riskHerfindahlIndex: ratio(payload?.risk_herfindahl_index, 3),
    explanation: payload?.explanation ?? [],
    limitations: payload?.limitations ?? [],
  };
}

export type OpportunitiesView = {
  available: boolean;
  status: string;
  highestMarginOfSafety: Array<{ symbol: string; value: string }>;
  highestExpectedCagr: Array<{ symbol: string; value: string }>;
  bestQuality: Array<{ symbol: string; value: string }>;
  lowestRisk: Array<{ symbol: string; value: string }>;
  highestConviction: Array<{ symbol: string; value: string }>;
  limitations: string[];
};

export function mapOpportunitiesView(
  payload: OpportunityRankingPayload | null | undefined,
): OpportunitiesView {
  const mapEntries = (
    entries: Array<{ symbol: string; value: number }> | undefined,
    formatter: (v: number) => string,
  ) => (entries ?? []).map((e) => ({ symbol: e.symbol, value: formatter(e.value) }));
  return {
    available: Boolean(payload && payload.status !== "unavailable"),
    status: display(payload?.status),
    highestMarginOfSafety: mapEntries(payload?.highest_margin_of_safety, (v) => pct(v)),
    highestExpectedCagr: mapEntries(payload?.highest_expected_cagr, (v) => pct(v)),
    bestQuality: mapEntries(payload?.best_quality, (v) => score100(v)),
    lowestRisk: mapEntries(payload?.lowest_risk, (v) => pct(v)),
    highestConviction: mapEntries(payload?.highest_conviction, (v) => pct(v)),
    limitations: payload?.limitations ?? [],
  };
}

export type ScenarioView = {
  available: boolean;
  status: string;
  cases: Array<{ case: string; impliedReturnPct: string }>;
  expectedCagr: string;
  expectedCagrBasis: string | null;
  worstCaseDrawdown: string;
  worstCaseDrawdownBasis: string | null;
  confidence: string;
  confidenceBasis: string | null;
  limitations: string[];
};

const CASE_LABELS: Record<string, string> = { bear: "Bear", base: "Base", bull: "Bull" };

export function mapScenarioView(
  payload: PortfolioScenarioSummaryPayload | null | undefined,
): ScenarioView {
  return {
    available: Boolean(payload && payload.status !== "unavailable"),
    status: display(payload?.status),
    cases: (payload?.cases ?? []).map((c) => ({
      case: CASE_LABELS[c.case] ?? c.case,
      impliedReturnPct: pct(c.implied_return_pct),
    })),
    expectedCagr: pct(payload?.expected_cagr),
    expectedCagrBasis: payload?.expected_cagr_basis ?? null,
    worstCaseDrawdown: pct(payload?.worst_case_drawdown),
    worstCaseDrawdownBasis: payload?.worst_case_drawdown_basis ?? null,
    confidence: pct(payload?.confidence),
    confidenceBasis: payload?.confidence_basis ?? null,
    limitations: payload?.limitations ?? [],
  };
}

export type PortfolioInsightsView = {
  available: boolean;
  message: string | null;
  holdingCount: number;
  health: HealthScoreView;
  concentration: ConcentrationView;
  valuationHeatmap: ValuationHeatmapView;
  riskSummary: RiskSummaryView;
  recommendations: RecommendationView[];
  drift: DriftView;
  diversification: DiversificationView;
  opportunities: OpportunitiesView;
  scenario: ScenarioView;
  limitations: string[];
};

export function mapPortfolioInsightsView(
  payload: PortfolioInsightsPayload | null | undefined,
): PortfolioInsightsView {
  return {
    available: Boolean(payload?.available),
    message: payload?.message ?? (payload?.available ? null : "Data unavailable."),
    holdingCount: payload?.holding_count ?? 0,
    health: mapHealthScoreView(payload?.health_score),
    concentration: mapConcentrationView(payload?.concentration),
    valuationHeatmap: mapValuationHeatmapView(payload?.valuation_heatmap),
    riskSummary: mapRiskSummaryView(payload?.risk_summary),
    recommendations: mapRecommendations(payload?.recommendations),
    drift: mapDriftView(payload?.drift),
    diversification: mapDiversificationView(payload?.diversification),
    opportunities: mapOpportunitiesView(payload?.opportunities),
    scenario: mapScenarioView(payload?.scenario),
    limitations: payload?.limitations ?? [],
  };
}
