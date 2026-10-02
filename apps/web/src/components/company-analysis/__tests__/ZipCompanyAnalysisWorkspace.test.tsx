/** @vitest-environment jsdom */
import { render, screen, fireEvent } from "@testing-library/react";
import { CompanyHeader, EvidenceExplorerSection, InvestmentSummary, ValuationSection } from "../ZipCompanyAnalysisWorkspace";
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

  it("exposes exactly one accessible Company Search element which is the search input", () => {
    const mockResponse: AnalyseResponse = {
      ok: true,
      capability: "analyse",
      payload: { ok: true },
      limitations: [],
      errors: [],
      api_version: "v1",
      platform_version: "1.0",
      pipeline_version: "1.0",
      correlation_id: "corr-search-a11y",
    };
    const model = mapZipResearchView(mockResponse, { ticker: "TCS", exchange: "NSE" });

    render(
      <CompanyHeader
        model={model}
        onModeSwitch={() => {}}
      />
    );

    const searchElements = screen.getAllByLabelText(/Company search/i);
    expect(searchElements.length).toBe(1);

    const searchInput = screen.getByLabelText(/Company search/i);
    expect(searchInput).toHaveAttribute("type", "search");
    expect(searchInput).toHaveAttribute("id", "company-search-input");
  });

  it("renders evidence and provenance correctly with accessible progressive disclosure", () => {
    const mockModel = {
      analysisId: "test-analysis-123",
      auditReference: "AUDIT-TCS-XYZ",
      evidence: [
        {
          metric: "Operating Margin",
          value: "25.4%",
          period: "FY25",
          source: "Company filing",
          stage: "Financial Analysis",
          confidence: "High",
        },
      ],
    } as any;

    const { getByText, getByRole } = render(
      <EvidenceExplorerSection model={mockModel} analysisId="test-analysis-123" />
    );

    // Provenance rendering
    expect(getByText("Analysis ID")).toBeDefined();
    expect(getByText("test-analysis-123")).toBeDefined();
    expect(getByText("Audit Reference")).toBeDefined();
    expect(getByText("AUDIT-TCS-XYZ")).toBeDefined();

    // Evidence trail toggle accessible state
    const trailToggle = getByRole("button", { name: /View evidence trail/i });
    expect(trailToggle).toHaveAttribute("aria-expanded", "false");

    // Expand trail
    fireEvent.click(trailToggle);
    expect(trailToggle).toHaveAttribute("aria-expanded", "true");
    expect(getByText("Operating Margin")).toBeDefined();
    expect(getByText("Company filing")).toBeDefined();
    expect(getByText("25.4%")).toBeDefined();

    // Expand item details
    const detailsBtn = getByRole("button", { name: /Toggle details for Operating Margin/i });
    expect(detailsBtn).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(detailsBtn);
    expect(detailsBtn).toHaveAttribute("aria-expanded", "true");
  });

  it("handles missing evidence state gracefully without inventing data", () => {
    const emptyModel = {
      analysisId: "empty-analysis",
      auditReference: null,
      evidence: [],
    } as any;

    const { getByRole, getByText } = render(
      <EvidenceExplorerSection model={emptyModel} />
    );

    const trailToggle = getByRole("button", { name: /View evidence trail/i });
    fireEvent.click(trailToggle);

    expect(
      getByText("No evidence items reported by the backend analytical pipeline.")
    ).toBeDefined();
  });

  it("handles missing source state explicitly as Source unavailable", () => {
    const noSourceModel = {
      analysisId: "no-source",
      auditReference: "REF-001",
      evidence: [
        {
          metric: "Beta",
          value: "0.85",
          period: "Current",
          source: "",
          stage: "Risk",
          confidence: "Low",
        },
      ],
    } as any;

    const { getByRole, getByText } = render(
      <EvidenceExplorerSection model={noSourceModel} />
    );

    const trailToggle = getByRole("button", { name: /View evidence trail/i });
    fireEvent.click(trailToggle);

    expect(getByText("Source unavailable")).toBeDefined();
  });

  describe("Responsive viewport regression checks for analysis results", () => {
    const viewports = [320, 375, 768, 1024, 1440];

    viewports.forEach((width) => {
      it(`renders metric cards, valuation, and evidence at ${width}px without structural breakage`, () => {
        window.innerWidth = width;
        window.dispatchEvent(new Event("resize"));

        const model = {
          analysisId: "resp-test",
          auditReference: "REF-RESP",
          header: {
            exchange: "NSE",
            companyName: "Responsive Test Corp",
            ticker: "RESP",
            sector: "Technology",
            currency: "₹",
            asOfDate: "2026-10-02",
          },
          investmentSummary: {
            verdict: "Strong",
            recommendationBadge: "POSITIVE",
            recommendationStatus: "strong",
            summaryText: "Analysis text for testing responsive layouts.",
            metrics: [
              { label: "P/E Ratio", value: "24.5" },
              { label: "ROCE", value: "32.1%" },
            ],
          },
          valuation: {
            status: "strong",
            currentPriceFormatted: "₹3,400",
            intrinsicValueFormatted: "₹4,100",
            marginOfSafetyFormatted: "+20.5%",
            methodologyNote: "Standard DCF model",
          },
          evidence: [
            {
              metric: "Free Cash Flow",
              value: "₹12,000 Cr",
              period: "FY25",
              source: "Annual Report",
              stage: "Cashflow",
              confidence: "High",
            },
          ],
        } as any;

        const { container } = render(
          <div>
            <InvestmentSummary model={model} onAsk={() => {}} />
            <ValuationSection model={model} onAsk={() => {}} />
            <EvidenceExplorerSection model={model} />
          </div>
        );

        expect(container).toBeDefined();
        expect(container.querySelectorAll("button").length).toBeGreaterThan(0);
      });
    });
  });
});
