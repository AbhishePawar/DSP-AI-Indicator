/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: () => "/research",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
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
    user: null,
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
  loadResearchSession: vi.fn(() => null),
  clearResearchSession: vi.fn(),
}));

vi.mock("@/lib/copilot/sessionArchive", () => ({
  listArchivedSessions: vi.fn(() => []),
  loadArchivedSession: vi.fn(() => null),
  archiveResearchSession: vi.fn(),
}));

vi.mock("@/lib/analysis/recentAnalyses", () => ({
  loadRecentAnalyses: vi.fn(() => [
    {
      ticker: "AAPL",
      company: "Apple",
      exchange: "NASDAQ",
      recommendation: "Unavailable",
      analysedAt: "2026-07-28T12:00:00.000Z",
    },
  ]),
  pushRecentAnalysis: vi.fn(),
}));

vi.mock("@/lib/recentReports", () => ({
  listRecentReports: vi.fn(() => []),
}));

const analyseMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    analyse: (...args: unknown[]) => analyseMock(...args),
  },
}));

import {
  RESEARCH_SECTIONS,
  libraryFromRecent,
  mergeLibraryItems,
  useResearchWorkspacePrefsStore,
} from "@/lib/research-workspace";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";
import { acknowledgeResearchDisclaimer } from "@/lib/legal";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";

const sampleResponse: AnalyseResponse = {
  ok: true,
  capability: "analyse",
  limitations: ["Demo limitation"],
  errors: [],
  api_version: "v1",
  platform_version: "1.0.0",
  pipeline_version: "1.0.0",
  correlation_id: "corr-rw",
  payload: {
    ok: true,
    metadata: {
      pipeline_version: "1.0.0",
      platform_version: "1.0.0",
      execution_order: ["valuation", "investment_committee"],
      confidence_summary: { valuation: 0.7 },
      warnings: [],
      total_elapsed_ms: 90,
    },
    stage_summaries: [
      {
        stage: "valuation",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "DCF",
        decision: "hold",
        confidence: 0.7,
      },
      {
        stage: "investment_committee",
        status: "succeeded",
        has_result: true,
        score: 65,
        label: "Hold",
        decision: "hold",
        confidence: 0.65,
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
        decision: "ok",
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
        confidence: 0.68,
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
        stage: "financial",
        status: "succeeded",
        has_result: true,
        score: 71,
        label: "Healthy",
        decision: "ok",
        confidence: 0.7,
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
    ],
    recommendation_summary: {
      decision: "hold",
      confidence: 0.6,
      margin_of_safety: 0.1,
      label: "Hold",
    },
    committee_summary: {
      decision: "hold",
      confidence: 0.65,
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

describe("EPIC-F007 research workspace lib", () => {
  it("registers sections", () => {
    expect(RESEARCH_SECTIONS.map((s) => s.id)).toEqual(
      expect.arrayContaining([
        "library",
        "viewer",
        "ratings",
        "valuationTransparency",
        "archive",
        "diff",
        "ai",
        "buffett",
        "compliance",
        "export",
      ]),
    );
  });

  it("builds library rows from local recent analyses", () => {
    const items = mergeLibraryItems(
      libraryFromRecent([
        {
          ticker: "AAPL",
          company: "Apple",
          exchange: "NASDAQ",
          recommendation: "Unavailable",
          analysedAt: "2026-07-28T12:00:00.000Z",
        },
      ]),
    );
    expect(items[0]?.ticker).toBe("AAPL");
    expect(items[0]?.source).toBe("recent");
  });

  it("persists favourites and pins", () => {
    useResearchWorkspacePrefsStore.setState({
      activeSection: "library",
      leftOpen: true,
      rightOpen: true,
      selectedTicker: null,
      favourites: [],
      pinnedTickers: [],
      notes: [],
      tags: [],
    });
    useResearchWorkspacePrefsStore.getState().toggleFavourite("aapl", "Apple");
    expect(useResearchWorkspacePrefsStore.getState().isFavourite("AAPL")).toBe(
      true,
    );
    useResearchWorkspacePrefsStore.getState().togglePinned("aapl");
    expect(useResearchWorkspacePrefsStore.getState().isPinned("AAPL")).toBe(
      true,
    );
  });
});

describe("EPIC-F007 workspace UI", () => {
  beforeEach(() => {
    cleanup();
    acknowledgeResearchDisclaimer();
    analyseMock.mockReset();
    analyseMock.mockResolvedValue(sampleResponse);
    useResearchWorkspacePrefsStore.setState({
      activeSection: "library",
      leftOpen: true,
      rightOpen: true,
      selectedTicker: null,
      favourites: [],
      pinnedTickers: [],
      notes: [],
      tags: [],
    });
  });

  it("renders workspace layout and library", async () => {
    const { ResearchWorkspace } = await import(
      "@/components/research-workspace/ResearchWorkspace"
    );
    wrap(<ResearchWorkspace />);
    expect(screen.getByLabelText("Research navigation")).toBeTruthy();
    expect(screen.getByLabelText("Main research view")).toBeTruthy();
    expect(screen.getByLabelText("Research context panel")).toBeTruthy();
    expect(screen.getByText("Research Library")).toBeTruthy();
    expect((await screen.findAllByText("AAPL")).length).toBeGreaterThan(0);
  });

  it("shows honest empty diff state", async () => {
    useResearchWorkspacePrefsStore.setState({ activeSection: "diff" });
    const { DiffSection } = await import(
      "@/components/research-workspace/Sections"
    );
    wrap(<DiffSection />);
    expect(screen.getByText("Research Diff Viewer")).toBeTruthy();
    expect(
      screen.getAllByText(/Data unavailable/i).length,
    ).toBeGreaterThan(0);
  });

  it("loads analyse API into viewer when opening ticker", async () => {
    const { ResearchWorkspace } = await import(
      "@/components/research-workspace/ResearchWorkspace"
    );
    wrap(<ResearchWorkspace />);
    const openButtons = await screen.findAllByRole("button", { name: "Open" });
    openButtons[0]?.click();
    await waitFor(() => {
      expect(analyseMock).toHaveBeenCalled();
    });
  });
});

describe("EPIC-F007 foundation version", () => {
  it("is foundation 2.0.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
  });
});
