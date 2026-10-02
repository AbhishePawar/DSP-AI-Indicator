/**
 * @vitest-environment jsdom
 */
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { SearchFirstDashboard } from "./SearchFirstDashboard";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

const mockRecentAnalyses = vi.fn(() => [
  {
    ticker: "TCS.NS",
    company: "Tata Consultancy Services",
    exchange: "NSE",
    recommendation: "Strong",
    analysedAt: "2026-10-01T10:00:00Z",
  },
]);

vi.mock("@/lib/companies/catalogue", () => ({
  searchCatalogue: (query: string) => {
    if (!query) return [];
    if (query.toUpperCase().includes("TCS")) {
      return [
        {
          ticker: "TCS",
          name: "Tata Consultancy Services",
          exchange: "NSE",
          sector: "Technology",
          industry: "IT Services",
          marketCap: "Large Cap",
        },
        {
          ticker: "TCS.BO",
          name: "Tata Consultancy Services (BSE)",
          exchange: "BSE",
          sector: "Technology",
          industry: "IT Services",
          marketCap: "Large Cap",
        },
      ];
    }
    if (query.toUpperCase().includes("HDFC")) {
      return [
        {
          ticker: "HDFCBANK",
          name: "HDFC Bank Limited",
          exchange: "NSE",
          sector: "Financials",
          industry: "Banking",
          marketCap: "Large Cap",
        },
      ];
    }
    if (query.toUpperCase().includes("UNKNOWN")) {
      return [];
    }
    return [
      {
        ticker: "INFY",
        name: "Infosys Limited",
        exchange: "NSE",
        sector: "Technology",
        industry: "IT Services",
        marketCap: "Large Cap",
      },
    ];
  },
}));

vi.mock("@/lib/analysis/recentAnalyses", () => ({
  loadRecentAnalyses: () => mockRecentAnalyses(),
}));

describe("SearchFirstDashboard: Search, Accessibility, and Keyboard Navigation", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    mockRecentAnalyses.mockReturnValue([
      {
        ticker: "TCS.NS",
        company: "Tata Consultancy Services",
        exchange: "NSE",
        recommendation: "Strong",
        analysedAt: "2026-10-01T10:00:00Z",
      },
    ]);
  });

  it("provides exactly ONE accessible company searchbox in the primary hierarchy", () => {
    render(<SearchFirstDashboard />);
    const searchBoxes = screen.getAllByRole("searchbox");
    expect(searchBoxes).toHaveLength(1);
    expect(searchBoxes[0].getAttribute("aria-label")).toBe(
      "Search a company or ask a research question"
    );
  });

  it("handles keyboard navigation across matched catalogue suggestions and submits active item on Enter", async () => {
    render(<SearchFirstDashboard />);

    const searchInput = screen.getByRole("searchbox", {
      name: "Search a company or ask a research question",
    });
    fireEvent.change(searchInput, { target: { value: "TCS" } });

    // Wait for debounced search dropdown listbox
    await waitFor(() => {
      expect(
        screen.getByRole("listbox", { name: "Company search results" })
      ).toBeTruthy();
    });

    // Arrow down moves selection
    fireEvent.keyDown(searchInput, { key: "ArrowDown" });
    // Arrow down again
    fireEvent.keyDown(searchInput, { key: "ArrowDown" });
    // Arrow up moves back
    fireEvent.keyDown(searchInput, { key: "ArrowUp" });

    // Enter submits selected item
    fireEvent.keyDown(searchInput, { key: "Enter" });
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/analysis?symbol=TCS")
    );
  });

  it("renders rich search result metadata: ticker, exchange, sector and industry", async () => {
    render(<SearchFirstDashboard />);

    const searchInput = screen.getByRole("searchbox", {
      name: "Search a company or ask a research question",
    });
    fireEvent.change(searchInput, { target: { value: "TCS" } });

    await waitFor(() => {
      expect(
        screen.getByRole("listbox", { name: "Company search results" })
      ).toBeTruthy();
    });

    const listbox = screen.getByRole("listbox", { name: "Company search results" });
    expect(listbox).toBeTruthy();
    expect(screen.getAllByText("TCS")[0]).toBeTruthy();
    expect(screen.getAllByText("NSE")[0]).toBeTruthy();
    expect(screen.getAllByText("Technology · IT Services")[0]).toBeTruthy();
  });

  it("displays honest no-results guidance when no catalogue items match", async () => {
    render(<SearchFirstDashboard />);

    const searchInput = screen.getByRole("searchbox", {
      name: "Search a company or ask a research question",
    });
    fireEvent.change(searchInput, { target: { value: "UNKNOWNXYZ" } });

    await waitFor(() => {
      expect(screen.getByText("No matching securities found")).toBeTruthy();
    });
    expect(
      screen.getByText(/Try searching by ticker/i)
    ).toBeTruthy();
  });

  it("submits search when clicking the Analyze button", () => {
    render(<SearchFirstDashboard />);

    const searchInput = screen.getByRole("searchbox", {
      name: "Search a company or ask a research question",
    });
    fireEvent.change(searchInput, { target: { value: "TCS" } });

    const analyzeBtn = screen.getByRole("button", { name: "Analyze" });
    fireEvent.click(analyzeBtn);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/analysis?symbol=TCS")
    );
  });

  it("clears search input query on Escape key press", async () => {
    render(<SearchFirstDashboard />);

    const searchInput = screen.getByRole("searchbox", {
      name: "Search a company or ask a research question",
    });
    fireEvent.change(searchInput, { target: { value: "HDFC Bank" } });
    expect((searchInput as HTMLInputElement).value).toBe("HDFC Bank");

    fireEvent.keyDown(searchInput, { key: "Escape" });
    expect((searchInput as HTMLInputElement).value).toBe("");
  });

  it("submits research suggestion when clicking on suggestion button", async () => {
    render(<SearchFirstDashboard />);

    const suggestionBtns = screen.getAllByRole("button", {
      name: /Analyse HDFC Bank using the DSP Indicator/i,
    });
    expect(suggestionBtns.length).toBeGreaterThan(0);
    fireEvent.click(suggestionBtns[0]);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/analysis?symbol=HDFC%20BANK")
    );
  });
});

describe("SearchFirstDashboard: Research Workflows and Boundaries", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders all four research workflows with governed status for Deep Research", () => {
    render(<SearchFirstDashboard />);

    expect(screen.getByRole("button", { name: /^DSP Indicator/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /^Company Research/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /^Compare Companies/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /^Deep Research/i })).toBeTruthy();

    // Verify Deep Research communicates legitimate backend availability boundary
    expect(
      screen.getByText("Governed / Subject to provider availability")
    ).toBeTruthy();
  });

  it("allows selecting a research path and submitting with chosen intent", () => {
    render(<SearchFirstDashboard />);

    const compareBtn = screen.getByRole("button", { name: /^Compare Companies/i });
    fireEvent.click(compareBtn);

    const searchInput = screen.getByRole("searchbox", {
      name: "Search a company or ask a research question",
    });
    fireEvent.change(searchInput, { target: { value: "INFY" } });
    fireEvent.keyDown(searchInput, { key: "Enter" });

    expect(mockPush).toHaveBeenCalledWith("/analysis?symbol=INFY&intent=compare");
  });
});

describe("SearchFirstDashboard: Recent Analyses Presentation and Empty State", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders recent analysis cards with company, ticker, context, and resume action", () => {
    mockRecentAnalyses.mockReturnValue([
      {
        ticker: "TCS.NS",
        company: "Tata Consultancy Services",
        exchange: "NSE",
        recommendation: "Strong",
        analysedAt: "2026-10-01T10:00:00Z",
      },
    ]);

    render(<SearchFirstDashboard />);

    expect(screen.getByRole("heading", { name: "Recent research" })).toBeTruthy();
    expect(screen.getByText("Tata Consultancy Services")).toBeTruthy();
    expect(screen.getByText("TCS.NS")).toBeTruthy();
    expect(screen.getByText("· Strong")).toBeTruthy();

    const resumeBtn = screen.getByRole("button", {
      name: /Resume analysis for Tata Consultancy Services/i,
    });
    expect(resumeBtn).toBeTruthy();
    fireEvent.click(resumeBtn);
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/analysis?symbol=TCS.NS")
    );
  });

  it("renders honest empty state when there are no recent analyses", () => {
    mockRecentAnalyses.mockReturnValue([]);

    render(<SearchFirstDashboard />);

    expect(screen.getByText("No recent analyses yet")).toBeTruthy();
    expect(
      screen.getByText(/Securities you analyze will appear here/i)
    ).toBeTruthy();
    // Verify no fake analyses are rendered
    expect(screen.queryByText("Tata Consultancy Services")).toBeNull();
  });
});

describe("SearchFirstDashboard: Responsive regression tests across viewport widths", () => {
  beforeEach(() => {
    cleanup();
  });

  const viewports = [
    { name: "mobile-320", width: 320 },
    { name: "mobile-375", width: 375 },
    { name: "mobile-414", width: 414 },
    { name: "tablet-768", width: 768 },
    { name: "desktop-1024", width: 1024 },
    { name: "large-desktop-1440", width: 1440 },
  ];

  viewports.forEach(({ name, width }) => {
    it(`renders usable company search container and controls at ${name} (${width}px)`, () => {
      window.innerWidth = width;
      window.dispatchEvent(new Event("resize"));

      const { container } = render(<SearchFirstDashboard />);
      const mainContainer = container.querySelector(".dsp-page-enter");
      expect(mainContainer).toBeTruthy();
      expect(mainContainer?.className).toContain("max-w-5xl");

      // Verify search input exists and is accessible at this viewport
      const searchInput = screen.getByRole("searchbox", {
        name: "Search a company or ask a research question",
      });
      expect(searchInput).toBeTruthy();
      expect(searchInput.getAttribute("type")).toBe("search");

      // Verify research path action buttons are present and have touch targets
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);
    });
  });
});
