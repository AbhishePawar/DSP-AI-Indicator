/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";

const signalsMock = vi.fn();
const performanceMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    coverageSignals: (...args: unknown[]) => signalsMock(...args),
    researchIntelligencePerformance: (...args: unknown[]) => performanceMock(...args),
  },
}));

import { FigmaSignalFeed } from "./FigmaSignalFeed";

function wrap(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const SIGNALS = {
  count: 2,
  sectors: ["IT", "Banking"],
  today: { new_signals: 2, upgrades: 1, downgrades: 0, risk_flags: 1, as_of: null },
  signals: [
    {
      signal_id: "s1",
      symbol: "TCS",
      company_name: "Tata Consultancy Services",
      sector: "IT",
      type: "upgrade",
      timestamp: new Date().toISOString(),
      label: "Rating change",
      text: "Rating moved after the latest research run.",
      severity: "info",
    },
    {
      signal_id: "s2",
      symbol: "HDFCBANK",
      company_name: "HDFC Bank",
      sector: "Banking",
      type: "risk",
      timestamp: new Date().toISOString(),
      label: "Risk alert",
      text: "Leverage flag raised by the risk stage.",
      severity: "warn",
    },
  ],
};

describe("FigmaSignalFeed (Research Intelligence)", () => {
  beforeEach(() => {
    cleanup();
    signalsMock.mockReset();
    performanceMock.mockReset();
  });

  it("renders API signals, sector filter, summary and measurement values", async () => {
    signalsMock.mockResolvedValue(SIGNALS);
    performanceMock.mockResolvedValue({
      dashboard: { overall_accuracy: 0.62, recommendation_accuracy: null },
    });
    wrap(<FigmaSignalFeed />);

    expect(await screen.findByText("TCS")).toBeTruthy();
    expect(screen.getByText("HDFCBANK")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Research TCS →" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "IT" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Banking" })).toBeTruthy();
    expect(screen.getByText("Today's Summary")).toBeTruthy();
    expect(await screen.findByText("62.0%")).toBeTruthy();
    expect(screen.getAllByText("Data unavailable.").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Risk Alert" }));
    expect(screen.queryByText("TCS")).toBeNull();
    expect(screen.getByText("HDFCBANK")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Banking" }));
    expect(signalsMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ sector: "Banking" }),
    );
  });

  it("renders honest empty and error states without demo signals", async () => {
    signalsMock.mockResolvedValue({ ...SIGNALS, signals: [], count: 0 });
    performanceMock.mockRejectedValue(new Error("down"));
    wrap(<FigmaSignalFeed />);
    expect(await screen.findAllByText("Data unavailable.")).toBeTruthy();
    expect(screen.queryByText(/TITAN|Titan Company/)).toBeNull();

    cleanup();
    signalsMock.mockRejectedValue(new Error("down"));
    wrap(<FigmaSignalFeed />);
    expect(await screen.findByText("Signals unavailable")).toBeTruthy();
  });
});
