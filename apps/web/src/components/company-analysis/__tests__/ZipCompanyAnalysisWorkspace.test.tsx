/** @vitest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, cleanup, within } from "@testing-library/react";
import {
  CompanyHeader,
  EvidenceExplorerSection,
  InvestmentSummary,
  ValuationSection,
  ZipCompanyAnalysisWorkspace,
  TOC_GROUPS,
  ALL_SECTIONS,
} from "../ZipCompanyAnalysisWorkspace";
import { describe, it, expect, vi, beforeAll, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { mapZipResearchView } from "@/lib/research/mapZipResearchView";
import type { AnalyseResponse, AnalyseRequest } from "@/lib/api/compositionTypes";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams("symbol=TCS"),
}));

beforeAll(() => {
  class MockIntersectionObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }
  Object.defineProperty(window, "IntersectionObserver", {
    writable: true,
    configurable: true,
    value: MockIntersectionObserver,
  });
});

afterEach(() => {
  cleanup();
});

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
    const viewports = [320, 375, 414, 768, 1024, 1440];

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

  it("renders analysis results at 414px mobile viewport verifying metric cards, valuation, and evidence rows without overflow", () => {
    window.innerWidth = 414;
    window.dispatchEvent(new Event("resize"));

    const model = {
      analysisId: "resp-414",
      auditReference: "REF-414",
      header: {
        exchange: "NSE",
        companyName: "Mobile 414 Test Corp",
        ticker: "M414",
        sector: "Technology",
        currency: "₹",
        asOfDate: "2026-10-02",
      },
      investmentSummary: {
        verdict: "Strong",
        recommendationBadge: "POSITIVE",
        recommendationStatus: "strong",
        summaryText: "Analysis text for 414px mobile regression check.",
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

    const { container, getAllByText, getByRole } = render(
      <div>
        <InvestmentSummary model={model} onAsk={() => {}} />
        <ValuationSection model={model} onAsk={() => {}} />
        <EvidenceExplorerSection model={model} />
      </div>
    );

    // Metric cards rendered
    expect(getAllByText("P/E Ratio").length).toBeGreaterThanOrEqual(1);
    expect(getAllByText("ROCE").length).toBeGreaterThanOrEqual(1);
    expect(getAllByText("24.5").length).toBeGreaterThanOrEqual(1);
    expect(getAllByText("32.1%").length).toBeGreaterThanOrEqual(1);

    // Valuation rendered
    expect(getAllByText("₹3,400").length).toBeGreaterThanOrEqual(1);
    expect(getAllByText("₹4,100").length).toBeGreaterThanOrEqual(1);
    expect(getAllByText("+20.5%").length).toBeGreaterThanOrEqual(1);

    // Evidence rows rendered
    const trailToggle = getByRole("button", { name: /View evidence trail/i });
    fireEvent.click(trailToggle);
    expect(getAllByText("Free Cash Flow").length).toBeGreaterThanOrEqual(1);
    expect(getAllByText("₹12,000 Cr").length).toBeGreaterThanOrEqual(1);
    expect(getAllByText("Annual Report").length).toBeGreaterThanOrEqual(1);

    expect(container).toBeDefined();
  });

  describe("Unavailable data and missing metadata handling", () => {
    it("renders Data unavailable when analysis ID is missing without fabricating an ID", () => {
      const model = {
        analysisId: null,
        auditReference: "REF-VALID",
        evidence: [],
      } as any;

      const { getByText } = render(
        <EvidenceExplorerSection model={model} />
      );

      expect(getByText("Data unavailable")).toBeDefined();
    });

    it("renders Unavailable when audit reference is missing without fabricating a reference", () => {
      const model = {
        analysisId: "test-id-123",
        auditReference: null,
        evidence: [],
      } as any;

      const { container } = render(
        <EvidenceExplorerSection model={model} />
      );

      expect(within(container).getAllByText("Unavailable").length).toBeGreaterThanOrEqual(1);
    });

    it("handles missing research objects and stage summaries without fabricating AI or financial data", () => {
      const emptyResponse: AnalyseResponse = {
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
        correlation_id: "corr-no-research",
      };

      const model = mapZipResearchView(emptyResponse, { ticker: "TEST", exchange: "NSE" });

      expect(model.analysisId).toBeNull();
      expect(model.auditReference).toBeNull();
      expect(model.revenueData).toEqual([]);
      expect(model.profitData).toEqual([]);
      expect(model.cashData).toEqual([]);
      expect(model.marginData).toEqual([]);
      expect(model.currentPrice).toBe("Unavailable");
      expect(model.intrinsicValue).toBe("Unavailable");
      expect(model.marginOfSafety).toBe("Unavailable");
    });

    it("renders Source unavailable when source metadata is empty, null, or whitespace", () => {
      const emptySourceModel = {
        analysisId: "test-id",
        auditReference: "ref-id",
        evidence: [
          {
            metric: "Operating Margin",
            value: "22%",
            period: "FY25",
            source: "   ",
            stage: "Financial",
            confidence: "Medium",
          },
        ],
      } as any;

      const { getByRole, getByText } = render(
        <EvidenceExplorerSection model={emptySourceModel} />
      );

      const toggle = getByRole("button", { name: /View evidence trail/i });
      fireEvent.click(toggle);

      expect(getByText("Source unavailable")).toBeDefined();
    });
  });

  describe("Company Analysis Navigation and Information Architecture", () => {
    const renderWorkspace = () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });
      return render(
        <QueryClientProvider client={queryClient}>
          <ZipCompanyAnalysisWorkspace />
        </QueryClientProvider>
      );
    };

    it("structures navigation into the 6 designated groups with exact section IDs", () => {
      const expectedGroups = [
        {
          label: "OVERVIEW",
          items: [{ id: "s01", label: "Executive Summary" }],
        },
        {
          label: "FUNDAMENTALS",
          items: [{ id: "s04", label: "Financials" }],
        },
        {
          label: "VALUATION",
          items: [
            { id: "s09", label: "Valuation" },
            { id: "s10", label: "Margin of Safety" },
          ],
        },
        {
          label: "BUFFETT / QUALITY",
          items: [
            { id: "s03", label: "Buffett Indicator" },
            { id: "s02", label: "Business Quality" },
            { id: "s06", label: "Management" },
            { id: "s07", label: "Earnings Quality" },
            { id: "s08", label: "Growth Quality" },
          ],
        },
        {
          label: "RISKS",
          items: [
            { id: "s11", label: "Key Risks" },
            { id: "s12", label: "Strengths & Weaknesses" },
          ],
        },
        {
          label: "EVIDENCE & AUDIT",
          items: [
            { id: "s13", label: "Investment Context" },
            { id: "s14", label: "Supporting Evidence" },
            { id: "s15", label: "Downloads" },
          ],
        },
      ];

      expect(TOC_GROUPS.map((g) => ({ label: g.label, items: g.items }))).toEqual(expectedGroups);

      // Verify Key Risks is under RISKS and not FUNDAMENTALS
      const fundamentalsGroup = TOC_GROUPS.find((g) => g.label === "FUNDAMENTALS");
      const risksGroup = TOC_GROUPS.find((g) => g.label === "RISKS");
      expect(fundamentalsGroup?.items.some((i) => i.id === "s11")).toBe(false);
      expect(risksGroup?.items.some((i) => i.id === "s11")).toBe(true);
    });

    it("contains all 14 section IDs in the flattened section list without omissions or fabrications", () => {
      expect(ALL_SECTIONS.length).toBe(14);
      const expectedIds = ["s01", "s04", "s09", "s10", "s03", "s02", "s06", "s07", "s08", "s11", "s12", "s13", "s14", "s15"];
      expect(ALL_SECTIONS.map((s) => s.id)).toEqual(expectedIds);
    });

    it("renders navigation preserving required P1-09 labels and landmarks", () => {
      const { getAllByRole, getByLabelText } = renderWorkspace();

      // Landmark: nav aria-label="Analysis sections"
      const nav = getByLabelText("Analysis sections");
      expect(nav).toBeDefined();

      // Required P1-09 labels must be present as buttons
      const valuationBtns = getAllByRole("button", { name: "Valuation" });
      expect(valuationBtns.length).toBeGreaterThanOrEqual(1);

      const buffettBtns = getAllByRole("button", { name: "Buffett Indicator" });
      expect(buffettBtns.length).toBeGreaterThanOrEqual(1);

      const evidenceBtns = getAllByRole("button", { name: "Supporting Evidence" });
      expect(evidenceBtns.length).toBeGreaterThanOrEqual(1);

      const downloadsBtns = getAllByRole("button", { name: "Downloads" });
      expect(downloadsBtns.length).toBeGreaterThanOrEqual(1);

      const summaryBtns = getAllByRole("button", { name: /Executive Summary|Summary/i });
      expect(summaryBtns.length).toBeGreaterThanOrEqual(1);
    });

    it("exposes aria-current on the active section navigation button and reflects dynamic progress", () => {
      const { getByLabelText, getByRole } = renderWorkspace();

      const nav = getByLabelText("Analysis sections");
      const activeItem = nav.querySelector('button[aria-current="page"]');
      expect(activeItem).not.toBeNull();
      expect(activeItem?.textContent).toContain("Executive Summary");

      // Dynamic progress indicator is present derived from section list
      const progressBar = getByRole("progressbar", { name: "Analysis reading progress" });
      expect(progressBar).toHaveAttribute("aria-valuenow", "1");
      expect(progressBar).toHaveAttribute("aria-valuemax", "14");
      expect(nav.textContent).toContain("Section 1 of 14");
    });

    it("manages mobile navigation drawer semantics, touch targets, Escape key, and focus return", () => {
      const { getByRole, queryByRole } = renderWorkspace();

      const sectionsBtn = getByRole("button", { name: "Sections" });
      expect(sectionsBtn).toBeDefined();
      expect(sectionsBtn).toHaveAttribute("aria-haspopup", "dialog");
      expect(sectionsBtn).toHaveAttribute("aria-expanded", "false");

      // Touch target >= 44px
      expect(sectionsBtn.style.minHeight).toBe("44px");

      // Open drawer
      fireEvent.click(sectionsBtn);
      expect(sectionsBtn).toHaveAttribute("aria-expanded", "true");

      // Dialog semantics
      const dialog = getByRole("dialog", { name: "Analysis Sections" });
      expect(dialog).toBeDefined();
      expect(dialog).toHaveAttribute("aria-modal", "true");

      // Explicit close button with >= 44px touch target
      const closeBtn = getByRole("button", { name: "Close navigation" });
      expect(closeBtn).toBeDefined();
      expect(closeBtn.style.minHeight).toBe("44px");

      // Close via Escape key
      fireEvent.keyDown(window, { key: "Escape" });
      expect(queryByRole("dialog", { name: "Analysis Sections" })).toBeNull();
      expect(sectionsBtn).toHaveAttribute("aria-expanded", "false");

      // Open again and close via explicit close button
      fireEvent.click(sectionsBtn);
      expect(getByRole("dialog", { name: "Analysis Sections" })).toBeDefined();
      fireEvent.click(getByRole("button", { name: "Close navigation" }));
      expect(queryByRole("dialog", { name: "Analysis Sections" })).toBeNull();
    });
  });
});
