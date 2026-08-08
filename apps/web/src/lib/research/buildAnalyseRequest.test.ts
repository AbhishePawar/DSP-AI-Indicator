import { describe, expect, it } from "vitest";

import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";
import {
  ANALYSE_DATA_UNAVAILABLE,
  buildAnalyseRequestForTicker,
  buildDemoAnalyseRequest,
  financialStatementsInputFromAuthenticated,
  isDemoStatementContamination,
  loadAuthenticatedAnalyseRequest,
} from "@/lib/research/buildAnalyseRequest";

const AUTH_STATEMENTS = {
  available: true,
  authenticated: true,
  reporting_currency: "USD",
  periods: [
    {
      period_type: "annual",
      period_end: "2025-09-27",
      fiscal_year: 2025,
      income_statement: { revenue: 391_035, net_income: 93_736 },
      balance_sheet: { total_assets: 364_980, total_equity: 56_950 },
      cash_flow: { operating_cash_flow: 118_254, free_cash_flow: 98_771 },
    },
  ],
} as const;

describe("P0-01 buildAnalyseRequestForTicker", () => {
  it("builds from authenticated statements without ACM financials or valuation_signals", () => {
    const fs = financialStatementsInputFromAuthenticated(AUTH_STATEMENTS);
    expect(fs).not.toBeNull();
    const req = buildAnalyseRequestForTicker("aapl", {
      company: "Apple Inc",
      exchange: "NASDAQ",
      financial_statements: fs!,
    });
    expect(req.ticker).toBe("AAPL");
    expect(req.company).toBe("Apple Inc");
    expect(req.financial_statements.income_statement?.revenue).toBe(391_035);
    expect(req.financial_statements.income_statement?.revenue).not.toBe(
      SAMPLE_ANALYSE_REQUEST.financial_statements.income_statement?.revenue,
    );
    expect(req.valuation_signals).toBeUndefined();
  });

  it("rejects missing statements", () => {
    expect(() =>
      buildAnalyseRequestForTicker("AAPL", {
        financial_statements: {
          period: { period_type: "", period_end: "" },
        },
      }),
    ).toThrow(ANALYSE_DATA_UNAVAILABLE);
  });

  it("rejects ACM demo statement contamination on another ticker", () => {
    expect(
      isDemoStatementContamination(
        "AAPL",
        SAMPLE_ANALYSE_REQUEST.financial_statements,
      ),
    ).toBe(true);
    expect(() =>
      buildAnalyseRequestForTicker("AAPL", {
        financial_statements: SAMPLE_ANALYSE_REQUEST.financial_statements,
      }),
    ).toThrow(ANALYSE_DATA_UNAVAILABLE);
  });

  it("allows explicit demo fixture helper for tests only", () => {
    const demo = buildDemoAnalyseRequest("ACM");
    expect(demo.ticker).toBe("ACM");
    expect(demo.financial_statements.income_statement?.revenue).toBe(
      SAMPLE_ANALYSE_REQUEST.financial_statements.income_statement?.revenue,
    );
    expect(demo.valuation_signals?.intrinsic_value_per_share).toBe(100);
  });

  it("loadAuthenticatedAnalyseRequest fails closed when unavailable", async () => {
    await expect(
      loadAuthenticatedAnalyseRequest("MSFT", {
        loadStatements: async () => ({
          available: false,
          authenticated: false,
          periods: null,
          message: "Data unavailable.",
        }),
      }),
    ).rejects.toThrow(ANALYSE_DATA_UNAVAILABLE);
  });

  it("loadAuthenticatedAnalyseRequest maps authenticated periods", async () => {
    const req = await loadAuthenticatedAnalyseRequest("MSFT", {
      company: "Microsoft",
      exchange: "NASDAQ",
      loadStatements: async () => AUTH_STATEMENTS,
    });
    expect(req.ticker).toBe("MSFT");
    expect(req.financial_statements.period.period_end).toBe("2025-09-27");
    expect(req.valuation_signals).toBeUndefined();
  });
});
