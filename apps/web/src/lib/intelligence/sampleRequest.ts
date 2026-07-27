/** Default sample analyse payload for the Intelligence Workspace (demo only). */

import type { AnalyseRequest } from "@/lib/api/compositionTypes";

export const SAMPLE_ANALYSE_REQUEST: AnalyseRequest = {
  ticker: "ACM",
  exchange: "NYSE",
  company: "Acme Research Corp",
  financial_statements: {
    period: {
      period_type: "annual",
      period_end: "2024-12-31",
      fiscal_year: 2024,
      currency: "USD",
    },
    income_statement: {
      revenue: 1000.0,
      cogs: 400.0,
      gross_profit: 600.0,
      ebit: 300.0,
      ebitda: 350.0,
      interest_expense: 20.0,
      pretax_income: 280.0,
      tax: 70.0,
      net_income: 210.0,
      weighted_shares: 100.0,
      eps: 2.1,
    },
    balance_sheet: {
      cash: 150.0,
      short_term_investments: 50.0,
      accounts_receivable: 120.0,
      inventory: 80.0,
      current_assets: 450.0,
      ppe: 400.0,
      goodwill: 50.0,
      intangibles: 50.0,
      total_assets: 1000.0,
      accounts_payable: 60.0,
      short_term_debt: 50.0,
      current_liabilities: 200.0,
      long_term_debt: 200.0,
      total_liabilities: 400.0,
      retained_earnings: 300.0,
      equity: 600.0,
      total_equity: 600.0,
    },
    cash_flow: {
      operating_cash_flow: 250.0,
      capex: -80.0,
      free_cash_flow: 170.0,
      dividends_paid: -50.0,
      share_buybacks: -30.0,
      debt_issued: 10.0,
      debt_repaid: -40.0,
    },
    statement_metadata: { unit_scale: "millions" },
  },
  valuation_signals: {
    intrinsic_value_per_share: 100.0,
    current_market_price: 70.0,
    confidence: 0.7,
  },
};
