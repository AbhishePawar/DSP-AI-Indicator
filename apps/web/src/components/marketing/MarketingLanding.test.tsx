/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MarketingLanding } from "./MarketingLanding";
import { ANALYSIS_INTENTS } from "@/lib/analysis/intents";
import { useDashboardPrefsStore } from "@/lib/dashboard";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

const mockUseAuth = vi.fn();

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => mockUseAuth(),
}));

describe("MarketingLanding - Research Mode Routing & Depth Selector", () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockUseAuth.mockReturnValue({ user: null });
  });

  afterEach(() => {
    cleanup();
  });

  it("1. normal company search routes to Simple Research (mode=simple, intent=company)", () => {
    render(<MarketingLanding />);
    const input = screen.getByTestId("landing-company-search");
    fireEvent.change(input, { target: { value: "TCS" } });

    const form = screen.getByTestId("landing-search-form");
    fireEvent.submit(form);

    expect(mockPush).toHaveBeenCalledTimes(1);
    const calledUrl = mockPush.mock.calls[0][0] as string;

    const url = new URL(calledUrl, "https://dspaiindicator.com");
    expect(url.pathname).toBe("/analysis");
    expect(url.searchParams.get("symbol")).toBe("TCS");
    expect(url.searchParams.get("mode")).toBe("simple");
    expect(url.searchParams.get("intent")).toBe(ANALYSIS_INTENTS.company);
  });

  it("2. dedicated DSP Buffett button routes to Full DSP analysis (mode=full, intent=dsp_indicator)", () => {
    render(<MarketingLanding />);
    const input = screen.getByTestId("landing-company-search");
    fireEvent.change(input, { target: { value: "TCS" } });

    const buffettBtn = screen.getByTestId("landing-buffett-analysis");
    fireEvent.click(buffettBtn);

    expect(mockPush).toHaveBeenCalledTimes(1);
    const calledUrl = mockPush.mock.calls[0][0] as string;

    const url = new URL(calledUrl, "https://dspaiindicator.com");
    expect(url.pathname).toBe("/analysis");
    expect(url.searchParams.get("symbol")).toBe("TCS");
    expect(url.searchParams.get("mode")).toBe("full");
    expect(url.searchParams.get("intent")).toBe(ANALYSIS_INTENTS.dspIndicator);
  });

  it("2b. dedicated DSP Buffett button with empty query routes to Full DSP analysis without symbol", () => {
    render(<MarketingLanding />);
    const buffettBtn = screen.getByTestId("landing-buffett-analysis");
    fireEvent.click(buffettBtn);

    expect(mockPush).toHaveBeenCalledTimes(1);
    const calledUrl = mockPush.mock.calls[0][0] as string;

    const url = new URL(calledUrl, "https://dspaiindicator.com");
    expect(url.pathname).toBe("/analysis");
    expect(url.searchParams.get("symbol")).toBeNull();
    expect(url.searchParams.get("mode")).toBe("full");
    expect(url.searchParams.get("intent")).toBe(ANALYSIS_INTENTS.dspIndicator);
  });

  it("3. verifies Simple and Full routes are distinctly different and not identical", () => {
    render(<MarketingLanding />);
    const input = screen.getByTestId("landing-company-search");
    fireEvent.change(input, { target: { value: "INFY" } });

    // Submit for simple
    fireEvent.submit(screen.getByTestId("landing-search-form"));
    const simpleUrl = mockPush.mock.calls[0][0] as string;

    mockPush.mockReset();

    // Click buffett button for full
    fireEvent.click(screen.getByTestId("landing-buffett-analysis"));
    const fullUrl = mockPush.mock.calls[0][0] as string;

    expect(simpleUrl).not.toBe(fullUrl);

    const parsedSimple = new URL(simpleUrl, "https://dspaiindicator.com");
    const parsedFull = new URL(fullUrl, "https://dspaiindicator.com");

    expect(parsedSimple.searchParams.get("mode")).toBe("simple");
    expect(parsedSimple.searchParams.get("intent")).toBe(ANALYSIS_INTENTS.company);

    expect(parsedFull.searchParams.get("mode")).toBe("full");
    expect(parsedFull.searchParams.get("intent")).toBe(ANALYSIS_INTENTS.dspIndicator);
  });

  it("4. preserves existing unknown multi-word company identity-search behavior (/search?q=...)", () => {
    render(<MarketingLanding />);
    const input = screen.getByTestId("landing-company-search");
    fireEvent.change(input, { target: { value: "Some Unknown Multiword Company" } });

    fireEvent.submit(screen.getByTestId("landing-search-form"));

    expect(mockPush).toHaveBeenCalledTimes(1);
    const calledUrl = mockPush.mock.calls[0][0] as string;
    expect(calledUrl).toBe("/search?q=Some%20Unknown%20Multiword%20Company");
  });

  it("5a. analysis-depth selector exposes both choices and routes Simple Research correctly", () => {
    render(<MarketingLanding />);
    const input = screen.getByTestId("landing-company-search");
    fireEvent.change(input, { target: { value: "RELIANCE" } });

    // Depth panel should be displayed
    const depthPanel = screen.getByTestId("landing-depth-panel");
    expect(depthPanel).toBeInTheDocument();

    const simpleBtn = screen.getByTestId("landing-simple-research");
    const fullBtn = screen.getByTestId("landing-full-research");
    expect(simpleBtn).toBeInTheDocument();
    expect(fullBtn).toBeInTheDocument();

    // Click Simple Research button
    fireEvent.click(simpleBtn);
    expect(mockPush).toHaveBeenCalledTimes(1);
    const simpleUrl = mockPush.mock.calls[0][0] as string;
    const parsedSimple = new URL(simpleUrl, "https://dspaiindicator.com");
    expect(parsedSimple.searchParams.get("symbol")).toBe("RELIANCE");
    expect(parsedSimple.searchParams.get("mode")).toBe("simple");
    expect(parsedSimple.searchParams.get("intent")).toBe(ANALYSIS_INTENTS.company);
  });

  it("5b. analysis-depth selector exposes both choices and routes Full Research correctly", () => {
    render(<MarketingLanding />);
    const input = screen.getByTestId("landing-company-search");
    fireEvent.change(input, { target: { value: "RELIANCE" } });

    // Depth panel should be displayed
    const depthPanel = screen.getByTestId("landing-depth-panel");
    expect(depthPanel).toBeInTheDocument();

    const fullBtn = screen.getByTestId("landing-full-research");
    expect(fullBtn).toBeInTheDocument();

    // Click Full Research button
    fireEvent.click(fullBtn);
    expect(mockPush).toHaveBeenCalledTimes(1);
    const fullUrl = mockPush.mock.calls[0][0] as string;
    const parsedFull = new URL(fullUrl, "https://dspaiindicator.com");
    expect(parsedFull.searchParams.get("symbol")).toBe("RELIANCE");
    expect(parsedFull.searchParams.get("mode")).toBe("full");
    expect(parsedFull.searchParams.get("intent")).toBe(ANALYSIS_INTENTS.dspIndicator);
  });

  it("6a. company example chip populates company, preserves homepage, and allows picking Simple Research", () => {
    render(<MarketingLanding />);

    // Click an example chip (e.g. TCS)
    const exampleChip = screen.getByTestId("landing-example-TCS");
    fireEvent.click(exampleChip);

    // Should NOT have navigated immediately to /analysis
    expect(mockPush).not.toHaveBeenCalled();

    // Input must be populated with ticker
    const input = screen.getByTestId<HTMLInputElement>("landing-company-search");
    expect(input.value).toBe("TCS");

    // Depth panel must be open presenting both choices
    const depthPanel = screen.getByTestId("landing-depth-panel");
    expect(depthPanel).toBeInTheDocument();
    expect(screen.getByTestId("landing-simple-research")).toBeInTheDocument();
    expect(screen.getByTestId("landing-full-research")).toBeInTheDocument();

    // User picks Simple Research
    fireEvent.click(screen.getByTestId("landing-simple-research"));
    expect(mockPush).toHaveBeenCalledTimes(1);
    const calledUrl = mockPush.mock.calls[0][0] as string;
    const parsedUrl = new URL(calledUrl, "https://dspaiindicator.com");
    expect(parsedUrl.searchParams.get("symbol")).toBe("TCS");
    expect(parsedUrl.searchParams.get("mode")).toBe("simple");
    expect(parsedUrl.searchParams.get("intent")).toBe(ANALYSIS_INTENTS.company);
  });

  it("6b. company example chip populates company and allows picking DSP Buffett Analysis", () => {
    render(<MarketingLanding />);

    // Click an example chip (e.g. HDFCBANK)
    const exampleChip = screen.getByTestId("landing-example-HDFCBANK");
    fireEvent.click(exampleChip);

    expect(mockPush).not.toHaveBeenCalled();

    const input = screen.getByTestId<HTMLInputElement>("landing-company-search");
    expect(input.value).toBe("HDFCBANK");

    // User picks DSP Buffett Analysis
    fireEvent.click(screen.getByTestId("landing-full-research"));
    expect(mockPush).toHaveBeenCalledTimes(1);
    const calledUrl = mockPush.mock.calls[0][0] as string;
    const parsedUrl = new URL(calledUrl, "https://dspaiindicator.com");
    expect(parsedUrl.searchParams.get("symbol")).toBe("HDFCBANK");
    expect(parsedUrl.searchParams.get("mode")).toBe("full");
    expect(parsedUrl.searchParams.get("intent")).toBe(ANALYSIS_INTENTS.dspIndicator);
  });

  it("7. recent search chip populates company, preserves homepage, and opens depth panel", () => {
    mockUseAuth.mockReturnValue({
      user: { userId: "u-1", displayName: "Tester" },
    });
    useDashboardPrefsStore.getState().recordSearch("WIPRO");

    render(<MarketingLanding />);

    const recentChip = screen.getByTestId("landing-recent-WIPRO");
    expect(recentChip).toBeInTheDocument();

    fireEvent.click(recentChip);
    expect(mockPush).not.toHaveBeenCalled();

    const input = screen.getByTestId<HTMLInputElement>("landing-company-search");
    expect(input.value).toBe("WIPRO");

    const depthPanel = screen.getByTestId("landing-depth-panel");
    expect(depthPanel).toBeInTheDocument();
  });
});
