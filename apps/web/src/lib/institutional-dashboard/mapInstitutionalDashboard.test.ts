import { describe, expect, it } from "vitest";

import { DATA_UNAVAILABLE, UNABLE_TO_CALCULATE } from "@/lib/institutional-dashboard/types";
import {
  mapInstitutionalDashboard,
  payloadsFromUnifiedBundle,
} from "@/lib/institutional-dashboard/mapInstitutionalDashboard";
import { researchStandardsPass } from "@/lib/institutional-dashboard/rsValidation";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";
import { getPrimaryNav, breadcrumbsFor } from "@/lib/navigation";

function sampleResponse(): AnalyseResponse {
  return {
    ok: true,
    capability: "analyse",
    payload: {
      ok: true,
      metadata: {
        pipeline_version: "1.0.0-test",
        platform_version: "0.7.1",
        package_versions: { valuation: "0.12.0" },
        total_elapsed_ms: 12,
      },
      stage_summaries: [
        {
          stage: "business_quality_aggregator",
          status: "succeeded",
          has_result: true,
          score: 72,
          label: "Good",
          confidence: 0.8,
        },
        {
          stage: "economic_moat",
          status: "succeeded",
          has_result: true,
          score: 68,
          label: "Narrow",
          confidence: 0.7,
        },
      ],
      recommendation_summary: {
        decision: "hold_for_research",
        confidence: 0.75,
        margin_of_safety: 0.3,
      },
    },
    correlation_id: "corr-test-1",
    errors: [],
    limitations: [],
    api_version: "v1",
    platform_version: "0.7.1",
    pipeline_version: "1.0.0-test",
  };
}

describe("mapInstitutionalDashboard", () => {
  it("maps RS sections without fabricating market quotes", () => {
    const view = mapInstitutionalDashboard({
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
      analysedAt: "2026-07-28T00:00:00.000Z",
    });

    expect(view.market.hasAuthenticatedMarketData).toBe(false);
    expect(view.market.currentPrice.display).toBe(DATA_UNAVAILABLE);
    expect(view.corporateActions.hasAuthenticatedCorporateActions).toBe(false);
    expect(view.historical.hasAuthenticatedHistoricalSeries).toBe(false);
    expect(view.market.marketCap.display).toBe(DATA_UNAVAILABLE);
    expect(view.executive.ticker.display).toBe("ACM");
    expect(view.executive.currentMarketPrice.category).toBe("user_input");
    expect(view.executive.marginOfSafety.presence).toBe("available");
    expect(view.valuation.methods.length).toBeGreaterThan(0);
    expect(view.valuation.methods[0]?.value.display).toBe(UNABLE_TO_CALCULATE);
    expect(view.financial.incomeStatement.length).toBeGreaterThan(0);
    expect(view.explainabilityScores[0]?.explainability.formula.display).toBe(
      DATA_UNAVAILABLE,
    );
    expect(researchStandardsPass(view.rsValidation)).toBe(true);
    expect(view.rsValidation).toHaveLength(10);
  });

  it("maps authenticated market quote when provider payload is present", () => {
    const view = mapInstitutionalDashboard({
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
      analysedAt: "2026-07-28T00:00:00.000Z",
      marketQuote: {
        ok: true,
        available: true,
        authenticated: true,
        symbol: "ACM",
        fields: {
          current_price: 100.5,
          open: 99,
          high: 101,
          low: 98,
          previous_close: 99.5,
          week_52_high: 120,
          week_52_low: 80,
          volume: 1_000_000,
          average_volume: 900_000,
          market_cap: 50_000_000_000,
          enterprise_value: 55_000_000_000,
          shares_outstanding: 500_000_000,
          dividend_yield: 0.01,
          beta: 1.1,
        },
        provenance: {
          provider_id: "memory_authenticated_quote",
          provider_name: "Memory",
          source_type: "licensed_vendor",
          retrieved_at: "2026-07-28T00:00:00.000Z",
          auth_mode: "api_key",
        },
      },
    });

    expect(view.market.hasAuthenticatedMarketData).toBe(true);
    expect(view.market.currentPrice.presence).toBe("available");
    expect(view.market.currentPrice.source).toBe("authenticated_market_data");
    expect(view.executive.currentMarketPrice.source).toBe(
      "authenticated_market_data",
    );
    expect(view.market.currentPrice.display).not.toBe(DATA_UNAVAILABLE);
    expect(researchStandardsPass(view.rsValidation)).toBe(true);
  });

  it("maps authenticated financial statements when provider payload is present", () => {
    const view = mapInstitutionalDashboard({
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
      analysedAt: "2026-07-28T00:00:00.000Z",
      financialStatements: {
        ok: true,
        available: true,
        authenticated: true,
        symbol: "ACM",
        periods: [
          {
            period_type: "annual",
            period_end: "2024-12-31",
            reporting_currency: "USD",
            restated: false,
            income_statement: { revenue: 1_000_000, net_income: 100_000 },
            balance_sheet: { cash_and_equivalents: 50_000, total_equity: 400_000 },
            cash_flow: { operating_cash_flow: 120_000 },
            ratios: { roe: 0.2 },
          },
          {
            period_type: "annual",
            period_end: "2023-12-31",
            income_statement: { revenue: 900_000 },
            balance_sheet: {},
            cash_flow: {},
            ratios: {},
          },
        ],
        provenance: {
          provider_id: "memory_authenticated_statements",
          provider_name: "Memory",
          source_type: "licensed_vendor",
          retrieved_at: "2026-07-28T00:00:00.000Z",
        },
      },
    });

    expect(view.financial.source.source).toBe("verified_financial_statement");
    expect(view.financial.incomeStatement[0]?.field.presence).toBe("available");
    expect(view.financial.ratios.find((r) => r.label === "ROE")?.field.presence).toBe(
      "available",
    );
    expect(view.financial.historicalTrends.length).toBe(2);
    expect(researchStandardsPass(view.rsValidation)).toBe(true);
  });

  it("maps authenticated corporate actions when provider payload is present", () => {
    const view = mapInstitutionalDashboard({
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
      analysedAt: "2026-07-28T00:00:00.000Z",
      corporateActions: {
        ok: true,
        available: true,
        authenticated: true,
        events: [
          {
            action_id: "div-1",
            action_type: "dividend",
            ex_date: "2024-05-10",
            amount: 0.25,
          },
          {
            action_id: "split-1",
            action_type: "stock_split",
            effective_date: "2020-08-31",
            ratio_from: 1,
            ratio_to: 4,
          },
        ],
        provenance: {
          provider_id: "memory_authenticated_corporate_actions",
          provider_name: "Memory",
          source_type: "licensed_vendor",
          retrieved_at: "2026-07-28T00:00:00.000Z",
        },
      },
    });

    expect(view.corporateActions.hasAuthenticatedCorporateActions).toBe(true);
    expect(view.corporateActions.events).toHaveLength(2);
    expect(view.corporateActions.events[0]?.actionType.display).toBe("dividend");
    expect(researchStandardsPass(view.rsValidation)).toBe(true);
  });

  it("maps authenticated historical series when provider payload is present", () => {
    const view = mapInstitutionalDashboard({
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
      analysedAt: "2026-07-28T00:00:00.000Z",
      historicalSeries: {
        ok: true,
        available: true,
        authenticated: true,
        series_kind: "ohlcv",
        frequency: "daily",
        start_date: "2024-01-02",
        end_date: "2024-01-03",
        bars: [
          {
            date: "2024-01-02",
            open: 100,
            high: 105,
            low: 99,
            close: 104,
            volume: 1_000_000,
          },
          {
            date: "2024-01-03",
            open: 104,
            high: 106,
            low: 103,
            close: 105,
            volume: 1_100_000,
          },
        ],
        provenance: {
          provider_id: "memory_authenticated_historical",
          provider_name: "Memory",
          source_type: "licensed_vendor",
          retrieved_at: "2026-07-28T00:00:00.000Z",
        },
      },
    });

    expect(view.historical.hasAuthenticatedHistoricalSeries).toBe(true);
    expect(view.historical.bars.length).toBe(2);
    expect(view.historical.seriesKind.display).toBe("ohlcv");
    expect(researchStandardsPass(view.rsValidation)).toBe(true);
  });

  it("extracts section payloads from unified data bundle", () => {
    const sections = payloadsFromUnifiedBundle({
      market_quote: {
        status: { available: true, authenticated: true, status: "ok" },
        payload: {
          fields: { current_price: 10 },
          provenance: { provider_id: "mq", provider_name: "MQ" },
        },
      },
      financial_statements: {
        status: { available: false, status: "unavailable" },
        payload: null,
      },
    });
    expect(sections.marketQuote?.available).toBe(true);
    expect(sections.financialStatements?.available).toBe(false);
    expect(sections.financialStatements?.message).toBe(DATA_UNAVAILABLE);
  });

  it("never emits placeholder masks", () => {
    const view = mapInstitutionalDashboard({
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
      analysedAt: null,
    });
    const blob = JSON.stringify(view);
    expect(blob).not.toMatch(/₹XXXX|XX%|TODO|lorem/i);
  });
});

describe("institutional nav", () => {
  it("registers institutional dashboard route", () => {
    expect(
      getPrimaryNav().some((n) => n.href === "/research/institutional"),
    ).toBe(true);
  });

  it("breadcrumbs institutional without treating path as ticker", () => {
    const crumbs = breadcrumbsFor("/research/institutional");
    expect(crumbs.some((c) => c.label === "Institutional")).toBe(true);
    expect(crumbs.some((c) => c.label === "INSTITUTIONAL")).toBe(false);
  });
});
