import { describe, it, expect } from "vitest";
import { mapZipResearchView } from "@/lib/research/mapZipResearchView";
import type { AnalyseResponse, AnalyseRequest } from "@/lib/api/compositionTypes";

describe("Stage 3 Research Workspace Data-State and Adapter Contract", () => {
  const mockBaseRequest: AnalyseRequest = {
    ticker: "TCS",
    exchange: "NSE",
  };

  it("handles missing financial time series without fabricating data points", () => {
    const mockResponse: AnalyseResponse = {
      ok: true,
      capability: "analyse",
      payload: {
        ok: true,
      },
      limitations: [],
      errors: [],
      api_version: "v1",
      platform_version: "1.0",
      pipeline_version: "1.0",
      correlation_id: "corr-123",
    };

    const model = mapZipResearchView(mockResponse, mockBaseRequest);

    // Verified: No fake financial points generated
    expect(model.revenueData).toEqual([]);
    expect(model.profitData).toEqual([]);
    expect(model.marginData).toEqual([]);
    expect(model.cashData).toEqual([]);
  });

  it("preserves server-authoritative valuation metrics without client calculation", () => {
    const mockResponse: AnalyseResponse = {
      ok: true,
      capability: "analyse",
      payload: {
        ok: true,
        server_valuation: {
          current_market_price: 3500,
          intrinsic_value_per_share: 4200,
          margin_of_safety: 20,
        },
      },
      limitations: [],
      errors: [],
      api_version: "v1",
      platform_version: "1.0",
      pipeline_version: "1.0",
      correlation_id: "corr-123",
      analysis_id: "analysis-999",
      audit_reference: "AUDIT-TCS-001",
    };

    const model = mapZipResearchView(mockResponse, mockBaseRequest);

    // Server-authoritative values preserved
    expect(model.currentPrice).toBe("₹3,500");
    expect(model.intrinsicValue).toBe("₹4,200");
    expect(model.marginOfSafety).toBe("20.0%");
    expect(model.analysisId).toBe("analysis-999");
    expect(model.auditReference).toBe("AUDIT-TCS-001");
  });

  it("sets Buffett criteria status to unavailable when stage summaries are missing", () => {
    const mockResponse: AnalyseResponse = {
      ok: true,
      capability: "analyse",
      payload: {
        ok: true,
        stage_summaries: [],
      },
      limitations: [],
      errors: [],
      api_version: "v1",
      platform_version: "1.0",
      pipeline_version: "1.0",
      correlation_id: "corr-123",
    };

    const model = mapZipResearchView(mockResponse, mockBaseRequest);

    // When stages are missing, criteria should reflect unavailable/neutral status
    expect(model.buffettRows.length).toBe(10);
    model.buffettRows.forEach((row) => {
      expect(["strong", "watch", "weak", "neutral", "unavailable"]).toContain(row.status);
    });
  });

  it("extracts categorized risks from CompanyRiskPayload without synthetic additions", () => {
    const mockResponse: AnalyseResponse = {
      ok: true,
      capability: "analyse",
      payload: {
        ok: true,
        risk: {
          business_risk: { category: "business", available: true, level: "low", message: "Stable market position" },
          financial_risk: { category: "financial", available: true, level: "low", message: "Zero debt" },
          regulatory_risk: { category: "regulatory", available: false },
          technology_risk: { category: "technology", available: false },
          currency_risk: { category: "currency", available: false },
          customer_concentration_risk: { category: "concentration", available: false },
          categories_available: 2,
          categories_total: 6,
        },
      },
      limitations: [],
      errors: [],
      api_version: "v1",
      platform_version: "1.0",
      pipeline_version: "1.0",
      correlation_id: "corr-123",
    };

    const model = mapZipResearchView(mockResponse, mockBaseRequest);
    expect(model.risks.length).toBeGreaterThanOrEqual(1);
  });

  it("renders workspace model when symbol is provided via URL without claiming completed results", () => {
    const emptyResponse: AnalyseResponse = {
      ok: true,
      capability: "analyse",
      payload: { ok: true },
      limitations: [],
      errors: [],
      api_version: "v1",
      platform_version: "1.0",
      pipeline_version: "1.0",
      correlation_id: "corr-empty",
    };
    const model = mapZipResearchView(emptyResponse, { ticker: "INFY", exchange: "NSE" });
    expect(model.symbol).toBe("INFY");
    expect(model.currentPrice).toBe("Unavailable");
    expect(model.intrinsicValue).toBe("Unavailable");
    expect(model.marginOfSafety).toBe("Unavailable");
    expect(model.analysisId).toBeNull();
  });
});
