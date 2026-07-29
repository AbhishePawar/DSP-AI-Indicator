/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/portfolio",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams("section=summary"),
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
  portfolioSnapshotToCsv,
  portfolioSnapshotToJson,
  usePortfolioIntelPrefsStore,
} from "@/lib/portfolio-intelligence";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";

describe("EPIC-F006 portfolio intelligence lib", () => {
  it("registers sections", () => {
    expect(PORTFOLIO_SECTIONS.map((s) => s.id)).toEqual(
      expect.arrayContaining([
        "summary",
        "holdings",
        "research",
        "ai",
        "monitoring",
        "compliance",
        "export",
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

describe("EPIC-F006 workspace UI", () => {
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

  it("renders workspace layout and summary counts", async () => {
    const { PortfolioIntelligenceWorkspace } = await import(
      "@/components/portfolio-intelligence/PortfolioIntelligenceWorkspace"
    );
    render(<PortfolioIntelligenceWorkspace />);
    expect(screen.getByLabelText("Portfolio navigation")).toBeTruthy();
    expect(screen.getByLabelText("Main portfolio view")).toBeTruthy();
    expect(screen.getByLabelText("Portfolio context panel")).toBeTruthy();
    expect(screen.getByText("Portfolio Overview")).toBeTruthy();
    expect(screen.getByText("Holdings count")).toBeTruthy();
  });

  it("renders holdings table with company links", async () => {
    usePortfolioIntelPrefsStore.setState({ activeSection: "holdings" });
    const { HoldingsSection } = await import(
      "@/components/portfolio-intelligence/Sections"
    );
    render(
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

describe("EPIC-F006 foundation version", () => {
  it("is foundation 2.0.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
  });
});
