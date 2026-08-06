/** HTTP client for `/api/v1` only — no DSP Platform imports. */

import { env } from "@/lib/env";
import type {
  AnalyseRequest,
  AnalyseResponse,
  CapabilitiesResponse,
  ValidateResponse,
  VersionResponse,
} from "@/lib/api/compositionTypes";
import {
  ApiClientError,
  type ApiErrorBody,
  type ApiResponse,
  type AnalyzeCompanyPayload,
  type HealthResponse,
  type LoginPayload,
  type PlatformInfoResponse,
  type ReportResponse,
} from "@/lib/api/types";

export type RequestOptions = {
  token?: string | null;
  signal?: AbortSignal;
};

/** Shared envelope shape returned by every Data Connector Framework endpoint. */
type ConnectorIdentity = {
  symbol?: string;
  exchange?: string | null;
  company_name?: string | null;
  isin?: string | null;
  provider_company_id?: string | null;
  currency?: string | null;
} | null;

type ConnectorProvenance = {
  provider_id?: string;
  provider_name?: string;
  source_type?: string;
  retrieved_at?: string;
  as_of?: string | null;
  request_id?: string | null;
  cache_hit?: boolean;
  auth_mode?: string;
} | null;

/** Authenticated news payload from GET /api/v1/news. */
export type NewsPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  articles?: Array<{
    article_id?: string;
    headline?: string;
    url?: string;
    source?: string;
    published_at?: string;
    summary?: string | null;
    sentiment?: string | null;
    related_symbols?: string[];
    image_url?: string | null;
  }> | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** Authenticated regulatory filings payload from GET /api/v1/filings. */
export type FilingsPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  filings?: Array<{
    filing_id?: string;
    filing_type?: string;
    title?: string;
    url?: string;
    filed_at?: string;
    period_of_report?: string | null;
    accession_number?: string | null;
    source?: string | null;
  }> | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** Authenticated shareholding pattern payload from GET /api/v1/ownership. */
export type OwnershipPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  as_of?: string | null;
  stakes?: Array<{
    holder_type?: string;
    holder_name?: string | null;
    percent_held?: number | null;
    shares_held?: number | null;
  }> | null;
  promoter_holding_percent?: number | null;
  institutional_holding_percent?: number | null;
  public_holding_percent?: number | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** Authenticated insider trading payload from GET /api/v1/insider-trading. */
export type InsiderTradingPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  transactions?: Array<{
    transaction_id?: string;
    insider_name?: string;
    role?: string | null;
    transaction_type?: string;
    shares?: number | null;
    price?: number | null;
    value?: number | null;
    transaction_date?: string;
    filed_at?: string | null;
    source?: string | null;
  }> | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** Authenticated ESG score payload from GET /api/v1/esg. */
export type EsgPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  as_of?: string | null;
  environmental_score?: number | null;
  social_score?: number | null;
  governance_score?: number | null;
  total_score?: number | null;
  controversy_level?: string | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** Authenticated earnings call transcripts payload from GET /api/v1/transcripts. */
export type TranscriptsPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  transcripts?: Array<{
    transcript_id?: string;
    quarter?: number | null;
    year?: number | null;
    call_date?: string | null;
    title?: string;
    url?: string | null;
    content?: string | null;
    participants?: string[];
    source?: string | null;
  }> | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** One caller-declared portfolio holding for the Portfolio Analytics module. */
export type PortfolioAnalyticsHolding = {
  symbol: string;
  weight: number;
  units?: number | null;
  cost_basis_per_unit?: number | null;
  purchase_date?: string | null;
  sector?: string | null;
  country?: string | null;
  exchange?: string | null;
  value_score?: number | null;
  quality_score?: number | null;
  momentum_score?: number | null;
  size_score?: number | null;
  volatility_score?: number | null;
};

export type PortfolioAnalyticsPortfolio = { holdings: PortfolioAnalyticsHolding[] };

/** Sharpe/Sortino/Treynor/Alpha/Beta/Tracking Error/Information Ratio/Max Drawdown. */
export type PerformanceRatiosPayload = {
  status: "complete" | "partial" | "unavailable";
  window_days: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  treynor_ratio: number | null;
  jensen_alpha: number | null;
  beta: number | null;
  tracking_error: number | null;
  information_ratio: number | null;
  max_drawdown: number | null;
  annualized_return: number | null;
  annualized_volatility: number | null;
  risk_free_rate: number;
  limitations: string[];
};

export type PortfolioAnalyticsPerformancePayload = {
  ok?: boolean;
  available?: boolean;
  message?: string | null;
  result?: PerformanceRatiosPayload | null;
  benchmark_symbol?: string | null;
  limitations?: string[];
};

export type HeatmapCellPayload = {
  symbol: string;
  sector: string | null;
  weight: number;
  volatility: number | null;
  risk_contribution_pct: number | null;
};

export type CorrelationMatrixPayload = {
  symbols: string[];
  matrix: (number | null)[][];
  window_days: number;
};

export type RiskAttributionRowPayload = {
  symbol: string;
  weight: number;
  volatility: number | null;
  correlation_to_portfolio: number | null;
  risk_contribution_pct: number | null;
};

export type RiskAttributionPayload = {
  status: "complete" | "partial" | "unavailable";
  rows: RiskAttributionRowPayload[];
  heatmap: HeatmapCellPayload[];
  correlation_matrix: CorrelationMatrixPayload | null;
  limitations: string[];
};

export type FactorExposurePayload = {
  status: "complete" | "partial" | "unavailable";
  factors: Array<{
    factor_name: string;
    exposure_value: number | null;
    contributing_positions: number;
    total_positions: number;
  }>;
  limitations: string[];
};

export type PortfolioAnalyticsRiskPayload = {
  ok?: boolean;
  available?: boolean;
  message?: string | null;
  risk_attribution?: RiskAttributionPayload | null;
  factor_exposure?: FactorExposurePayload | null;
};

export type AllocationBreakdownPayload = {
  dimension: "sector" | "country";
  status: "complete" | "partial" | "unavailable";
  buckets: Array<{ label: string; weight: number; symbols: string[] }>;
  unclassified_weight: number;
  limitations: string[];
};

export type PortfolioAnalyticsAllocationPayload = {
  ok?: boolean;
  available?: boolean;
  message?: string | null;
  sector_allocation?: AllocationBreakdownPayload | null;
  country_allocation?: AllocationBreakdownPayload | null;
};

export type MonteCarloPayload = {
  status: "complete" | "partial" | "unavailable";
  paths: number;
  horizon_days: number;
  percentiles: Record<string, number>;
  mean_terminal_return: number | null;
  method_id: string;
  seed: number | null;
  limitations: string[];
};

export type EfficientFrontierPointPayload = {
  expected_return: number;
  volatility: number;
  weights: Record<string, number>;
};

export type EfficientFrontierPayload = {
  status: "complete" | "partial" | "unavailable";
  points: EfficientFrontierPointPayload[];
  current_portfolio_point: EfficientFrontierPointPayload | null;
  method_id: string;
  samples: number;
  limitations: string[];
};

export type PortfolioAnalyticsSimulationPayload = {
  ok?: boolean;
  available?: boolean;
  message?: string | null;
  monte_carlo?: MonteCarloPayload | null;
  efficient_frontier?: EfficientFrontierPayload | null;
};

export type ScenarioImpactPayload = {
  scenario_name: string;
  shock_pct: number;
  portfolio_impact_pct: number | null;
  per_position_impact_pct: Record<string, number>;
  method_id: string;
};

export type StressTestResultPayload = {
  scenario_id: string;
  description?: string;
  available?: boolean;
  message?: string;
  window_start?: string;
  window_end?: string;
  portfolio_return_pct?: number | null;
  per_position_return_pct?: Record<string, number>;
  positions_with_history?: number;
  positions_beta_scaled?: number;
};

export type PortfolioAnalyticsStressPayload = {
  ok?: boolean;
  available?: boolean;
  message?: string | null;
  scenarios?: ScenarioImpactPayload[];
  stress_tests?: StressTestResultPayload[];
  stress_window_catalog?: Record<
    string,
    { start: string; end: string; description: string }
  >;
};

export type PositionLimitBreachPayload = {
  label: string;
  limit_type: string;
  limit_value: number;
  actual_value: number;
  breached: boolean;
};

export type RebalancingTradePayload = {
  symbol: string;
  current_weight: number;
  target_weight: number;
  drift: number;
  suggested_action: "increase" | "decrease" | "hold";
  suggested_delta_weight: number;
};

export type PortfolioAnalyticsConstraintsPayload = {
  ok?: boolean;
  available?: boolean;
  message?: string | null;
  position_limits?: {
    status: "complete" | "partial" | "unavailable";
    breaches: PositionLimitBreachPayload[];
    checks: PositionLimitBreachPayload[];
  } | null;
  rebalancing?: {
    status: "complete" | "partial" | "unavailable";
    trades: RebalancingTradePayload[];
    total_drift: number;
    disclaimer: string;
  } | null;
};

export type TaxLotAnalysisPayload = {
  symbol: string;
  available: boolean;
  unrealized_gain_loss_pct: number | null;
  unrealized_gain_loss_per_unit: number | null;
  holding_period_days: number | null;
  term: "short_term" | "long_term" | null;
  harvesting_candidate: boolean;
  reason_unavailable: string | null;
};

export type PortfolioAnalyticsTaxPayload = {
  ok?: boolean;
  available?: boolean;
  message?: string | null;
  result?: {
    status: "complete" | "partial" | "unavailable";
    lots: TaxLotAnalysisPayload[];
    harvesting_candidates: string[];
    limitations: string[];
  } | null;
};

export type PortfolioAnalyticsHealthPayload = {
  ok?: boolean;
  health?: Record<string, unknown>;
};

/**
 * Portfolio Intelligence Engine (RC1 Milestone 4) — orchestration layer that
 * combines existing engine outputs (Portfolio Analytics, Valuation Engine,
 * AI Committee via linked Research Objects) into portfolio-level insights.
 * Mounted at `/portfolio/insights` — distinct from the EPIC-A002
 * `/portfolio/intelligence` endpoint (caller-supplied research summary
 * only, no engine orchestration). Stateless; holdings + optional linked
 * Research Objects are supplied by the caller.
 */
export type IntelligenceStatus = "complete" | "partial" | "unavailable";

export type PortfolioInsightsRequestBody = {
  portfolio?: PortfolioAnalyticsPortfolio | null;
  research_objects?: Record<string, unknown> | unknown[] | null;
  reports?: Record<string, unknown> | unknown[] | null;
  snapshots?: Record<string, unknown> | unknown[] | null;
  snapshot_ids?: Record<string, string> | null;
  benchmark_symbol?: string | null;
  window_days?: number;
  as_of?: string | null;
};

export type HealthSubScorePayload = {
  name: string;
  available: boolean;
  score: number | null;
  weight: number;
  contribution: number | null;
  explanation: string;
};

export type HealthScorePayload = {
  status: IntelligenceStatus;
  score: number | null;
  components: HealthSubScorePayload[];
  method_id: string;
  limitations: string[];
};

export type ConcentrationFlagPayload = {
  kind: "position" | "sector" | "industry" | "style" | "country";
  label: string;
  weight: number;
  threshold: number;
  symbols: string[];
};

export type ConcentrationBucketPayload = { label: string; weight: number; symbols: string[] };

export type ConcentrationAnalysisPayload = {
  status: IntelligenceStatus;
  largest_holdings: Array<{ symbol: string; weight: number; weight_pct_of_portfolio: number }>;
  sector_concentration: ConcentrationBucketPayload[];
  industry_concentration: ConcentrationBucketPayload[];
  style_concentration: ConcentrationBucketPayload[];
  country_concentration: ConcentrationBucketPayload[];
  herfindahl_index: number | null;
  flags: ConcentrationFlagPayload[];
  limitations: string[];
};

export type ValuationHeatmapRowPayload = {
  symbol: string;
  weight: number;
  valuation_class: "undervalued" | "fairly_valued" | "overvalued" | "unavailable";
  margin_of_safety: number | null;
  confidence: number | null;
  message: string | null;
};

export type ValuationHeatmapPayload = {
  status: IntelligenceStatus;
  rows: ValuationHeatmapRowPayload[];
  undervalued_weight: number;
  fairly_valued_weight: number;
  overvalued_weight: number;
  unavailable_weight: number;
  method_id: string;
  limitations: string[];
};

export type RiskHighlightPayload = {
  symbol: string;
  weight: number;
  volatility: number | null;
  risk_contribution_pct: number | null;
};

export type PortfolioRiskSummaryPayload = {
  status: IntelligenceStatus;
  beta: number | null;
  annualized_volatility: number | null;
  max_drawdown: number | null;
  tracking_error: number | null;
  value_at_risk_95: number | null;
  value_at_risk_method: string | null;
  conditional_value_at_risk_95: number | null;
  stress_test_count: number;
  monte_carlo_available: boolean;
  highest_risk_holdings: RiskHighlightPayload[];
  limitations: string[];
};

export type PortfolioRecommendationPayload = {
  symbol: string;
  action: "increase" | "reduce" | "hold" | "review" | "watch";
  reason: string;
  supporting_metrics: Record<string, unknown>;
  confidence: number | null;
};

export type DriftRowPayload = {
  label: string;
  weight: number;
  baseline_weight: number;
  direction: "overweight" | "underweight" | "missing" | "in_line";
};

export type DriftAnalysisPayload = {
  status: IntelligenceStatus;
  sector_drift: DriftRowPayload[];
  missing_sectors: string[];
  style_drift: DriftRowPayload[];
  cap_drift: DriftRowPayload[];
  method_id: string;
  limitations: string[];
};

export type DiversificationScorePayload = {
  status: IntelligenceStatus;
  score: number | null;
  holding_count: number;
  sector_count: number;
  average_pairwise_correlation: number | null;
  largest_position_weight: number | null;
  position_herfindahl_index: number | null;
  risk_herfindahl_index: number | null;
  explanation: string[];
  limitations: string[];
};

export type OpportunityEntryPayload = { symbol: string; value: number; weight: number };

export type OpportunityRankingPayload = {
  status: IntelligenceStatus;
  highest_margin_of_safety: OpportunityEntryPayload[];
  highest_expected_cagr: OpportunityEntryPayload[];
  best_quality: OpportunityEntryPayload[];
  lowest_risk: OpportunityEntryPayload[];
  highest_conviction: OpportunityEntryPayload[];
  limitations: string[];
};

export type ScenarioCasePayload = { case: "bear" | "base" | "bull"; implied_return_pct: number | null };

export type PortfolioScenarioSummaryPayload = {
  status: IntelligenceStatus;
  cases: ScenarioCasePayload[];
  expected_cagr: number | null;
  expected_cagr_basis: string | null;
  worst_case_drawdown: number | null;
  worst_case_drawdown_basis: string | null;
  confidence: number | null;
  confidence_basis: string | null;
  method_id: string;
  limitations: string[];
};

export type PortfolioInsightsPayload = {
  ok?: boolean;
  available: boolean;
  message: string | null;
  service_version?: string;
  holding_count?: number;
  health_score?: HealthScorePayload;
  concentration?: ConcentrationAnalysisPayload;
  valuation_heatmap?: ValuationHeatmapPayload;
  risk_summary?: PortfolioRiskSummaryPayload;
  recommendations?: PortfolioRecommendationPayload[];
  drift?: DriftAnalysisPayload;
  diversification?: DiversificationScorePayload;
  opportunities?: OpportunityRankingPayload;
  scenario?: PortfolioScenarioSummaryPayload;
  limitations: string[];
};

export type PortfolioInsightsHealthPayload = {
  ok?: boolean;
  available: boolean;
  message: string | null;
  health_score?: HealthScorePayload;
  diversification?: DiversificationScorePayload;
  concentration?: ConcentrationAnalysisPayload;
  limitations: string[];
};

export type PortfolioInsightsRecommendationsPayload = {
  ok?: boolean;
  available: boolean;
  message: string | null;
  recommendations?: PortfolioRecommendationPayload[];
  limitations: string[];
};

export type PortfolioInsightsOpportunitiesPayload = {
  ok?: boolean;
  available: boolean;
  message: string | null;
  opportunities?: OpportunityRankingPayload;
  limitations: string[];
};

export type PortfolioInsightsScenarioPayload = {
  ok?: boolean;
  available: boolean;
  message: string | null;
  scenario?: PortfolioScenarioSummaryPayload;
  limitations: string[];
};

/**
 * Server-side Portfolio persistence (RC1 Milestone 3) — replaces browser-only
 * localStorage. Every route requires authentication; ownership is enforced
 * server-side by user_id (never trust a client-supplied identity).
 */
export type ServerPortfolio = {
  portfolio_id: string;
  user_id: string;
  org_id: string | null;
  name: string;
  is_default: boolean;
  benchmark_symbol: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
};

export type ServerHolding = {
  holding_id: string;
  portfolio_id: string;
  symbol: string;
  weight: number;
  units: number | null;
  cost_basis_per_unit: number | null;
  purchase_date: string | null;
  sector: string | null;
  country: string | null;
  exchange: string | null;
  value_score: number | null;
  quality_score: number | null;
  momentum_score: number | null;
  size_score: number | null;
  volatility_score: number | null;
  created_at: string;
  updated_at: string;
};

export type ServerTransaction = {
  transaction_id: string;
  portfolio_id: string;
  transaction_type:
    | "buy"
    | "sell"
    | "dividend"
    | "bonus"
    | "split"
    | "rights"
    | "fee"
    | "tax"
    | "cash_deposit"
    | "cash_withdrawal";
  transaction_date: string;
  symbol: string | null;
  quantity: number | null;
  price: number | null;
  amount: number | null;
  currency: string;
  notes: string | null;
  created_at: string;
};

export type ServerWatchlistItem = {
  item_id: string;
  portfolio_id: string;
  symbol: string;
  label: string | null;
  added_at: string;
};

type PortfolioEnvelope<T> = {
  ok: boolean;
  result?: T;
  error?: string;
  message?: string | null;
};

async function request<T>(
  path: string,
  init: RequestInit = {},
  options: RequestOptions = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = options.token;
  if (token && token !== "__cookie__") {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${env.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;

  let response: Response;
  try {
    const cookieMode =
      process.env.NEXT_PUBLIC_COOKIE_AUTH !== "false" &&
      process.env.NEXT_PUBLIC_COOKIE_AUTH !== "0";
    let csrf: Record<string, string> = {};
    if (cookieMode && typeof window !== "undefined") {
      try {
        const { csrfHeaders } = await import("@/lib/auth/cookieSession");
        csrf = csrfHeaders();
      } catch {
        csrf = {};
      }
      for (const [k, v] of Object.entries(csrf)) {
        if (!headers.has(k)) headers.set(k, v);
      }
    }
    response = await fetch(url, {
      ...init,
      headers,
      signal: options.signal,
      credentials: cookieMode ? "include" : init.credentials,
    });
  } catch (err) {
    const aborted =
      options.signal?.aborted ||
      (err instanceof DOMException && err.name === "AbortError");
    throw new ApiClientError(
      aborted ? "Request timed out or was cancelled" : "API unavailable",
      aborted ? 408 : 0,
      {
        ok: false,
        error: aborted ? "TIMEOUT" : "NETWORK_ERROR",
        detail: aborted
          ? "Request timed out or was cancelled"
          : "Unable to reach the API service",
        api_version: "v1",
        status_code: aborted ? 408 : 0,
      },
    );
  }

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const body = (data as ApiErrorBody | null) ?? null;
    throw new ApiClientError(
      body?.message || body?.detail || body?.error || `HTTP ${response.status}`,
      response.status,
      body,
    );
  }

  return data as T;
}

export const api = {
  health: (options?: RequestOptions) =>
    request<HealthResponse>("/health", { method: "GET" }, options),

  platform: (options?: RequestOptions) =>
    request<PlatformInfoResponse>("/platform", { method: "GET" }, options),

  version: (options?: RequestOptions) =>
    request<VersionResponse>("/version", { method: "GET" }, options),

  capabilities: (options?: RequestOptions) =>
    request<CapabilitiesResponse>("/capabilities", { method: "GET" }, options),

  validateAnalyse: (body: AnalyseRequest, options?: RequestOptions) =>
    request<ValidateResponse>(
      "/validate",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  analyse: (body: AnalyseRequest, options?: RequestOptions) =>
    request<AnalyseResponse>(
      "/analyse",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  login: (body: {
    username?: string;
    password?: string;
    api_key_id?: string;
    api_key_secret?: string;
  }) =>
    request<ApiResponse<LoginPayload>>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  refresh: (body: { refresh_token: string }, options?: RequestOptions) =>
    request<
      ApiResponse<{
        access_token: string;
        refresh_token?: string;
        token_type: string;
        expires_in?: number;
        session_id?: string;
      }>
    >(
      "/auth/refresh",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  analyzeCompany: (
    body: {
      symbol: string;
      asset_class?: string;
      currency?: string;
      start: string;
      end: string;
      as_decision_pack?: boolean;
    },
    options?: RequestOptions,
  ) =>
    request<ApiResponse<AnalyzeCompanyPayload>>(
      "/analyze/company",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  getReport: (reportId: string, options?: RequestOptions) =>
    request<ReportResponse>(
      `/report/${encodeURIComponent(reportId)}`,
      { method: "GET" },
      options,
    ),

  copilotComplete: (
    body: import("@/lib/api/copilotTypes").CopilotCompleteRequestBody,
    options?: RequestOptions,
  ) =>
    request<import("@/lib/api/copilotTypes").CopilotCompleteResponseBody>(
      "/copilot/complete",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  copilotStream: async (
    body: import("@/lib/api/copilotTypes").CopilotCompleteRequestBody,
    options?: RequestOptions,
  ) => {
    const headers = new Headers();
    headers.set("Accept", "text/event-stream");
    headers.set("Content-Type", "application/json");
    if (options?.token) {
      headers.set("Authorization", `Bearer ${options.token}`);
    }
    const url = `${env.apiBaseUrl}/copilot/stream`;
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: options?.signal,
    });
    if (!response.ok || !response.body) {
      throw new ApiClientError(`HTTP ${response.status}`, response.status);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const chunks: import("@/lib/api/copilotTypes").CopilotStreamChunkBody[] = [];
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          chunks.push(
            JSON.parse(line.slice(6)) as import("@/lib/api/copilotTypes").CopilotStreamChunkBody,
          );
        } catch {
          // ignore malformed chunks
        }
      }
    }
    return chunks;
  },

  copilotProviders: (options?: RequestOptions) =>
    request<import("@/lib/api/copilotTypes").CopilotProvidersResponseBody>(
      "/copilot/providers",
      { method: "GET" },
      options,
    ),

  /** Authenticated market quote (EPIC-D001) — never invents missing fields. */
  marketQuote: (
    symbol: string,
    options?: RequestOptions & { exchange?: string | null },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) {
      params.set("exchange", options.exchange);
    }
    return request<import("@/lib/institutional-dashboard/mapInstitutionalDashboard").MarketQuotePayload>(
      `/market/quote?${params.toString()}`,
      { method: "GET" },
      options,
    );
  },

  marketHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; provider: Record<string, unknown> }>(
      "/market/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated financial statements (EPIC-D002) — never invents missing fields. */
  financialStatements: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      period_type?: string | null;
      limit?: number;
      include_restated?: boolean;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.period_type) params.set("period_type", options.period_type);
    if (options?.limit != null) params.set("limit", String(options.limit));
    if (options?.include_restated != null) {
      params.set("include_restated", options.include_restated ? "true" : "false");
    }
    return request<
      import("@/lib/institutional-dashboard/mapInstitutionalDashboard").FinancialStatementsPayload
    >(`/fundamentals/statements?${params.toString()}`, { method: "GET" }, options);
  },

  fundamentalsHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; provider: Record<string, unknown> }>(
      "/fundamentals/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated corporate actions (EPIC-D003) — never invents events. */
  corporateActions: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      action_type?: string | null;
      start_date?: string | null;
      end_date?: string | null;
      limit?: number;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.action_type) params.set("action_type", options.action_type);
    if (options?.start_date) params.set("start_date", options.start_date);
    if (options?.end_date) params.set("end_date", options.end_date);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<
      import("@/lib/institutional-dashboard/mapInstitutionalDashboard").CorporateActionsPayload
    >(`/corporate-actions?${params.toString()}`, { method: "GET" }, options);
  },

  corporateActionsHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; provider: Record<string, unknown> }>(
      "/corporate-actions/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated historical series (EPIC-D004) — never invents history. */
  historicalSeries: (
    symbol: string,
    seriesKind: string,
    options?: RequestOptions & {
      exchange?: string | null;
      frequency?: string | null;
      start_date?: string | null;
      end_date?: string | null;
      limit?: number;
    },
  ) => {
    const params = new URLSearchParams({
      symbol: symbol.trim().toUpperCase(),
      series_kind: seriesKind,
    });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.frequency) params.set("frequency", options.frequency);
    if (options?.start_date) params.set("start_date", options.start_date);
    if (options?.end_date) params.set("end_date", options.end_date);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<
      import("@/lib/institutional-dashboard/mapInstitutionalDashboard").HistoricalSeriesPayload
    >(`/historical/series?${params.toString()}`, { method: "GET" }, options);
  },

  historicalHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; provider: Record<string, unknown> }>(
      "/historical/health",
      { method: "GET" },
      options,
    ),

  /** Unified authenticated data gateway (EPIC-D005). */
  dataBundle: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      include_market_quote?: boolean;
      include_financial_statements?: boolean;
      include_corporate_actions?: boolean;
      include_historical_series?: boolean;
      historical_series_kind?: string;
      historical_frequency?: string | null;
      historical_limit?: number;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.include_market_quote != null) {
      params.set("include_market_quote", String(options.include_market_quote));
    }
    if (options?.include_financial_statements != null) {
      params.set(
        "include_financial_statements",
        String(options.include_financial_statements),
      );
    }
    if (options?.include_corporate_actions != null) {
      params.set(
        "include_corporate_actions",
        String(options.include_corporate_actions),
      );
    }
    if (options?.include_historical_series != null) {
      params.set(
        "include_historical_series",
        String(options.include_historical_series),
      );
    }
    if (options?.historical_series_kind) {
      params.set("historical_series_kind", options.historical_series_kind);
    }
    if (options?.historical_frequency) {
      params.set("historical_frequency", options.historical_frequency);
    }
    if (options?.historical_limit != null) {
      params.set("historical_limit", String(options.historical_limit));
    }
    return request<{
      ok: boolean;
      symbol?: string;
      bundle?: import("@/lib/institutional-dashboard/mapInstitutionalDashboard").UnifiedDataBundlePayload;
      message?: string | null;
    }>(`/data/bundle?${params.toString()}`, { method: "GET" }, options);
  },

  dataHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; health: Record<string, unknown> }>(
      "/data/health",
      { method: "GET" },
      options,
    ),

  // -- Data Connector Framework: News/Filings/Ownership/Insider/ESG/
  // Transcripts. Each additive endpoint tries every configured provider in
  // priority order (automatic failover) and returns HTTP 200 with
  // `available: false` when no provider has data — never fabricated.

  /** Authenticated company news — never invents headlines. */
  news: (
    symbol: string,
    options?: RequestOptions & { exchange?: string | null; limit?: number },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<NewsPayload>(`/news?${params.toString()}`, { method: "GET" }, options);
  },

  newsHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/news/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated regulatory/corporate filings — never invents documents. */
  filings: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      filing_types?: string | null;
      start_date?: string | null;
      end_date?: string | null;
      limit?: number;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.filing_types) params.set("filing_types", options.filing_types);
    if (options?.start_date) params.set("start_date", options.start_date);
    if (options?.end_date) params.set("end_date", options.end_date);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<FilingsPayload>(`/filings?${params.toString()}`, { method: "GET" }, options);
  },

  filingsHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/filings/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated shareholding pattern — never invents holders. */
  ownership: (
    symbol: string,
    options?: RequestOptions & { exchange?: string | null; as_of?: string | null },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.as_of) params.set("as_of", options.as_of);
    return request<OwnershipPayload>(
      `/ownership?${params.toString()}`,
      { method: "GET" },
      options,
    );
  },

  ownershipHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/ownership/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated insider trading activity — never invents transactions. */
  insiderTrading: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      start_date?: string | null;
      end_date?: string | null;
      limit?: number;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.start_date) params.set("start_date", options.start_date);
    if (options?.end_date) params.set("end_date", options.end_date);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<InsiderTradingPayload>(
      `/insider-trading?${params.toString()}`,
      { method: "GET" },
      options,
    );
  },

  insiderTradingHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/insider-trading/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated ESG score — never invents scores. */
  esg: (symbol: string, options?: RequestOptions & { exchange?: string | null }) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    return request<EsgPayload>(`/esg?${params.toString()}`, { method: "GET" }, options);
  },

  esgHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/esg/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated earnings call transcripts — never invents content. */
  transcripts: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      year?: number | null;
      quarter?: number | null;
      limit?: number;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.year != null) params.set("year", String(options.year));
    if (options?.quarter != null) params.set("quarter", String(options.quarter));
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<TranscriptsPayload>(
      `/transcripts?${params.toString()}`,
      { method: "GET" },
      options,
    );
  },

  transcriptsHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/transcripts/health",
      { method: "GET" },
      options,
    ),

  /**
   * Portfolio Intelligence (EPIC-A002 / P9.5) — summarize linked research only.
   * Client must not invent research_objects; pass holdings/watchlist metadata only.
   */
  portfolioIntelligence: (
    body: {
      portfolio?: Record<string, unknown> | null;
      watchlist?: Record<string, unknown> | null;
      research_objects?: Record<string, unknown> | unknown[] | null;
      reports?: Record<string, unknown> | unknown[] | null;
      snapshots?: Record<string, unknown> | unknown[] | null;
      snapshot_ids?: Record<string, string> | null;
      result_id?: string | null;
      created_at?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      result?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>(
      "/portfolio/intelligence",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioIntelligenceSchema: (options?: RequestOptions) =>
    request<{ ok: boolean; schema?: Record<string, unknown> }>(
      "/portfolio/intelligence/schema",
      { method: "GET" },
      options,
    ),

  /**
   * Research Intelligence (EPIC-011B) — measurement & validation only.
   * Thin client: no outcome fabrication; missing feeds stay Data unavailable.
   */
  researchIntelligenceSchema: (options?: RequestOptions) =>
    request<{ ok: boolean; schema?: Record<string, unknown> }>(
      "/research/intelligence/schema",
      { method: "GET" },
      options,
    ),

  researchIntelligenceSnapshots: (
    params?: { symbol?: string; company?: string; limit?: number; offset?: number },
    options?: RequestOptions,
  ) => {
    const q = new URLSearchParams();
    if (params?.symbol) q.set("symbol", params.symbol);
    if (params?.company) q.set("company", params.company);
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.offset != null) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<{
      ok: boolean;
      total?: number;
      snapshots?: Record<string, unknown>[];
      windows_supported?: number[];
    }>(
      `/research/intelligence/snapshots${qs ? `?${qs}` : ""}`,
      { method: "GET" },
      options,
    );
  },

  researchIntelligenceTimeline: (
    params?: { symbol?: string; company?: string; limit?: number; offset?: number },
    options?: RequestOptions,
  ) => {
    const q = new URLSearchParams();
    if (params?.symbol) q.set("symbol", params.symbol);
    if (params?.company) q.set("company", params.company);
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.offset != null) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<{
      ok: boolean;
      total?: number;
      timeline?: Record<string, unknown>[];
      provenance?: Record<string, unknown>;
    }>(
      `/research/intelligence/timeline${qs ? `?${qs}` : ""}`,
      { method: "GET" },
      options,
    );
  },

  researchIntelligencePerformance: (
    body: {
      window_months?: number;
      horizon_prices?: Record<string, number | null>;
      result_id?: string;
      created_at?: string;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      dashboard?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>(
      "/research/intelligence/performance",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchIntelligenceCalibration: (
    body: {
      window_months?: number;
      horizon_prices?: Record<string, number | null>;
      result_id?: string;
      created_at?: string;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      calibration?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>(
      "/research/intelligence/calibration",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  /**
   * Build a canonical Research Object from an existing `/analyse` response
   * (EPIC-R001). No new scoring — passes through the already-computed
   * analysis payload and optionally fetches the D005 data bundle.
   */
  researchObject: (
    body: {
      symbol: string;
      company?: string | null;
      exchange?: string | null;
      correlation_id?: string | null;
      data_bundle?: Record<string, unknown> | null;
      analysis_payload?: Record<string, unknown> | null;
      valuation_signals?: Record<string, unknown> | null;
      fetch_data_bundle?: boolean;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      symbol?: string;
      research_object?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>(
      "/research/object",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  /** Generate an Institutional Research Report from a Research Object (EPIC-R002). */
  researchReport: (
    body: {
      research_object: Record<string, unknown>;
      report_id?: string | null;
      generated_at?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      symbol?: string;
      report?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>(
      "/research/report",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  /** Export an Institutional Research Report to json/csv/xlsx/pdf/docx/pptx (EPIC-R003). */
  researchExport: (
    body: {
      report: Record<string, unknown>;
      format: "json" | "csv" | "xlsx" | "pdf" | "docx" | "pptx";
      export_id?: string | null;
      exported_at?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      export?: {
        metadata: {
          filename: string;
          content_type: string;
          [key: string]: unknown;
        };
        content_base64: string;
        [key: string]: unknown;
      };
      message?: string | null;
      error?: string;
    }>(
      "/research/export",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  /**
   * Peer comparison over pre-computed Decision Pack reports (EPIC — Peers tab).
   * Reuses `comparison.QualitativeComparisonEngine` server-side; the client
   * never re-derives peer eligibility or scores.
   */
  compare: (
    body: {
      report_ids: string[];
      allow_related?: boolean;
      allow_limited?: boolean;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      result?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>("/compare", { method: "POST", body: JSON.stringify(body) }, options),

  researchIntelligenceInsights: (
    body: {
      window_months?: number;
      horizon_prices?: Record<string, number | null>;
      result_id?: string;
      top_n?: number;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      insights?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>(
      "/research/intelligence/insights",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  /**
   * Portfolio Intelligence Analytics module (additive) — Sharpe/Sortino/
   * Treynor/Alpha/Beta/Tracking Error/Information Ratio/Max Drawdown,
   * Risk Attribution, Factor Exposure, Correlation Matrix, Heatmap,
   * Sector/Country Allocation, Monte Carlo, Efficient Frontier, Scenario
   * Analysis, Stress Testing, Position Limits, Rebalancing, Tax
   * Optimization. Stateless — holdings are supplied by the caller, never
   * persisted server-side. Reuses `quantitative_risk` (Max Drawdown) and
   * authenticated `historical_series` price history server-side.
   */
  portfolioAnalyticsPerformance: (
    body: {
      portfolio?: PortfolioAnalyticsPortfolio | null;
      benchmark_symbol?: string | null;
      window_days?: number;
      risk_free_rate?: number;
      as_of?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioAnalyticsPerformancePayload>(
      "/portfolio/analytics/performance",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioAnalyticsRisk: (
    body: {
      portfolio?: PortfolioAnalyticsPortfolio | null;
      window_days?: number;
      as_of?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioAnalyticsRiskPayload>(
      "/portfolio/analytics/risk",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioAnalyticsAllocation: (
    body: { portfolio?: PortfolioAnalyticsPortfolio | null },
    options?: RequestOptions,
  ) =>
    request<PortfolioAnalyticsAllocationPayload>(
      "/portfolio/analytics/allocation",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioAnalyticsSimulation: (
    body: {
      portfolio?: PortfolioAnalyticsPortfolio | null;
      window_days?: number;
      monte_carlo_paths?: number;
      monte_carlo_horizon_days?: number;
      frontier_samples?: number;
      seed?: number | null;
      as_of?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioAnalyticsSimulationPayload>(
      "/portfolio/analytics/simulation",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioAnalyticsStress: (
    body: {
      portfolio?: PortfolioAnalyticsPortfolio | null;
      scenarios?: Array<{ name: string; shock_pct: number; default_beta?: number }> | null;
      stress_window_ids?: string[] | null;
      benchmark_symbol?: string | null;
      window_days?: number;
      as_of?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioAnalyticsStressPayload>(
      "/portfolio/analytics/stress",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioAnalyticsConstraints: (
    body: {
      portfolio?: PortfolioAnalyticsPortfolio | null;
      max_position_weight?: number | null;
      max_sector_weight?: number | null;
      sector_limits?: Record<string, number> | null;
      min_cash_weight?: number | null;
      cash_weight?: number | null;
      target_weights?: Record<string, number> | null;
      drift_threshold?: number;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioAnalyticsConstraintsPayload>(
      "/portfolio/analytics/constraints",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioAnalyticsTax: (
    body: {
      portfolio?: PortfolioAnalyticsPortfolio | null;
      as_of?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioAnalyticsTaxPayload>(
      "/portfolio/analytics/tax",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioAnalyticsHealth: (options?: RequestOptions) =>
    request<PortfolioAnalyticsHealthPayload>(
      "/portfolio/analytics/health",
      { method: "GET" },
      options,
    ),

  /**
   * Portfolio Intelligence Engine (RC1 Milestone 4) — orchestrates Portfolio
   * Analytics + linked-research valuation/quality/committee signals into
   * Health Score, Concentration, Valuation Heatmap, Risk Summary,
   * Recommendations, Drift, Diversification, Opportunities, and Scenario
   * Summary. Stateless; never persists holdings or research server-side.
   */
  portfolioInsights: (
    body: PortfolioInsightsRequestBody & {
      cash_weight?: number | null;
      stress_window_ids?: string[] | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioInsightsPayload>(
      "/portfolio/insights",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioInsightsHealth: (
    body: PortfolioInsightsRequestBody & { cash_weight?: number | null },
    options?: RequestOptions,
  ) =>
    request<PortfolioInsightsHealthPayload>(
      "/portfolio/insights/health",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioInsightsRecommendations: (
    body: PortfolioInsightsRequestBody,
    options?: RequestOptions,
  ) =>
    request<PortfolioInsightsRecommendationsPayload>(
      "/portfolio/insights/recommendations",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioInsightsOpportunities: (
    body: PortfolioInsightsRequestBody,
    options?: RequestOptions,
  ) =>
    request<PortfolioInsightsOpportunitiesPayload>(
      "/portfolio/insights/opportunities",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioInsightsScenario: (
    body: PortfolioInsightsRequestBody,
    options?: RequestOptions,
  ) =>
    request<PortfolioInsightsScenarioPayload>(
      "/portfolio/insights/scenario",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  /** Server-side Portfolio Store (RC1 Milestone 3) — authenticated, owned by user_id. */
  portfolioSchema: (options?: RequestOptions) =>
    request<{ ok: boolean; schema?: Record<string, unknown> }>(
      "/portfolio/schema",
      { method: "GET" },
      options,
    ),

  portfolioList: (options?: RequestOptions) =>
    request<PortfolioEnvelope<ServerPortfolio[]>>(
      "/portfolio",
      { method: "GET" },
      options,
    ),

  portfolioCreate: (
    body: {
      name: string;
      is_default?: boolean | null;
      benchmark_symbol?: string | null;
      metadata?: Record<string, unknown> | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioEnvelope<ServerPortfolio>>(
      "/portfolio",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioGet: (portfolioId: string, options?: RequestOptions) =>
    request<PortfolioEnvelope<ServerPortfolio>>(
      `/portfolio/${encodeURIComponent(portfolioId)}`,
      { method: "GET" },
      options,
    ),

  portfolioUpdate: (
    portfolioId: string,
    body: {
      name?: string | null;
      is_default?: boolean | null;
      metadata?: Record<string, unknown> | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioEnvelope<ServerPortfolio>>(
      `/portfolio/${encodeURIComponent(portfolioId)}`,
      { method: "PUT", body: JSON.stringify(body) },
      options,
    ),

  portfolioDelete: (portfolioId: string, options?: RequestOptions) =>
    request<PortfolioEnvelope<{ deleted: boolean }>>(
      `/portfolio/${encodeURIComponent(portfolioId)}`,
      { method: "DELETE" },
      options,
    ),

  portfolioSetBenchmark: (
    portfolioId: string,
    benchmarkSymbol: string | null,
    options?: RequestOptions,
  ) =>
    request<PortfolioEnvelope<ServerPortfolio>>(
      `/portfolio/${encodeURIComponent(portfolioId)}/benchmark`,
      {
        method: "PUT",
        body: JSON.stringify({ benchmark_symbol: benchmarkSymbol }),
      },
      options,
    ),

  portfolioListHoldings: (portfolioId: string, options?: RequestOptions) =>
    request<PortfolioEnvelope<ServerHolding[]>>(
      `/portfolio/${encodeURIComponent(portfolioId)}/holdings`,
      { method: "GET" },
      options,
    ),

  portfolioUpsertHolding: (
    portfolioId: string,
    body: {
      symbol: string;
      weight: number;
      units?: number | null;
      cost_basis_per_unit?: number | null;
      purchase_date?: string | null;
      sector?: string | null;
      country?: string | null;
      exchange?: string | null;
      value_score?: number | null;
      quality_score?: number | null;
      momentum_score?: number | null;
      size_score?: number | null;
      volatility_score?: number | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioEnvelope<ServerHolding>>(
      `/portfolio/${encodeURIComponent(portfolioId)}/holdings`,
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioRemoveHolding: (
    portfolioId: string,
    symbol: string,
    options?: RequestOptions,
  ) =>
    request<PortfolioEnvelope<{ removed: boolean }>>(
      `/portfolio/${encodeURIComponent(portfolioId)}/holdings/${encodeURIComponent(symbol)}`,
      { method: "DELETE" },
      options,
    ),

  portfolioListTransactions: (
    portfolioId: string,
    params?: { symbol?: string; limit?: number },
    options?: RequestOptions,
  ) => {
    const q = new URLSearchParams();
    if (params?.symbol) q.set("symbol", params.symbol);
    if (params?.limit != null) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<PortfolioEnvelope<ServerTransaction[]>>(
      `/portfolio/${encodeURIComponent(portfolioId)}/transactions${qs ? `?${qs}` : ""}`,
      { method: "GET" },
      options,
    );
  },

  portfolioRecordTransaction: (
    portfolioId: string,
    body: {
      transaction_type: string;
      transaction_date: string;
      symbol?: string | null;
      quantity?: number | null;
      price?: number | null;
      amount?: number | null;
      currency?: string;
      notes?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioEnvelope<ServerTransaction>>(
      `/portfolio/${encodeURIComponent(portfolioId)}/transactions`,
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioListWatchlist: (portfolioId: string, options?: RequestOptions) =>
    request<PortfolioEnvelope<ServerWatchlistItem[]>>(
      `/portfolio/${encodeURIComponent(portfolioId)}/watchlist`,
      { method: "GET" },
      options,
    ),

  portfolioAddWatchlistSymbol: (
    portfolioId: string,
    body: { symbol: string; label?: string | null },
    options?: RequestOptions,
  ) =>
    request<PortfolioEnvelope<ServerWatchlistItem>>(
      `/portfolio/${encodeURIComponent(portfolioId)}/watchlist`,
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioRemoveWatchlistSymbol: (
    portfolioId: string,
    symbol: string,
    options?: RequestOptions,
  ) =>
    request<PortfolioEnvelope<{ removed: boolean }>>(
      `/portfolio/${encodeURIComponent(portfolioId)}/watchlist/${encodeURIComponent(symbol)}`,
      { method: "DELETE" },
      options,
    ),

  /**
   * Local -> server migration (RC1 Milestone 3). Idempotent: if the user
   * already has a server default portfolio, the local snapshot is ignored
   * and `migrated: false` is returned — the caller's local copy is never
   * assumed stale and must not be deleted regardless of the outcome.
   */
  portfolioMigrate: (
    body: {
      name?: string;
      holdings?: Array<Record<string, unknown>> | null;
      watchlist?: Array<Record<string, unknown>> | null;
      benchmark_symbol?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<PortfolioEnvelope<{ migrated: boolean; portfolio: ServerPortfolio }>>(
      "/portfolio/migrate",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),
};
