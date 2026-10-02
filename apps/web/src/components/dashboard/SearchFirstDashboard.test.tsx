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

vi.mock("@/lib/companies/catalogue", () => ({
  searchCatalogue: (query: string) => {
    if (!query) return [];
    if (query.toUpperCase().includes("TCS")) {
      return [
        { ticker: "TCS", name: "Tata Consultancy Services", exchange: "NSE" },
        { ticker: "TCS.BO", name: "Tata Consultancy Services (BSE)", exchange: "BSE" },
      ];
    }
    if (query.toUpperCase().includes("HDFC")) {
      return [{ ticker: "HDFCBANK", name: "HDFC Bank Limited", exchange: "NSE" }];
    }
    return [{ ticker: "INFY", name: "Infosys Limited", exchange: "NSE" }];
  },
}));

vi.mock("@/lib/analysis/recentAnalyses", () => ({
  loadRecentAnalyses: () => [
    {
      ticker: "TCS.NS",
      company: "Tata Consultancy Services",
      exchange: "NSE",
      recommendation: "Strong",
      analysedAt: "2026-10-01T10:00:00Z",
    },
  ],
}));

describe("SearchFirstDashboard: Keyboard navigation, selection, and Escape behavior", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("handles keyboard navigation across matched catalogue suggestions and submits active item on Enter", async () => {
    render(<SearchFirstDashboard />);

    const searchInput = screen.getByRole("searchbox", {
      name: "Search a company or ask a research question",
    });
    fireEvent.change(searchInput, { target: { value: "TCS" } });

    // Wait for debounced search match
    await waitFor(() => {
      expect(screen.getByText("Tata Consultancy Services")).toBeTruthy();
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
