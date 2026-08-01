/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: () => "/portfolio",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams("section=summary"),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    session: {
      accessToken: "test-token",
      username: "analyst",
      displayName: "Analyst",
      email: "a@example.com",
    },
  }),
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    portfolioIntelligence: vi.fn().mockResolvedValue({
      ok: true,
      result: {
        result_id: "pi-1",
        schema_version: "1",
        portfolio_summary: {
          holding_count: 2,
          linked_research_count: 0,
          missing_research_count: 2,
          weights_provided_count: 2,
        },
        diversification_summary: {
          unique_sector_count: 1,
          sectors: ["Technology"],
          note: "Counts only",
        },
        sector_allocation: { by_sector: [], note: "No weights" },
        position_concentration: { top_holdings_by_weight: [], note: "n/a" },
        portfolio_risk_summary: {
          positions: [],
          available_count: 0,
          unavailable_count: 0,
          note: "n/a",
        },
        margin_of_safety_summary: {
          positions: [],
          available_count: 0,
          unavailable_count: 0,
          note: "n/a",
        },
        quality_summary: {
          positions: [],
          available_count: 0,
          unavailable_count: 0,
          note: "n/a",
        },
        watchlist_summary: { symbol_count: 0 },
        missing_research: [],
      },
    }),
  },
}));

vi.mock("@/lib/portfolio/PortfolioProvider", () => ({
  usePortfolio: () => ({
    holdings: [
      {
        company: "Apple",
        ticker: "AAPL",
        sector: "Technology",
        allocationPercent: 50,
        recommendation: "Data unavailable.",
        researchAvailable: true,
      },
      {
        company: "Microsoft",
        ticker: "MSFT",
        sector: "Technology",
        allocationPercent: 50,
        recommendation: "Data unavailable.",
        researchAvailable: false,
      },
    ],
    view: {
      summary: {
        totalHoldings: 2,
        sectorCount: 1,
        researchCoverage: "1/2",
        portfolioStatus: "Active",
        portfolioValue: "Data unavailable.",
        cashAllocation: "Data unavailable.",
        averageQualityScore: "Unavailable",
        averageRecommendation: "Unavailable",
      },
      holdings: [],
      allocations: { bySector: [], byMarketCap: [], byGeography: [] },
      activities: [
        {
          id: "a1",
          label: "Added AAPL",
          timestamp: "2026-07-28T10:00:00.000Z",
        },
      ],
    },
    isEmpty: false,
    hasTicker: () => true,
    addHolding: vi.fn(),
    removeHolding: vi.fn(),
    recordResearchOpened: vi.fn(),
    loadDemo: vi.fn(),
    clearPortfolio: vi.fn(),
  }),
}));

vi.mock("@/components/portfolio/RemoveHoldingButton", () => ({
  RemoveHoldingButton: ({ ticker }: { ticker: string }) => (
    <button type="button">Remove {ticker}</button>
  ),
}));

vi.mock("@/components/portfolio/PortfolioActions", () => ({
  PortfolioActions: () => <div>Portfolio actions</div>,
}));

vi.mock("@/components/persistence/PortfolioSync", () => ({
  PortfolioSync: () => <div>Sync</div>,
}));

import {
  PORTFOLIO_SECTIONS,
  buildPortfolioExportSnapshot,
  mapPortfolioIntelligenceResult,
  portfolioSnapshotToCsv,
  portfolioSnapshotToJson,
  sectorHoldingCounts,
  usePortfolioIntelPrefsStore,
} from "@/lib/portfolio-intelligence";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("P9.5 portfolio intelligence lib", () => {
  it("registers institutional sections", () => {
    expect(PORTFOLIO_SECTIONS.map((s) => s.id)).toEqual(
      expect.arrayContaining([
        "summary",
        "allocation",
        "performance",
        "quality",
        "valuation",
        "risk",
        "research",
        "watchlist",
        "opportunities",
        "rebalancing",
        "explainability",
        "export",
        "holdings",
        "compliance",
      ]),
    );
  });

  it("exports holdings without inventing portfolio value", () => {
    const snapshot = buildPortfolioExportSnapshot({
      portfolioId: "primary",
      portfolioName: "Primary",
      holdings: [
        {
          company: "Apple",
          ticker: "AAPL",
          sector: "Technology",
          allocationPercent: 100,
          recommendation: "Data unavailable.",
          researchAvailable: true,
        },
      ],
      watchlist: ["MSFT"],
      activities: [],
    });
    const json = portfolioSnapshotToJson(snapshot);
    expect(json).toContain("AAPL");
    expect(json).not.toContain("portfolioValue");
    expect(json).toMatch(/not computed/i);
    expect(portfolioSnapshotToCsv(snapshot)).toContain("ticker");
  });

  it("maps intelligence API without inventing MoS", () => {
    const view = mapPortfolioIntelligenceResult({
      ok: true,
      result: {
        result_id: "pi-1",
        schema_version: "1.0",
        portfolio_summary: { holding_count: 1, linked_research_count: 0 },
        diversification_summary: { unique_sector_count: 0, sectors: [] },
        sector_allocation: { by_sector: [], note: "n/a" },
        position_concentration: { top_holdings_by_weight: [] },
        portfolio_risk_summary: { positions: [], available_count: 0 },
        margin_of_safety_summary: {
          positions: [{ symbol: "AAPL", margin_of_safety: "Data unavailable." }],
          available_count: 0,
          note: "Pass-through only",
        },
        quality_summary: { positions: [], available_count: 0 },
        watchlist_summary: { symbol_count: 0 },
        missing_research: [],
      },
    });
    expect(view?.mosPositions[0]?.marginOfSafety).toMatch(/unavailable/i);
    expect(view?.holdingCount).toBe("1");
  });

  it("builds sector holding counts from session labels", () => {
    const segments = sectorHoldingCounts([
      {
        company: "A",
        ticker: "A",
        sector: "Technology",
        allocationPercent: 50,
        recommendation: "Data unavailable.",
        researchAvailable: true,
      },
      {
        company: "B",
        ticker: "B",
        sector: "Technology",
        allocationPercent: 50,
        recommendation: "Data unavailable.",
        researchAvailable: false,
      },
    ]);
    expect(segments[0]?.name).toBe("Technology");
    expect(segments[0]?.count).toBe(2);
  });

  it("persists prefs and watchlist", () => {
    usePortfolioIntelPrefsStore.setState({
      activeSection: "summary",
      leftOpen: true,
      rightOpen: true,
      activePortfolioId: "primary",
      portfolios: [
        {
          id: "primary",
          name: "Primary session portfolio",
          favourite: true,
          lastOpenedAt: new Date(0).toISOString(),
        },
      ],
      watchlist: [],
      notes: [],
      tags: [],
    });
    usePortfolioIntelPrefsStore.getState().addWatchlistSymbol("nvda");
    expect(usePortfolioIntelPrefsStore.getState().watchlist[0]?.symbol).toBe(
      "NVDA",
    );
    usePortfolioIntelPrefsStore.getState().setActiveSection("holdings");
    expect(usePortfolioIntelPrefsStore.getState().activeSection).toBe(
      "holdings",
    );
  });
});

describe("P9.5 workspace UI", () => {
  beforeEach(() => {
    cleanup();
    usePortfolioIntelPrefsStore.setState({
      activeSection: "summary",
      leftOpen: true,
      rightOpen: true,
      activePortfolioId: "primary",
      portfolios: [
        {
          id: "primary",
          name: "Primary session portfolio",
          favourite: true,
          lastOpenedAt: new Date(0).toISOString(),
        },
      ],
      watchlist: [],
      notes: [],
      tags: [],
    });
  });

  it("renders workspace layout and executive summary", async () => {
    const { PortfolioIntelligenceWorkspace } = await import(
      "@/components/portfolio-intelligence/PortfolioIntelligenceWorkspace"
    );
    wrap(<PortfolioIntelligenceWorkspace />);
    expect(screen.getByLabelText("Portfolio navigation")).toBeTruthy();
    expect(screen.getByLabelText("Main portfolio view")).toBeTruthy();
    expect(screen.getByLabelText("Portfolio context panel")).toBeTruthy();
    expect(
      await screen.findByRole("heading", { name: /Executive Portfolio Summary/i }),
    ).toBeTruthy();
    expect(screen.getByText("Holdings count")).toBeTruthy();
  });

  it("renders holdings table with company links", async () => {
    usePortfolioIntelPrefsStore.setState({ activeSection: "holdings" });
    const { HoldingsSection } = await import(
      "@/components/portfolio-intelligence/Sections"
    );
    wrap(
      <HoldingsSection
        holdings={[
          {
            company: "Apple",
            ticker: "AAPL",
            sector: "Technology",
            allocationPercent: 50,
            recommendation: "Data unavailable.",
            researchAvailable: true,
          },
        ]}
      />,
    );
    expect(screen.getByLabelText("Portfolio holdings")).toBeTruthy();
    expect(screen.getByText("AAPL")).toBeTruthy();
    expect(screen.getByText("Quick analysis")).toBeTruthy();
  });
});

describe("P9.5 foundation version", () => {
  it("is foundation 2.0.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
  });
});
