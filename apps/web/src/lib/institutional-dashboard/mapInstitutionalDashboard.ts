/**
 * Map AnalyseRequest + AnalyseResponse → InstitutionalDashboardView.
 * Thin client — presentation only. No scoring, valuation, or invented market data.
 */

import type {
  AnalyseRequest,
  AnalyseResponse,
  StageSummary,
} from "@/lib/api/compositionTypes";
import {
  availableField,
  emptyExplainability,
  fieldFromUnknown,
  mapConfidenceLevel,
  unableToCalculateField,
  unavailableField,
} from "@/lib/institutional-dashboard/display";
import { validateResearchStandards } from "@/lib/institutional-dashboard/rsValidation";
import type {
  BusinessQualityView,
  DashboardField,
  ExplainabilityBlock,
  FinancialStatementsView,
  InstitutionalDashboardView,
  MarginOfSafetyView,
  MarketDataView,
  RiskView,
  ScenarioView,
  ScoreCard,
  StatementLine,
  ValuationView,
  CorporateActionsView,
  CorporateActionEventView,
  HistoricalSeriesView,
  HistoricalBarView,
} from "@/lib/institutional-dashboard/types";
import { mapAnalyseResponse } from "@/lib/intelligence/mapResponse";
import { presentAction } from "@/lib/terminology";

function stageByName(
  stages: StageSummary[],
  name: string,
): StageSummary | undefined {
  return stages.find((s) => s.stage === name);
}

function statementLines(
  record: Record<string, number | null | undefined> | undefined,
  labels: Record<string, string>,
): StatementLine[] {
  return Object.entries(labels).map(([key, label]) => {
    const raw = record?.[key];
    return {
      label,
      field:
        raw === null || raw === undefined
          ? unavailableField()
          : fieldFromUnknown(raw, "user_input", "user_input", { money: false }),
    };
  });
}

function scoreCardFromStage(
  id: string,
  title: string,
  stage: StageSummary | undefined,
  engineName: string,
): ScoreCard {
  const explainability: ExplainabilityBlock = {
    ...emptyExplainability(),
    engines: stage
      ? availableField([engineName], "calculated", "calculated_metric")
      : unavailableField(),
    confidence: stage?.confidence != null
      ? fieldFromUnknown(stage.confidence, "calculated", "calculated_metric", {
          pct: true,
        })
      : unavailableField(),
    reasoning: stage?.decision
      ? availableField(String(stage.decision), "calculated", "calculated_metric")
      : unavailableField(),
    calculation: stage?.score != null
      ? availableField(
          `Score ${stage.score}`,
          "calculated",
          "calculated_metric",
        )
      : unableToCalculateField(),
    contribution: stage?.label
      ? availableField(String(stage.label), "calculated", "calculated_metric")
      : unavailableField(),
  };

  return {
    id,
    title,
    score:
      stage?.score != null
        ? fieldFromUnknown(stage.score, "calculated", "calculated_metric")
        : unableToCalculateField(),
    label: stage?.label
      ? availableField(String(stage.label), "calculated", "calculated_metric")
      : unavailableField(),
    explainability,
  };
}

function buildFinancial(
  request: AnalyseRequest,
  statements: FinancialStatementsPayload | null | undefined,
): FinancialStatementsView {
  // Prefer authenticated filings (EPIC-D002). Fall back to user-submitted
  // analyse inputs — never invent ratios/growth (no client calculations).
  if (statements?.available && statements.authenticated && statements.periods?.length) {
    const latest = statements.periods[0];
    const income = latest?.income_statement ?? {};
    const balance = latest?.balance_sheet ?? {};
    const cash = latest?.cash_flow ?? {};
    const ratios = latest?.ratios ?? {};
    const periodLabel = latest
      ? `${latest.period_type}${latest.restated ? " (restated)" : ""} ending ${latest.period_end}`
      : null;
    const srcLabel = statements.provenance
      ? `${statements.provenance.provider_name ?? "provider"} (${statements.provenance.provider_id ?? "unknown"})`
      : "Authenticated financial statements";

    const line = (
      value: number | null | undefined,
      opts?: { money?: boolean; pct?: boolean },
    ) =>
      value == null
        ? unavailableField()
        : fieldFromUnknown(value, "verified_fact", "verified_financial_statement", opts);

    const hist =
      statements.periods.length > 1
        ? statements.periods.map((p) => ({
            label: `${p.period_type} ${p.period_end}`,
            field:
              p.income_statement?.revenue == null
                ? unavailableField()
                : fieldFromUnknown(
                    p.income_statement.revenue,
                    "verified_fact",
                    "verified_financial_statement",
                    { money: true },
                  ),
          }))
        : [{ label: "Multi-period trend", field: unavailableField() }];

    return {
      reportingPeriod: periodLabel
        ? availableField(periodLabel, "verified_fact", "verified_financial_statement")
        : unavailableField(),
      source: availableField(srcLabel, "verified_fact", "verified_financial_statement"),
      incomeStatement: [
        { label: "Revenue", field: line(income.revenue, { money: true }) },
        { label: "COGS", field: line(income.cost_of_revenue, { money: true }) },
        { label: "Gross profit", field: line(income.gross_profit, { money: true }) },
        { label: "EBIT", field: line(income.ebit, { money: true }) },
        { label: "EBITDA", field: line(income.ebitda, { money: true }) },
        { label: "Net income", field: line(income.net_income, { money: true }) },
        { label: "EPS", field: line(income.eps_basic ?? income.eps_diluted) },
      ],
      balanceSheet: [
        { label: "Cash", field: line(balance.cash_and_equivalents, { money: true }) },
        { label: "Total assets", field: line(balance.total_assets, { money: true }) },
        {
          label: "Total liabilities",
          field: line(balance.total_liabilities, { money: true }),
        },
        { label: "Equity", field: line(balance.total_equity, { money: true }) },
        { label: "Long-term debt", field: line(balance.long_term_debt, { money: true }) },
        { label: "Current assets", field: line(balance.current_assets, { money: true }) },
        {
          label: "Current liabilities",
          field: line(balance.current_liabilities, { money: true }),
        },
      ],
      cashFlow: [
        {
          label: "Operating cash flow",
          field: line(cash.operating_cash_flow, { money: true }),
        },
        { label: "Capex", field: line(cash.capital_expenditures, { money: true }) },
        { label: "Free cash flow", field: line(cash.free_cash_flow, { money: true }) },
        { label: "Dividends paid", field: line(cash.dividends_paid, { money: true }) },
        { label: "Share buybacks", field: line(cash.share_buybacks, { money: true }) },
      ],
      // Pass-through provider ratios only — never calculate on the client.
      growthRates: [
        { label: "Revenue growth", field: line(ratios.revenue_growth, { pct: true }) },
        { label: "EPS growth", field: line(ratios.eps_growth, { pct: true }) },
      ],
      margins: [
        { label: "Gross margin", field: line(ratios.gross_margin, { pct: true }) },
        {
          label: "Operating margin",
          field: line(ratios.operating_margin, { pct: true }),
        },
        { label: "Net margin", field: line(ratios.net_margin, { pct: true }) },
      ],
      capitalAllocation: [
        { label: "Capex intensity", field: unavailableField() },
        { label: "Buybacks", field: line(cash.share_buybacks, { money: true }) },
        { label: "Dividends", field: line(cash.dividends_paid, { money: true }) },
      ],
      ratios: [
        { label: "ROE", field: line(ratios.roe, { pct: true }) },
        { label: "ROCE", field: line(ratios.roce, { pct: true }) },
        { label: "Debt / Equity", field: line(ratios.debt_to_equity) },
        {
          label: "Working capital",
          field: line(ratios.working_capital, { money: true }),
        },
      ],
      historicalTrends: hist,
    };
  }

  const fs = request.financial_statements;
  const period = fs?.period;
  const periodLabel = period
    ? `${period.period_type} ending ${period.period_end}`
    : null;

  return {
    reportingPeriod: periodLabel
      ? availableField(periodLabel, "user_input", "user_input")
      : unavailableField(),
    source: availableField(
      "Analysis request financial statements (user-submitted inputs)",
      "user_input",
      "user_input",
    ),
    incomeStatement: statementLines(fs?.income_statement, {
      revenue: "Revenue",
      cogs: "COGS",
      gross_profit: "Gross profit",
      ebit: "EBIT",
      ebitda: "EBITDA",
      net_income: "Net income",
      eps: "EPS",
    }),
    balanceSheet: statementLines(fs?.balance_sheet, {
      cash: "Cash",
      total_assets: "Total assets",
      total_liabilities: "Total liabilities",
      equity: "Equity",
      long_term_debt: "Long-term debt",
      current_assets: "Current assets",
      current_liabilities: "Current liabilities",
    }),
    cashFlow: statementLines(fs?.cash_flow, {
      operating_cash_flow: "Operating cash flow",
      capex: "Capex",
      free_cash_flow: "Free cash flow",
      dividends_paid: "Dividends paid",
      share_buybacks: "Share buybacks",
    }),
    growthRates: [
      { label: "Revenue growth", field: unableToCalculateField() },
      { label: "EPS growth", field: unableToCalculateField() },
    ],
    margins: [
      {
        label: "Gross margin",
        field: unableToCalculateField(),
      },
      { label: "Operating margin", field: unableToCalculateField() },
      { label: "Net margin", field: unableToCalculateField() },
    ],
    capitalAllocation: [
      { label: "Capex intensity", field: unableToCalculateField() },
      { label: "Buybacks", field: unavailableField() },
      { label: "Dividends", field: unavailableField() },
    ],
    ratios: [
      { label: "ROE", field: unableToCalculateField() },
      { label: "ROCE", field: unableToCalculateField() },
      { label: "Debt / Equity", field: unableToCalculateField() },
      { label: "Working capital", field: unableToCalculateField() },
    ],
    historicalTrends: [
      { label: "Multi-period trend", field: unavailableField() },
    ],
  };
}

/** Authenticated financial statements payload from GET /api/v1/fundamentals/statements. */
export type FinancialStatementsPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  reporting_currency?: string | null;
  identity?: {
    symbol?: string;
    exchange?: string | null;
    company_name?: string | null;
    provider_company_id?: string | null;
    currency?: string | null;
  } | null;
  periods?: Array<{
    period_type: string;
    fiscal_year?: number;
    fiscal_quarter?: number | null;
    period_end: string;
    filing_date?: string | null;
    reporting_currency?: string;
    restated?: boolean;
    income_statement?: Record<string, number | null | undefined>;
    balance_sheet?: Record<string, number | null | undefined>;
    cash_flow?: Record<string, number | null | undefined>;
    ratios?: Record<string, number | null | undefined>;
  }> | null;
  provenance?: {
    provider_id?: string;
    provider_name?: string;
    source_type?: string;
    retrieved_at?: string;
    as_of?: string | null;
    auth_mode?: string;
  } | null;
  message?: string | null;
};

/** Authenticated market quote payload from GET /api/v1/market/quote. */
export type MarketQuotePayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  exchange?: string | null;
  currency?: string | null;
  fields?: {
    current_price?: number | null;
    open?: number | null;
    high?: number | null;
    low?: number | null;
    previous_close?: number | null;
    week_52_high?: number | null;
    week_52_low?: number | null;
    volume?: number | null;
    average_volume?: number | null;
    market_cap?: number | null;
    enterprise_value?: number | null;
    shares_outstanding?: number | null;
    dividend_yield?: number | null;
    beta?: number | null;
  } | null;
  provenance?: {
    provider_id?: string;
    provider_name?: string;
    source_type?: string;
    retrieved_at?: string;
    as_of?: string | null;
    auth_mode?: string;
  } | null;
  message?: string | null;
};

/** Authenticated corporate actions payload from GET /api/v1/corporate-actions. */
export type CorporateActionsPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: {
    symbol?: string;
    exchange?: string | null;
    company_name?: string | null;
    provider_company_id?: string | null;
  } | null;
  events?: Array<{
    action_id?: string;
    action_type?: string;
    description?: string | null;
    effective_date?: string | null;
    ex_date?: string | null;
    record_date?: string | null;
    payment_date?: string | null;
    announcement_date?: string | null;
    currency?: string | null;
    amount?: number | null;
    ratio_from?: number | null;
    ratio_to?: number | null;
    shares?: number | null;
    old_symbol?: string | null;
    new_symbol?: string | null;
  }> | null;
  provenance?: {
    provider_id?: string;
    provider_name?: string;
    source_type?: string;
    retrieved_at?: string;
  } | null;
  message?: string | null;
};

function buildCorporateActions(
  payload: CorporateActionsPayload | null | undefined,
): CorporateActionsView {
  if (!payload?.available || !payload.authenticated || !payload.events?.length) {
    return {
      source: availableField(
        "No authenticated corporate-actions provider attached",
        "unavailable",
        "unavailable",
      ),
      events: [],
      hasAuthenticatedCorporateActions: false,
    };
  }

  const srcLabel = payload.provenance
    ? `${payload.provenance.provider_name ?? "provider"} (${payload.provenance.provider_id ?? "unknown"})`
    : "Authenticated corporate actions";

  const events: CorporateActionEventView[] = payload.events.map((e) => {
    const ratio =
      e.ratio_from != null && e.ratio_to != null
        ? availableField(
            `${e.ratio_from}:${e.ratio_to}`,
            "verified_fact",
            "verified_financial_statement",
          )
        : unavailableField();
    return {
      actionType: e.action_type
        ? availableField(e.action_type, "verified_fact", "verified_financial_statement")
        : unavailableField(),
      description: e.description
        ? availableField(e.description, "verified_fact", "verified_financial_statement")
        : unavailableField(),
      effectiveDate: e.effective_date
        ? availableField(
            e.effective_date,
            "verified_fact",
            "verified_financial_statement",
          )
        : unavailableField(),
      exDate: e.ex_date
        ? availableField(e.ex_date, "verified_fact", "verified_financial_statement")
        : unavailableField(),
      recordDate: e.record_date
        ? availableField(
            e.record_date,
            "verified_fact",
            "verified_financial_statement",
          )
        : unavailableField(),
      paymentDate: e.payment_date
        ? availableField(
            e.payment_date,
            "verified_fact",
            "verified_financial_statement",
          )
        : unavailableField(),
      amount:
        e.amount == null
          ? unavailableField()
          : fieldFromUnknown(e.amount, "verified_fact", "verified_financial_statement", {
              money: true,
            }),
      ratio,
    };
  });

  return {
    source: availableField(srcLabel, "verified_fact", "verified_financial_statement"),
    events,
    hasAuthenticatedCorporateActions: true,
  };
}

/** Authenticated historical series payload from GET /api/v1/historical/series. */
export type HistoricalSeriesPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  series_kind?: string;
  frequency?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  bars?: Array<{
    date?: string;
    open?: number | null;
    high?: number | null;
    low?: number | null;
    close?: number | null;
    volume?: number | null;
  }> | null;
  points?: Array<{ date?: string; value?: number | null }> | null;
  snapshots?: Array<{ as_of?: string; fields?: Record<string, number | null> }> | null;
  provenance?: {
    provider_id?: string;
    provider_name?: string;
    source_type?: string;
    retrieved_at?: string;
  } | null;
  message?: string | null;
};

/** Unified gateway payload from GET /api/v1/data/bundle (EPIC-D005). */
export type UnifiedDataBundlePayload = {
  authenticated_gateway?: boolean;
  identity?: {
    symbol?: string;
    exchange?: string | null;
    company_name?: string | null;
    provider_company_id?: string | null;
    currency?: string | null;
  };
  market_quote?: {
    status?: { available?: boolean; authenticated?: boolean; status?: string };
    payload?: MarketQuotePayload | null;
    provenance?: MarketQuotePayload["provenance"];
  };
  financial_statements?: {
    status?: { available?: boolean; authenticated?: boolean; status?: string };
    payload?: FinancialStatementsPayload | null;
    provenance?: FinancialStatementsPayload["provenance"];
  };
  corporate_actions?: {
    status?: { available?: boolean; authenticated?: boolean; status?: string };
    payload?: CorporateActionsPayload | null;
    provenance?: CorporateActionsPayload["provenance"];
  };
  historical_series?: {
    status?: { available?: boolean; authenticated?: boolean; status?: string };
    payload?: HistoricalSeriesPayload | null;
    provenance?: HistoricalSeriesPayload["provenance"];
  };
  retrieval?: {
    partial?: boolean;
    any_available?: boolean;
    all_available?: boolean;
  };
  health?: Record<string, unknown>;
};

/** Map unified gateway sections → individual authenticated payloads for thin mappers. */
export function payloadsFromUnifiedBundle(
  bundle: UnifiedDataBundlePayload | null | undefined,
): {
  marketQuote: MarketQuotePayload | null;
  financialStatements: FinancialStatementsPayload | null;
  corporateActions: CorporateActionsPayload | null;
  historicalSeries: HistoricalSeriesPayload | null;
} {
  const unavailable = { message: "Data unavailable." as const };

  const mq = bundle?.market_quote;
  const fs = bundle?.financial_statements;
  const ca = bundle?.corporate_actions;
  const hs = bundle?.historical_series;

  const marketQuote: MarketQuotePayload | null =
    mq?.status?.available && mq.payload
      ? {
          ...mq.payload,
          ok: true,
          available: true,
          authenticated: true,
          provenance: mq.provenance ?? mq.payload.provenance,
        }
      : {
          ok: true,
          available: false,
          authenticated: false,
          fields: null,
          provenance: null,
          ...unavailable,
        };

  const financialStatements: FinancialStatementsPayload | null =
    fs?.status?.available && fs.payload
      ? {
          ...fs.payload,
          ok: true,
          available: true,
          authenticated: true,
          provenance: fs.provenance ?? fs.payload.provenance,
        }
      : {
          ok: true,
          available: false,
          authenticated: false,
          periods: null,
          provenance: null,
          ...unavailable,
        };

  const corporateActions: CorporateActionsPayload | null =
    ca?.status?.available && ca.payload
      ? {
          ...ca.payload,
          ok: true,
          available: true,
          authenticated: true,
          provenance: ca.provenance ?? ca.payload.provenance,
        }
      : {
          ok: true,
          available: false,
          authenticated: false,
          events: null,
          provenance: null,
          ...unavailable,
        };

  const historicalSeries: HistoricalSeriesPayload | null =
    hs?.status?.available && hs.payload
      ? {
          ...hs.payload,
          ok: true,
          available: true,
          authenticated: true,
          provenance: hs.provenance ?? hs.payload.provenance,
        }
      : {
          ok: true,
          available: false,
          authenticated: false,
          bars: null,
          points: null,
          snapshots: null,
          provenance: null,
          ...unavailable,
        };

  return { marketQuote, financialStatements, corporateActions, historicalSeries };
}

function buildHistorical(
  payload: HistoricalSeriesPayload | null | undefined,
): HistoricalSeriesView {
  if (!payload?.available || !payload.authenticated) {
    return {
      source: availableField(
        "No authenticated historical-series provider attached",
        "unavailable",
        "unavailable",
      ),
      seriesKind: unavailableField(),
      frequency: unavailableField(),
      dateRange: unavailableField(),
      bars: [],
      pointCount: unavailableField(),
      snapshotCount: unavailableField(),
      hasAuthenticatedHistoricalSeries: false,
    };
  }

  const srcLabel = payload.provenance
    ? `${payload.provenance.provider_name ?? "provider"} (${payload.provenance.provider_id ?? "unknown"})`
    : "Authenticated historical series";
  const range =
    payload.start_date || payload.end_date
      ? `${payload.start_date ?? "…"} → ${payload.end_date ?? "…"}`
      : null;

  const bars: HistoricalBarView[] = (payload.bars ?? []).slice(-5).map((b) => ({
    date: b.date
      ? availableField(b.date, "verified_fact", "authenticated_market_data")
      : unavailableField(),
    open:
      b.open == null
        ? unavailableField()
        : fieldFromUnknown(b.open, "verified_fact", "authenticated_market_data", {
            money: true,
          }),
    high:
      b.high == null
        ? unavailableField()
        : fieldFromUnknown(b.high, "verified_fact", "authenticated_market_data", {
            money: true,
          }),
    low:
      b.low == null
        ? unavailableField()
        : fieldFromUnknown(b.low, "verified_fact", "authenticated_market_data", {
            money: true,
          }),
    close:
      b.close == null
        ? unavailableField()
        : fieldFromUnknown(b.close, "verified_fact", "authenticated_market_data", {
            money: true,
          }),
    volume:
      b.volume == null
        ? unavailableField()
        : fieldFromUnknown(b.volume, "verified_fact", "authenticated_market_data"),
  }));

  const hasObs =
    (payload.bars?.length ?? 0) > 0 ||
    (payload.points?.length ?? 0) > 0 ||
    (payload.snapshots?.length ?? 0) > 0;

  return {
    source: availableField(srcLabel, "verified_fact", "authenticated_market_data"),
    seriesKind: payload.series_kind
      ? availableField(payload.series_kind, "verified_fact", "authenticated_market_data")
      : unavailableField(),
    frequency: payload.frequency
      ? availableField(payload.frequency, "verified_fact", "authenticated_market_data")
      : unavailableField(),
    dateRange: range
      ? availableField(range, "verified_fact", "authenticated_market_data")
      : unavailableField(),
    bars,
    pointCount: availableField(
      String(payload.points?.length ?? 0),
      "verified_fact",
      "authenticated_market_data",
    ),
    snapshotCount: availableField(
      String(payload.snapshots?.length ?? 0),
      "verified_fact",
      "authenticated_market_data",
    ),
    hasAuthenticatedHistoricalSeries: hasObs,
  };
}

function buildMarket(quote: MarketQuotePayload | null | undefined): MarketDataView {
  // CV-001 / RS-002: only authenticated provider payloads populate fields.
  const u = (): DashboardField => unavailableField();
  if (!quote?.available || !quote.authenticated || !quote.fields) {
    return {
      currentPrice: u(),
      open: u(),
      high: u(),
      low: u(),
      previousClose: u(),
      week52High: u(),
      week52Low: u(),
      volume: u(),
      averageVolume: u(),
      marketCap: u(),
      enterpriseValue: u(),
      dividendYield: u(),
      sharesOutstanding: u(),
      beta: u(),
      timestamp: u(),
      source: availableField(
        "No authenticated market-data provider attached",
        "unavailable",
        "unavailable",
      ),
      hasAuthenticatedMarketData: false,
    };
  }

  const f = quote.fields;
  const srcLabel = quote.provenance
    ? `${quote.provenance.provider_name ?? "provider"} (${quote.provenance.provider_id ?? "unknown"})`
    : "Authenticated market provider";
  const ts = quote.provenance?.as_of || quote.provenance?.retrieved_at || null;

  const num = (
    value: number | null | undefined,
    opts?: { money?: boolean; pct?: boolean },
  ): DashboardField =>
    value == null
      ? unavailableField()
      : fieldFromUnknown(value, "verified_fact", "authenticated_market_data", opts);

  return {
    currentPrice: num(f.current_price, { money: true }),
    open: num(f.open, { money: true }),
    high: num(f.high, { money: true }),
    low: num(f.low, { money: true }),
    previousClose: num(f.previous_close, { money: true }),
    week52High: num(f.week_52_high, { money: true }),
    week52Low: num(f.week_52_low, { money: true }),
    volume: num(f.volume),
    averageVolume: num(f.average_volume),
    marketCap: num(f.market_cap, { money: true }),
    enterpriseValue: num(f.enterprise_value, { money: true }),
    dividendYield: num(f.dividend_yield, { pct: true }),
    sharesOutstanding: num(f.shares_outstanding),
    beta: num(f.beta),
    timestamp: ts
      ? availableField(ts, "verified_fact", "authenticated_market_data")
      : unavailableField(),
    source: availableField(srcLabel, "verified_fact", "authenticated_market_data"),
    hasAuthenticatedMarketData: true,
  };
}

function buildValuation(
  request: AnalyseRequest,
  intelligence: ReturnType<typeof mapAnalyseResponse>,
  stages: StageSummary[],
): ValuationView {
  const signals = request.valuation_signals;
  const valuationStage = stageByName(stages, "valuation");
  const intrinsic =
    signals?.intrinsic_value_per_share != null
      ? fieldFromUnknown(
          signals.intrinsic_value_per_share,
          "user_input",
          "user_input",
          { money: true },
        )
      : unableToCalculateField();

  const methods = [
    "DCF",
    "Reverse DCF",
    "Residual Income",
    "EPV",
    "Graham",
    "Relative Valuation",
    "Consensus Valuation",
  ].map((title) => ({
    id: title.toLowerCase().replace(/\s+/g, "_"),
    title,
    value: unableToCalculateField(),
  }));

  return {
    intrinsicValue: intrinsic,
    fairValue: unableToCalculateField(),
    fairValueRange: unableToCalculateField(),
    methods,
    methodContributions: valuationStage?.label
      ? availableField(
          String(valuationStage.label),
          "calculated",
          "calculated_metric",
        )
      : unavailableField(),
    sensitivity: unavailableField(),
    assumptions: unavailableField(),
    engineVersion: intelligence.packageVersions.valuation
      ? availableField(
          intelligence.packageVersions.valuation,
          "calculated",
          "calculated_metric",
        )
      : unavailableField(),
  };
}

function buildMoS(
  request: AnalyseRequest,
  intelligence: ReturnType<typeof mapAnalyseResponse>,
): MarginOfSafetyView {
  const signals = request.valuation_signals;
  const mos =
    intelligence.marginOfSafety != null
      ? fieldFromUnknown(
          intelligence.marginOfSafety,
          "calculated",
          "calculated_metric",
          { pct: true },
        )
      : signals?.margin_of_safety != null
        ? fieldFromUnknown(
            signals.margin_of_safety,
            "user_input",
            "user_input",
            { pct: true },
          )
        : unableToCalculateField();

  return {
    currentPrice:
      signals?.current_market_price != null
        ? fieldFromUnknown(
            signals.current_market_price,
            "user_input",
            "user_input",
            { money: true },
          )
        : unavailableField(),
    intrinsicValue:
      signals?.intrinsic_value_per_share != null
        ? fieldFromUnknown(
            signals.intrinsic_value_per_share,
            "user_input",
            "user_input",
            { money: true },
          )
        : unableToCalculateField(),
    marginOfSafety: mos,
    upsidePotential: unableToCalculateField(),
    downsideRisk: unableToCalculateField(),
    riskReward: unableToCalculateField(),
    valuationStatus: intelligence.ok
      ? availableField("Research complete", "calculated", "calculated_metric")
      : availableField("Partial / failed", "unknown", "unavailable"),
  };
}

function buildBusinessQuality(stages: StageSummary[]): BusinessQualityView {
  return {
    overall: scoreCardFromStage(
      "bq",
      "Business Quality",
      stageByName(stages, "business_quality_aggregator"),
      "business_quality_aggregator",
    ),
    moat: scoreCardFromStage(
      "moat",
      "Moat",
      stageByName(stages, "economic_moat"),
      "economic_moat",
    ),
    management: scoreCardFromStage(
      "management",
      "Management",
      stageByName(stages, "management_quality"),
      "management_quality",
    ),
    governance: scoreCardFromStage(
      "governance",
      "Governance",
      undefined,
      "governance",
    ),
    capitalAllocation: scoreCardFromStage(
      "capital_allocation",
      "Capital Allocation",
      undefined,
      "capital_allocation",
    ),
    financialStrength: scoreCardFromStage(
      "financial_strength",
      "Financial Strength",
      stageByName(stages, "financial_strength"),
      "financial_strength",
    ),
    predictability: scoreCardFromStage(
      "predictability",
      "Business Predictability",
      stageByName(stages, "earnings_quality"),
      "earnings_quality",
    ),
    competitivePosition: scoreCardFromStage(
      "competitive",
      "Competitive Position",
      stageByName(stages, "economic_moat"),
      "economic_moat",
    ),
    longTermOutlook: scoreCardFromStage(
      "outlook",
      "Long-Term Outlook",
      stageByName(stages, "growth_quality"),
      "growth_quality",
    ),
  };
}

function buildRisk(stages: StageSummary[]): RiskView {
  const riskStage = stageByName(stages, "risk");
  const empty = (id: string, title: string) =>
    scoreCardFromStage(id, title, undefined, "risk");
  return {
    business: empty("business_risk", "Business Risk"),
    financial: empty("financial_risk", "Financial Risk"),
    industry: empty("industry_risk", "Industry Risk"),
    macro: empty("macro_risk", "Macro Risk"),
    regulatory: empty("regulatory_risk", "Regulatory Risk"),
    execution: empty("execution_risk", "Execution Risk"),
    riskRating: riskStage?.label
      ? availableField(String(riskStage.label), "calculated", "calculated_metric")
      : unavailableField(),
    keyAssumptions: unavailableField(),
  };
}

function buildScenarios(
  intelligence: ReturnType<typeof mapAnalyseResponse>,
): ScenarioView {
  const caseOf = (id: string, title: string): ScenarioView["bull"] => ({
    id,
    title,
    narrative: unavailableField(),
    cagr: unableToCalculateField(),
    probability: unavailableField(),
  });
  return {
    bull: caseOf("bull", "Bull Case"),
    base: caseOf("base", "Base Case"),
    bear: caseOf("bear", "Bear Case"),
    expectedCagr: unableToCalculateField(),
    sensitivity: unavailableField(),
    keyDrivers: intelligence.strengths.length
      ? availableField(
          intelligence.strengths,
          "ai_interpretation",
          "ai_interpretation",
        )
      : unavailableField(),
  };
}

export function mapInstitutionalDashboard(args: {
  request: AnalyseRequest;
  response: AnalyseResponse;
  analysedAt: string | null;
  /** Optional authenticated quote from GET /api/v1/market/quote (EPIC-D001). */
  marketQuote?: MarketQuotePayload | null;
  /** Optional authenticated statements from GET /api/v1/fundamentals/statements (EPIC-D002). */
  financialStatements?: FinancialStatementsPayload | null;
  /** Optional authenticated corporate actions from GET /api/v1/corporate-actions (EPIC-D003). */
  corporateActions?: CorporateActionsPayload | null;
  /** Optional authenticated historical series from GET /api/v1/historical/series (EPIC-D004). */
  historicalSeries?: HistoricalSeriesPayload | null;
}): InstitutionalDashboardView {
  const {
    request,
    response,
    analysedAt,
    marketQuote,
    financialStatements,
    corporateActions: corporateActionsPayload,
    historicalSeries: historicalPayload,
  } = args;
  const intelligence = mapAnalyseResponse(response);
  const stages = intelligence.stages;
  const signals = request.valuation_signals;
  const rec = response.payload?.recommendation_summary;

  const market = buildMarket(marketQuote);
  const corporateActions = buildCorporateActions(corporateActionsPayload);
  const historical = buildHistorical(historicalPayload);

  const headerPrice =
    market.hasAuthenticatedMarketData &&
    market.currentPrice.presence === "available"
      ? market.currentPrice
      : signals?.current_market_price != null
        ? fieldFromUnknown(
            signals.current_market_price,
            "user_input",
            "user_input",
            { money: true },
          )
        : unavailableField();

  const intrinsic =
    signals?.intrinsic_value_per_share != null
      ? fieldFromUnknown(
          signals.intrinsic_value_per_share,
          "user_input",
          "user_input",
          { money: true },
        )
      : unableToCalculateField();

  const mos =
    intelligence.marginOfSafety != null
      ? fieldFromUnknown(
          intelligence.marginOfSafety,
          "calculated",
          "calculated_metric",
          { pct: true },
        )
      : unableToCalculateField();

  const recommendationRaw =
    rec?.decision ?? rec?.action ?? rec?.recommendation ?? null;
  const recommendation =
    recommendationRaw != null
      ? availableField(
          presentAction(String(recommendationRaw)),
          "calculated",
          "calculated_metric",
        )
      : unavailableField();

  const businessQuality = buildBusinessQuality(stages);
  const risk = buildRisk(stages);
  const explainabilityScores = [
    businessQuality.overall,
    businessQuality.moat,
    businessQuality.management,
    businessQuality.financialStrength,
    businessQuality.predictability,
    businessQuality.longTermOutlook,
  ];

  const financial = buildFinancial(request, financialStatements);
  const valuation = buildValuation(request, intelligence, stages);
  const marginOfSafety = buildMoS(request, intelligence);
  const scenarios = buildScenarios(intelligence);

  const packageVersionList = Object.entries(intelligence.packageVersions).map(
    ([k, v]) => `${k}@${v}`,
  );

  const audit = {
    reportId: intelligence.correlationId
      ? availableField(
          intelligence.correlationId,
          "calculated",
          "calculated_metric",
        )
      : unavailableField(),
    auditReference: intelligence.correlationId
      ? availableField(
          `corr:${intelligence.correlationId}`,
          "calculated",
          "calculated_metric",
        )
      : unavailableField(),
    generationTimestamp: analysedAt
      ? availableField(analysedAt, "calculated", "calculated_metric")
      : unavailableField(),
    marketDataTimestamp:
      market.hasAuthenticatedMarketData && market.timestamp.presence === "available"
        ? market.timestamp
        : unavailableField(),
    financialStatementPeriod: financial.reportingPeriod,
    engineVersion: intelligence.pipelineVersion
      ? availableField(
          intelligence.pipelineVersion,
          "calculated",
          "calculated_metric",
        )
      : unavailableField(),
    researchVersion: intelligence.platformVersion
      ? availableField(
          intelligence.platformVersion,
          "calculated",
          "calculated_metric",
        )
      : unavailableField(),
    rulesVersion: unavailableField(),
    dataSources: availableField(
      [
        financialStatements?.available && financialStatements.authenticated
          ? "Authenticated financial statements"
          : "User-submitted financial statements",
        "Composition pipeline stage summaries",
        ...(market.hasAuthenticatedMarketData
          ? ["Authenticated market data"]
          : ["Market data feed: not attached"]),
        ...(corporateActions.hasAuthenticatedCorporateActions
          ? ["Authenticated corporate actions"]
          : ["Corporate actions feed: not attached"]),
        ...(historical.hasAuthenticatedHistoricalSeries
          ? ["Authenticated historical series"]
          : ["Historical series feed: not attached"]),
      ],
      financialStatements?.available && financialStatements.authenticated
        ? "verified_fact"
        : "user_input",
      financialStatements?.available && financialStatements.authenticated
        ? "verified_financial_statement"
        : "user_input",
    ),
    calculationMetadata: availableField(
      `ok=${intelligence.ok}; elapsed_ms=${intelligence.totalElapsedMs ?? "n/a"}`,
      "calculated",
      "calculated_metric",
    ),
    correlationId: intelligence.correlationId
      ? availableField(
          intelligence.correlationId,
          "calculated",
          "calculated_metric",
        )
      : unavailableField(),
    packageVersions: packageVersionList.length
      ? availableField(packageVersionList, "calculated", "calculated_metric")
      : unavailableField<string[]>(),
  };

  const executive = {
    companyName: request.company
      ? availableField(request.company, "user_input", "user_input")
      : unavailableField(),
    ticker: availableField(request.ticker, "user_input", "user_input"),
    exchange: request.exchange
      ? availableField(request.exchange, "user_input", "user_input")
      : unavailableField(),
    sector: unavailableField(),
    industry: unavailableField(),
    currentMarketPrice: headerPrice,
    intrinsicValue: intrinsic,
    marginOfSafety: mos,
    fairValueRange: unableToCalculateField(),
    expectedCagr: unableToCalculateField(),
    overallScore:
      intelligence.businessQualityScore != null
        ? fieldFromUnknown(
            intelligence.businessQualityScore,
            "calculated",
            "calculated_metric",
          )
        : unableToCalculateField(),
    confidence:
      intelligence.recommendationConfidence != null
        ? fieldFromUnknown(
            intelligence.recommendationConfidence,
            "calculated",
            "calculated_metric",
            { pct: true },
          )
        : unavailableField(),
    researchStatus: availableField(
      intelligence.ok ? "Complete" : "Partial",
      "calculated",
      "calculated_metric",
    ),
    recommendation,
    reportTimestamp: audit.generationTimestamp,
    researchVersion: audit.researchVersion,
    engineVersion: audit.engineVersion,
    researchMode: availableField("Research Mode", "verified_fact", "user_input"),
    reportVersion: intelligence.pipelineVersion
      ? availableField(
          intelligence.pipelineVersion,
          "calculated",
          "calculated_metric",
        )
      : unavailableField(),
  };

  const view: InstitutionalDashboardView = {
    executive,
    market,
    financial,
    corporateActions,
    historical,
    valuation,
    marginOfSafety,
    businessQuality,
    risk,
    scenarios,
    explainabilityScores,
    audit,
    rsValidation: [],
    researchMode: true,
    ticker: request.ticker,
    confidenceLevel: mapConfidenceLevel(intelligence.recommendationConfidence),
  };

  view.rsValidation = validateResearchStandards(view);
  return view;
}
