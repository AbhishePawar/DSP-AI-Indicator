/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const push = vi.fn();
const replace = vi.fn();
const navigationState = { search: "symbol=AAPL" };

vi.mock("next/navigation", () => ({
  usePathname: () => "/analysis",
  useRouter: () => ({ push, replace }),
  useSearchParams: () => new URLSearchParams(navigationState.search),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: {
      accessToken: "tok",
      refreshToken: null,
      tokenType: "Bearer",
      role: "research_analyst",
      roles: ["research_analyst"],
      permissions: ["read_research"],
      subject: "u1",
      username: "analyst",
      displayName: "Ada Analyst",
      email: "ada@example.com",
      authMethod: "rbac",
      sessionId: "s1",
      issuedAt: "2026-07-28T10:00:00.000Z",
      expiresAt: null,
      rememberMe: false,
    },
    user: {
      subject: "u1",
      username: "analyst",
      displayName: "Ada Analyst",
      email: "ada@example.com",
      role: "research_analyst",
      roles: ["research_analyst"],
      permissions: ["read_research"],
    },
  }),
}));

vi.mock("@/providers/NotificationProvider", () => ({
  useNotifications: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  }),
}));

vi.mock("@/lib/research/sessionStore", () => ({
  saveResearchSession: vi.fn(),
}));

const analyseMock = vi.fn();
const marketQuoteMock = vi.fn();
const financialStatementsMock = vi.fn();
const corporateActionsMock = vi.fn();
const copilotCompleteMock = vi.fn();
const compareMock = vi.fn();
const selectIndianListingMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    analyse: (...args: unknown[]) => analyseMock(...args),
    marketQuote: (...args: unknown[]) => marketQuoteMock(...args),
    financialStatements: (...args: unknown[]) => financialStatementsMock(...args),
    corporateActions: (...args: unknown[]) => corporateActionsMock(...args),
    copilotComplete: (...args: unknown[]) => copilotCompleteMock(...args),
    compare: (...args: unknown[]) => compareMock(...args),
    selectIndianListing: (...args: unknown[]) => selectIndianListingMock(...args),
  },
}));

import {
  ANALYSIS_SECTIONS,
  researchViewToCsv,
  researchViewToJson,
  useWorkspacePrefsStore,
} from "@/lib/company-analysis";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { buildDemoAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";
import { acknowledgeResearchDisclaimer } from "@/lib/legal";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";

const sampleResponse: AnalyseResponse = {
  ok: true,
  capability: "analyse",
  limitations: [],
  errors: [],
  api_version: "v1",
  platform_version: "1.0.0",
  pipeline_version: "1.0.0",
  correlation_id: "corr-1",
  payload: {
    ok: true,
    metadata: {
      pipeline_version: "1.0.0",
      platform_version: "1.0.0",
      execution_order: ["financial", "valuation", "investment_committee"],
      confidence_summary: { valuation: 0.7 },
      warnings: [],
      total_elapsed_ms: 120,
    },
    stage_summaries: [
      {
        stage: "valuation",
        status: "succeeded",
        has_result: true,
        score: 72,
        label: "DCF",
        decision: "hold",
        confidence: 0.7,
      },
      {
        stage: "economic_moat",
        status: "succeeded",
        has_result: true,
        score: 80,
        label: "Wide",
        decision: "durable",
        confidence: 0.8,
      },
      {
        stage: "management_quality",
        status: "succeeded",
        has_result: true,
        score: 75,
        label: "Strong",
        decision: "aligned",
        confidence: 0.75,
      },
      {
        stage: "financial_strength",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Solid",
        decision: "ok",
        confidence: 0.7,
      },
      {
        stage: "earnings_quality",
        status: "succeeded",
        has_result: true,
        score: 68,
        label: "Good",
        decision: "ok",
        confidence: 0.65,
      },
      {
        stage: "business_quality_aggregator",
        status: "succeeded",
        has_result: true,
        score: 78,
        label: "High",
        decision: "quality",
        confidence: 0.77,
      },
      {
        stage: "investment_recommendation",
        status: "succeeded",
        has_result: true,
        score: 60,
        label: "Hold",
        decision: "hold",
        confidence: 0.6,
      },
      {
        stage: "investment_committee",
        status: "succeeded",
        has_result: true,
        score: 62,
        label: "Consensus hold",
        decision: "hold",
        confidence: 0.62,
      },
      {
        stage: "financial",
        status: "succeeded",
        has_result: true,
        score: 71,
        label: "Healthy",
        decision: "ok",
        confidence: 0.7,
      },
      {
        stage: "growth_quality",
        status: "succeeded",
        has_result: true,
        score: 66,
        label: "Steady",
        decision: "ok",
        confidence: 0.66,
      },
    ],
    recommendation_summary: {
      decision: "hold",
      confidence: 0.6,
      margin_of_safety: 0.12,
      label: "Hold",
    },
    committee_summary: {
      decision: "hold",
      confidence: 0.62,
      consensus: "majority hold",
      rationale: "Minority prefers wait",
    },
    risk: {
      business_risk: {
        category: "business_risk",
        available: true,
        level: "moderate",
        source_stage: "economic_moat",
        source_rating: "narrow",
        evidence: [],
      },
      financial_risk: {
        category: "financial_risk",
        available: true,
        level: "low",
        source_stage: "financial_strength",
        source_rating: "strong",
        evidence: [],
      },
      regulatory_risk: {
        category: "regulatory_risk",
        available: false,
        message: "Data unavailable — no data source connected.",
      },
      technology_risk: {
        category: "technology_risk",
        available: false,
        message: "Data unavailable — no data source connected.",
      },
      currency_risk: {
        category: "currency_risk",
        available: false,
        message: "Data unavailable — no data source connected.",
      },
      customer_concentration_risk: {
        category: "customer_concentration_risk",
        available: false,
        message: "Data unavailable — no data source connected.",
      },
      overall_risk_level: "moderate",
      categories_available: 2,
      categories_total: 6,
      limitations: [
        "Structural aggregation of existing financial_strength / economic_moat ratings only — no new risk-scoring algorithm.",
      ],
    },
  },
};

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("EPIC-F005 company analysis lib", () => {
  it("registers workspace sections", () => {
    expect(ANALYSIS_SECTIONS.map((s) => s.id)).toEqual(
      expect.arrayContaining([
        "summary",
        "valuation",
        "quality",
        "management",
        "moat",
        "risk",
        "financial",
        "ai",
        "explainability",
        "evidence",
        "timeline",
        "export",
        "ratings",
        "valuationTransparency",
        "research",
        "buffett",
        "compliance",
        "ownership",
        "peers",
        "documents",
        "news",
        "copilot",
        "settings",
      ]),
    );
  });

  it("exports mapped research view without inventing scores", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(sampleResponse, request, "2026-07-28T12:00:00.000Z");
    const json = researchViewToJson(view);
    expect(json).toContain("AAPL");
    expect(json).toContain("no client-side scoring");
    const csv = researchViewToCsv(view);
    expect(csv).toContain("intrinsicValue");
    expect(view.moat.label).toBe("Wide");
    expect(view.committeeDecision.toLowerCase()).toContain("hold");
    expect(view.buffett.kind).toBe("buffett_indicator_report");
    expect(view.buffett.recommendation.action).toBeTruthy();
    expect(json).toContain("buffettIndicator");
    expect(json).toContain("institutionalRatings");
    expect(json).toContain("reportInformation");
    expect(csv).toContain("buffettOverallRating");
    expect(csv).toContain("overallInvestmentGrade");
    expect(csv).toContain("reportId");
    expect(view.ratings.kind).toBe("institutional_rating_framework");
    expect(view.transparency.kind).toBe("report_transparency");
    expect(view.risk?.overall_risk_level).toBe("moderate");
    expect(view.risk?.business_risk.level).toBe("moderate");
    expect(view.risk?.regulatory_risk.available).toBe(false);
  });

  it("maps a missing risk payload to null without inventing values", () => {
    const request = buildDemoAnalyseRequest("AAPL");
    const responseWithoutRisk: AnalyseResponse = {
      ...sampleResponse,
      payload: { ...sampleResponse.payload, risk: undefined },
    };
    const view = mapResearchView(responseWithoutRisk, request, null);
    expect(view.risk).toBeNull();
  });

  it("persists workspace panel prefs", () => {
    useWorkspacePrefsStore.setState({
      activeSection: "summary",
      leftOpen: true,
      rightOpen: true,
      notes: [],
      tags: [],
    });
    useWorkspacePrefsStore.getState().setActiveSection("valuation");
    useWorkspacePrefsStore.getState().toggleLeft();
    expect(useWorkspacePrefsStore.getState().activeSection).toBe("valuation");
    expect(useWorkspacePrefsStore.getState().leftOpen).toBe(false);
  });
});

describe("EPIC-F005 workspace UI", () => {
  beforeEach(() => {
    cleanup();
    navigationState.search = "symbol=AAPL";
    acknowledgeResearchDisclaimer();
    analyseMock.mockReset();
    marketQuoteMock.mockReset();
    financialStatementsMock.mockReset();
    corporateActionsMock.mockReset();
    copilotCompleteMock.mockReset();
    compareMock.mockReset();
    selectIndianListingMock.mockReset();
    analyseMock.mockResolvedValue(sampleResponse);
    marketQuoteMock.mockResolvedValue({
      ok: true,
      available: true,
      authenticated: true,
      fields: { current_price: 190.5 },
    });
    // P0-01 — production analyse requires authenticated statements (not ACM clone).
    financialStatementsMock.mockResolvedValue({
      ok: true,
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
    });
    corporateActionsMock.mockResolvedValue({ ok: true, available: false });
    selectIndianListingMock.mockResolvedValue({
      ok: true,
      available: false,
      status: "NOT_FOUND",
      exchange: null,
    });
    useWorkspacePrefsStore.setState({
      activeSection: "summary",
      leftOpen: true,
      rightOpen: true,
      notes: [],
      tags: [],
    });
  });

  it("renders workspace layout and loads analyse API", async () => {
    const { CompanyAnalysisWorkspace } = await import(
      "@/components/company-analysis/CompanyAnalysisWorkspace"
    );
    wrap(<CompanyAnalysisWorkspace />);
    expect(screen.getByLabelText("Company navigation")).toBeTruthy();
    expect(screen.getByLabelText("Main analysis area")).toBeTruthy();
    expect(screen.getByLabelText("Context panel")).toBeTruthy();
    await waitFor(() => {
      expect(financialStatementsMock).toHaveBeenCalled();
      expect(analyseMock).toHaveBeenCalled();
    });
    const body = analyseMock.mock.calls[0]?.[0] as {
      ticker: string;
      financial_statements: { income_statement?: { revenue?: number } };
      valuation_signals?: unknown;
      current_market_price?: number;
    };
    expect(body.ticker).toBe("AAPL");
    expect(body.financial_statements.income_statement?.revenue).toBe(391_035);
    expect(body.financial_statements.income_statement?.revenue).not.toBe(1000);
    expect(body.valuation_signals).toBeUndefined();
    expect(body.current_market_price).toBe(190.5);
    expect(marketQuoteMock).toHaveBeenCalled();
    expect(
      await screen.findByRole("heading", { name: /Executive Summary/i }),
    ).toBeTruthy();
  });

  it("propagates selected BSE onto TCS statements, quote, and analyse", async () => {
    navigationState.search = "symbol=TCS";
    selectIndianListingMock.mockResolvedValue({
      ok: true,
      status: "SELECTED",
      symbol: "TCS",
      exchange: "BSE",
      isin: "INE467B01029",
    });
    const { CompanyAnalysisWorkspace } = await import(
      "@/components/company-analysis/CompanyAnalysisWorkspace"
    );
    wrap(<CompanyAnalysisWorkspace />);
    await waitFor(() => {
      expect(selectIndianListingMock).toHaveBeenCalled();
      expect(financialStatementsMock).toHaveBeenCalled();
      expect(analyseMock).toHaveBeenCalled();
    });
    const statementOpts = financialStatementsMock.mock.calls.map(
      (call) => call[1] as { exchange?: string; limit?: number },
    );
    expect(statementOpts.length).toBeGreaterThan(0);
    expect(statementOpts.every((opts) => opts.exchange === "BSE")).toBe(true);
    const quoteOpts = marketQuoteMock.mock.calls.map(
      (call) => call[1] as { exchange?: string },
    );
    expect(quoteOpts.length).toBeGreaterThan(0);
    expect(quoteOpts.every((opts) => opts.exchange === "BSE")).toBe(true);
    const body = analyseMock.mock.calls[0]?.[0] as { exchange?: string | null };
    expect(body.exchange).toBe("BSE");
  });

  it("does not invent exchange when the ticker is not in the catalogue", async () => {
    navigationState.search = "symbol=ZZZZNOTINCAT";
    const { CompanyAnalysisWorkspace } = await import(
      "@/components/company-analysis/CompanyAnalysisWorkspace"
    );
    wrap(<CompanyAnalysisWorkspace />);
    await waitFor(() => {
      expect(financialStatementsMock).toHaveBeenCalled();
      expect(analyseMock).toHaveBeenCalled();
    });
    const statementOpts = financialStatementsMock.mock.calls.map(
      (call) => call[1] as { exchange?: string },
    );
    expect(
      statementOpts.every(
        (opts) => opts.exchange == null || opts.exchange === "",
      ),
    ).toBe(true);
    const quoteOpts = marketQuoteMock.mock.calls.map(
      (call) => call[1] as { exchange?: string },
    );
    expect(
      quoteOpts.every((opts) => opts.exchange == null || opts.exchange === ""),
    ).toBe(true);
    const body = analyseMock.mock.calls[0]?.[0] as { exchange?: string | null };
    expect(body.exchange == null || body.exchange === "").toBe(true);
  });

  it("does not call analyse when authenticated statements are unavailable", async () => {
    financialStatementsMock.mockResolvedValue({
      ok: true,
      available: false,
      authenticated: false,
      periods: null,
      message: "Data unavailable.",
    });
    const { CompanyAnalysisWorkspace } = await import(
      "@/components/company-analysis/CompanyAnalysisWorkspace"
    );
    wrap(<CompanyAnalysisWorkspace />);
    await waitFor(() => {
      expect(financialStatementsMock).toHaveBeenCalled();
    });
    expect(analyseMock).not.toHaveBeenCalled();
  });

  it("blocks analyse until research disclaimer is acknowledged", async () => {
    const { clearResearchDisclaimerAcknowledgement } = await import(
      "@/lib/legal"
    );
    clearResearchDisclaimerAcknowledgement();
    const { CompanyAnalysisWorkspace } = await import(
      "@/components/company-analysis/CompanyAnalysisWorkspace"
    );
    wrap(<CompanyAnalysisWorkspace />);
    expect(
      await screen.findByRole("heading", {
        name: /Investment research disclaimer/i,
      }),
    ).toBeTruthy();
    expect(analyseMock).not.toHaveBeenCalled();
  });

  it("shows valuation fields from mapped backend outputs", async () => {
    const { ValuationSection } = await import(
      "@/components/company-analysis/WorkspaceSections"
    );
    const request = buildDemoAnalyseRequest("AAPL");
    const view = mapResearchView(sampleResponse, request, null);
    wrap(<ValuationSection view={view} />);
    expect(screen.getByText("Intrinsic Value")).toBeTruthy();
    expect(screen.getByText("Margin of Safety")).toBeTruthy();
  });

  it("renders the real Risk stage — available and honestly-unavailable categories", async () => {
    const { RiskSection } = await import(
      "@/components/company-analysis/FlagshipSections"
    );
    const request = buildDemoAnalyseRequest("AAPL");
    const view = mapResearchView(sampleResponse, request, null);
    wrap(<RiskSection view={view} />);
    expect(screen.getByText("Moderate (from economic_moat)")).toBeTruthy();
    expect(screen.getByText("Low (from financial_strength)")).toBeTruthy();
    expect(
      screen.getAllByText("Data unavailable — no data source connected.")
        .length,
    ).toBeGreaterThanOrEqual(4);
  });

  it("does not fire a new lazy section's queries until it becomes active", async () => {
    const { CompanyAnalysisWorkspace } = await import(
      "@/components/company-analysis/CompanyAnalysisWorkspace"
    );
    wrap(<CompanyAnalysisWorkspace />);
    await waitFor(() => expect(analyseMock).toHaveBeenCalled());
    await screen.findByRole("heading", { name: /Executive Summary/i });

    // Documents is a lazy, net-new section — its component (and therefore its
    // corporateActions query) must not mount while Overview is active.
    expect(corporateActionsMock).not.toHaveBeenCalled();

    const sectionsNav = await screen.findByRole("navigation", {
      name: "Analysis sections",
    });
    const documentsNavButton = within(sectionsNav).getByRole("button", {
      name: /Documents/i,
    });
    documentsNavButton.click();

    await waitFor(() => expect(corporateActionsMock).toHaveBeenCalled());
  });
});

describe("EPIC-F005 foundation version", () => {
  it("is foundation 2.0.0-rc.1", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc.1");
  });
});
