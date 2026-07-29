/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const push = vi.fn();
const replace = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/analysis",
  useRouter: () => ({ push, replace }),
  useSearchParams: () => new URLSearchParams("symbol=AAPL"),
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

vi.mock("@/lib/api/client", () => ({
  api: {
    analyse: (...args: unknown[]) => analyseMock(...args),
    marketQuote: (...args: unknown[]) => marketQuoteMock(...args),
  },
}));

import {
  ANALYSIS_SECTIONS,
  researchViewToCsv,
  researchViewToJson,
  useWorkspacePrefsStore,
} from "@/lib/company-analysis";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { buildAnalyseRequestForTicker } from "@/lib/research/buildAnalyseRequest";
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
        "ratings",
        "valuationTransparency",
        "research",
        "valuation",
        "quality",
        "ai",
        "buffett",
        "compliance",
        "timeline",
        "export",
      ]),
    );
  });

  it("exports mapped research view without inventing scores", () => {
    const request = buildAnalyseRequestForTicker("AAPL", {
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
    acknowledgeResearchDisclaimer();
    analyseMock.mockReset();
    marketQuoteMock.mockReset();
    analyseMock.mockResolvedValue(sampleResponse);
    marketQuoteMock.mockResolvedValue({ ok: true });
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
      expect(analyseMock).toHaveBeenCalled();
    });
    expect(await screen.findByText(/Executive Summary/i)).toBeTruthy();
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
    const request = buildAnalyseRequestForTicker("AAPL");
    const view = mapResearchView(sampleResponse, request, null);
    wrap(<ValuationSection view={view} />);
    expect(screen.getByText("Intrinsic value")).toBeTruthy();
    expect(screen.getByText("Margin of safety")).toBeTruthy();
  });
});

describe("EPIC-F005 foundation version", () => {
  it("is foundation 2.0.0-rc", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc");
  });
});
