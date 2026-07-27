/** Composition / intelligence API transport types — mirror /api/v1 DTOs only. */

export type CompositionErrorBody = {
  ok: false;
  error?: string;
  error_code?: string;
  message?: string;
  detail?: string | null;
  pipeline_stage?: string | null;
  validation_errors?: string[];
  correlation_id?: string | null;
  timestamp?: string | null;
  api_version?: string;
  status_code: number;
};

export type ValuationSignalsInput = {
  intrinsic_value_per_share?: number | null;
  current_market_price?: number | null;
  margin_of_safety?: number | null;
  premium_discount?: number | null;
  confidence?: number;
};

export type FinancialStatementsInput = {
  period: {
    period_type: string;
    period_end: string;
    fiscal_year?: number | null;
    fiscal_quarter?: number | null;
    currency?: string | Record<string, unknown>;
  };
  income_statement?: Record<string, number | null | undefined>;
  balance_sheet?: Record<string, number | null | undefined>;
  cash_flow?: Record<string, number | null | undefined>;
  statement_metadata?: Record<string, unknown>;
};

export type AnalyseRequest = {
  ticker: string;
  exchange?: string | null;
  company?: string;
  financial_statements: FinancialStatementsInput;
  valuation_signals?: ValuationSignalsInput | null;
  current_market_price?: number | null;
  stop_on_stage_failure?: boolean;
};

export type StageSummary = {
  stage: string;
  status: string;
  has_result: boolean;
  score?: number | null;
  label?: string | null;
  decision?: string | null;
  confidence?: number | null;
  error?: string | null;
  warnings?: string[];
};

export type DecisionSummary = {
  decision?: string | null;
  confidence?: number | null;
  score?: number | null;
  label?: string | null;
  margin_of_safety?: number | null;
  consensus?: string | null;
  rationale?: string | null;
  action?: string | null;
  recommendation?: string | null;
  [key: string]: unknown;
};

export type PipelinePayload = {
  ok: boolean;
  metadata?: {
    pipeline_version?: string;
    platform_version?: string;
    execution_order?: string[];
    package_versions?: Record<string, string>;
    evidence_counts?: Record<string, number>;
    confidence_summary?: Record<string, number | null>;
    warnings?: string[];
    total_elapsed_ms?: number;
    ok?: boolean;
    failed_stage?: string | null;
  };
  trace?: Array<{
    stage: string;
    status: string;
    elapsed_ms?: number;
    package?: string;
    package_version?: string | null;
    message?: string;
    error?: string | null;
  }>;
  stages?: Array<{
    stage: string;
    status: string;
    error?: string | null;
    warnings?: string[];
    has_result?: boolean;
  }>;
  stage_summaries?: StageSummary[];
  recommendation_summary?: DecisionSummary | null;
  committee_summary?: DecisionSummary | null;
  limitations?: string[];
  errors?: string[];
  has_financial_analysis?: boolean;
  has_valuation?: boolean;
  has_business_quality?: boolean;
  has_investment_recommendation?: boolean;
  has_investment_committee?: boolean;
  [key: string]: unknown;
};

export type AnalyseResponse = {
  ok: boolean;
  capability: string;
  payload: PipelinePayload;
  limitations: string[];
  errors: string[];
  api_version: string;
  platform_version: string | null;
  pipeline_version: string | null;
  correlation_id: string | null;
};

export type ValidateResponse = {
  ok: boolean;
  valid: boolean;
  errors: string[];
  warnings: string[];
  api_version: string;
};

export type VersionResponse = {
  api_version: string;
  api_package_version: string;
  platform_version: string;
  pipeline_version: string;
  docs_version: string;
  package_versions: Record<string, string>;
};

export type CapabilitiesResponse = {
  analytical_modules: string[];
  supported_reports: string[];
  pipeline_stages: string[];
  pipeline_version: string;
  platform_version: string;
  api_version: string;
  package_versions: Record<string, string>;
  platform_capabilities: string[];
};
