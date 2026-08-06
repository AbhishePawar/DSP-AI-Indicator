/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const push = vi.fn();
const replace = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/research/institutional",
  useRouter: () => ({ push, replace }),
  useSearchParams: () => new URLSearchParams("symbol=AAPL&section=cover"),
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
  REPORT_SECTIONS,
  asReportMode,
  asReportSectionId,
  useInstitutionalReportsPrefsStore,
} from "@/lib/institutional-reports";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { buildAnalyseRequestForTicker } from "@/lib/research/buildAnalyseRequest";
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
  correlation_id: "corr-report-1",
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

describe("P9.6 / EPIC-007 institutional reports lib", () => {
  it("registers all publishing modules", () => {
    expect(REPORT_SECTIONS.map((s) => s.id)).toEqual([
      "cover",
      "summary",
      "valuation",
      "quality",
      "management",
      "moat",
      "risk",
      "ai",
      "explainability",
      "evidence",
      "timeline",
      "export",
      "audit",
    ]);
    expect(asReportSectionId("unknown")).toBe("cover");
    expect(asReportMode("pdf")).toBe("pdf");
    expect(asReportMode("bogus")).toBe("interactive");
  });

  it("persists report prefs including mode", () => {
    useInstitutionalReportsPrefsStore.setState({
      activeSection: "cover",
      leftOpen: true,
      rightOpen: true,
      reportMode: "interactive",
      selectedTicker: "AAPL",
      favourites: [],
      notes: [],
      tags: [],
    });
    useInstitutionalReportsPrefsStore.getState().setActiveSection("audit");
    useInstitutionalReportsPrefsStore.getState().setReportMode("print");
    useInstitutionalReportsPrefsStore.getState().toggleFavourite("MSFT");
    expect(useInstitutionalReportsPrefsStore.getState().activeSection).toBe(
      "audit",
    );
    expect(useInstitutionalReportsPrefsStore.getState().reportMode).toBe(
      "print",
    );
    expect(useInstitutionalReportsPrefsStore.getState().favourites).toContain(
      "MSFT",
    );
  });
});

describe("P9.6 / EPIC-007 report modules", () => {
  beforeEach(() => {
    cleanup();
    acknowledgeResearchDisclaimer();
    analyseMock.mockReset();
    marketQuoteMock.mockReset();
    analyseMock.mockResolvedValue(sampleResponse);
    marketQuoteMock.mockResolvedValue({ ok: true });
    useInstitutionalReportsPrefsStore.setState({
      activeSection: "cover",
      leftOpen: true,
      rightOpen: true,
      reportMode: "interactive",
      selectedTicker: "AAPL",
      favourites: [],
      notes: [],
      tags: [],
    });
  });

  it("renders workspace and loads analyse API only", async () => {
    const { InstitutionalReportsWorkspace } = await import(
      "@/components/institutional-reports/InstitutionalReportsWorkspace"
    );
    wrap(<InstitutionalReportsWorkspace />);
    expect(screen.getByLabelText("Report navigation")).toBeTruthy();
    expect(screen.getByLabelText("Institutional research report")).toBeTruthy();
    expect(screen.getByLabelText("Report context panel")).toBeTruthy();
    await waitFor(() => {
      expect(analyseMock).toHaveBeenCalled();
    });
    expect(
      await screen.findByRole("heading", {
        name: /Institutional Research Report/i,
      }),
    ).toBeTruthy();
    expect(screen.getByText("Prepared By")).toBeTruthy();
    expect(screen.getByText("Ada Analyst")).toBeTruthy();
  });

  it("shows Book 04 labels without inventing sub-scores", async () => {
    const { BusinessQualityModule } = await import(
      "@/components/institutional-reports/ReportModules"
    );
    const request = buildAnalyseRequestForTicker("AAPL");
    const view = mapResearchView(sampleResponse, request, null);
    wrap(<BusinessQualityModule view={view} />);
    expect(screen.getAllByText("Capital Allocation").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Industry Structure").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Operating Discipline").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Franchise Durability").length).toBeGreaterThan(0);
    // Honest empty — metrics not on stage summaries
    expect(screen.getAllByText("Data unavailable.").length).toBeGreaterThan(0);
  });

  it("shows Book 07 risk labels without aliasing stage decisions", async () => {
    const { RiskModule } = await import(
      "@/components/institutional-reports/ReportModules"
    );
    const request = buildAnalyseRequestForTicker("AAPL");
    const view = mapResearchView(sampleResponse, request, null);
    wrap(<RiskModule view={view} />);
    expect(screen.getByText("Business Risk")).toBeTruthy();
    expect(screen.getByText("Governance Risk")).toBeTruthy();
    expect(screen.getByText("Permanent Capital Loss")).toBeTruthy();
    // Financial strength "Solid" must not appear as Business Risk
    const rows = screen.getAllByText("Data unavailable.");
    expect(rows.length).toBeGreaterThan(0);
  });

  it("renders AI committee and valuation from mapped outputs", async () => {
    const { AiCommitteeModule, ValuationModule } = await import(
      "@/components/institutional-reports/ReportModules"
    );
    const request = buildAnalyseRequestForTicker("AAPL");
    const view = mapResearchView(sampleResponse, request, null);
    wrap(<ValuationModule view={view} />);
    expect(screen.getByText("Intrinsic Value")).toBeTruthy();
    expect(screen.getAllByText("DCF").length).toBeGreaterThan(0);
    expect(screen.getAllByText("EPV").length).toBeGreaterThan(0);
    cleanup();
    wrap(<AiCommitteeModule view={view} />);
    expect(screen.getByText("Decision")).toBeTruthy();
    expect(screen.getByText("Contradictory evidence")).toBeTruthy();
  });

  it("renders explainability trust ladder and audit metadata", async () => {
    const { ExplainabilityModule, AuditModule, CoverSection } = await import(
      "@/components/institutional-reports/Sections"
    );
    const request = buildAnalyseRequestForTicker("AAPL");
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-08-01T12:00:00.000Z",
    );
    wrap(
      <CoverSection
        view={view}
        preparedBy="Ada Analyst"
        marketStatus="Quote loaded"
      />,
    );
    expect(screen.getByText("Research Date")).toBeTruthy();
    cleanup();
    wrap(<ExplainabilityModule view={view} />);
    expect(screen.getByText("Trust Ladder")).toBeTruthy();
    expect(screen.getByText("Evidence chain")).toBeTruthy();
    cleanup();
    wrap(<AuditModule view={view} marketStatus="Quote loaded" />);
    expect(screen.getByText("Audit Metadata")).toBeTruthy();
    expect(screen.getByText("Data freshness")).toBeTruthy();
  });
});
