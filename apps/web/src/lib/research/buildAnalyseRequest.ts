/**
 * Build AnalyseRequest payloads for the thin client.
 *
 * P0-01 — Production builders never clone demo ACM financials or valuation
 * signals onto another ticker. Authenticated statements are required, or the
 * path fails closed with "Data unavailable."
 */

import type {
  AnalyseRequest,
  FinancialStatementsInput,
  ValuationSignalsInput,
} from "@/lib/api/compositionTypes";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";

export const ANALYSE_DATA_UNAVAILABLE = "Data unavailable.";

export type AuthenticatedStatementsSource = {
  available?: boolean;
  authenticated?: boolean;
  reporting_currency?: string | null;
  periods?: Array<{
    period_type: string;
    period_end: string;
    fiscal_year?: number | null;
    fiscal_quarter?: number | null;
    reporting_currency?: string | null;
    income_statement?: Record<string, number | null | undefined>;
    balance_sheet?: Record<string, number | null | undefined>;
    cash_flow?: Record<string, number | null | undefined>;
  }> | null;
};

export type AnalyseRequestOverrides = {
  exchange?: string | null;
  company?: string;
  financial_statements: FinancialStatementsInput;
  valuation_signals?: ValuationSignalsInput | null;
  current_market_price?: number | null;
};

function normalizeTicker(ticker: string): string {
  const normalized = ticker.trim().toUpperCase();
  if (!normalized) {
    throw new Error(
      "Ticker is required — no default company is invented in the thin client.",
    );
  }
  return normalized;
}

/** Detect ACM demo statement clones applied to a different ticker (P0-01). */
export function isDemoStatementContamination(
  ticker: string,
  statements: FinancialStatementsInput,
): boolean {
  const normalized = ticker.trim().toUpperCase();
  if (normalized === SAMPLE_ANALYSE_REQUEST.ticker) {
    return false;
  }
  const sample = SAMPLE_ANALYSE_REQUEST.financial_statements;
  return (
    statements.income_statement?.revenue === sample.income_statement?.revenue &&
    statements.income_statement?.net_income ===
      sample.income_statement?.net_income &&
    statements.balance_sheet?.total_assets === sample.balance_sheet?.total_assets
  );
}

/**
 * Map authenticated GET /fundamentals/statements payload → analyse input.
 * Returns null when data is missing (never fabricates line items).
 */
export function financialStatementsInputFromAuthenticated(
  payload: AuthenticatedStatementsSource | null | undefined,
): FinancialStatementsInput | null {
  if (!payload?.available || !payload.authenticated) {
    return null;
  }
  const latest = payload.periods?.[0];
  if (!latest?.period_type || !latest.period_end) {
    return null;
  }
  return {
    period: {
      period_type: latest.period_type,
      period_end: latest.period_end,
      fiscal_year: latest.fiscal_year ?? null,
      fiscal_quarter: latest.fiscal_quarter ?? null,
      currency:
        latest.reporting_currency ?? payload.reporting_currency ?? "USD",
    },
    income_statement: { ...(latest.income_statement ?? {}) },
    balance_sheet: { ...(latest.balance_sheet ?? {}) },
    cash_flow: { ...(latest.cash_flow ?? {}) },
    statement_metadata: { source: "authenticated_fundamentals" },
  };
}

/**
 * Production analyse request builder.
 *
 * Requires authenticated (or otherwise caller-supplied, non-demo) statements.
 * Does not copy SAMPLE_ANALYSE_REQUEST financials or valuation_signals.
 */
export function buildAnalyseRequestForTicker(
  ticker: string,
  overrides: AnalyseRequestOverrides,
): AnalyseRequest {
  const normalized = normalizeTicker(ticker);
  const statements = overrides.financial_statements;
  if (!statements?.period?.period_type || !statements.period.period_end) {
    throw new Error(ANALYSE_DATA_UNAVAILABLE);
  }
  if (isDemoStatementContamination(normalized, statements)) {
    throw new Error(ANALYSE_DATA_UNAVAILABLE);
  }

  const request: AnalyseRequest = {
    ticker: normalized,
    exchange: overrides.exchange ?? null,
    company: overrides.company,
    financial_statements: statements,
  };
  if (overrides.valuation_signals !== undefined) {
    request.valuation_signals = overrides.valuation_signals;
  }
  if (overrides.current_market_price !== undefined) {
    request.current_market_price = overrides.current_market_price;
  }
  return request;
}

/**
 * Explicit demo/test fixture only — labeled non-production.
 * Never use from production workspace analyse mutations.
 */
export function buildDemoAnalyseRequest(
  ticker: string = SAMPLE_ANALYSE_REQUEST.ticker,
  overrides?: Partial<Pick<AnalyseRequest, "exchange" | "company">>,
): AnalyseRequest {
  const normalized = normalizeTicker(ticker);
  return {
    ...SAMPLE_ANALYSE_REQUEST,
    ticker: normalized,
    exchange: overrides?.exchange ?? SAMPLE_ANALYSE_REQUEST.exchange,
    company:
      overrides?.company ??
      (normalized === SAMPLE_ANALYSE_REQUEST.ticker
        ? SAMPLE_ANALYSE_REQUEST.company
        : `${normalized} Research (demo fixture)`),
  };
}

/**
 * Load a production AnalyseRequest from an authenticated statements fetch.
 * Fails closed with {@link ANALYSE_DATA_UNAVAILABLE} when statements are absent.
 */
export async function loadAuthenticatedAnalyseRequest(
  ticker: string,
  options: {
    exchange?: string | null;
    company?: string;
    loadStatements: () => Promise<AuthenticatedStatementsSource>;
  },
): Promise<AnalyseRequest> {
  let payload: AuthenticatedStatementsSource;
  try {
    payload = await options.loadStatements();
  } catch {
    throw new Error(ANALYSE_DATA_UNAVAILABLE);
  }
  const statements = financialStatementsInputFromAuthenticated(payload);
  if (!statements) {
    throw new Error(ANALYSE_DATA_UNAVAILABLE);
  }
  return buildAnalyseRequestForTicker(ticker, {
    exchange: options.exchange,
    company: options.company,
    financial_statements: statements,
  });
}
