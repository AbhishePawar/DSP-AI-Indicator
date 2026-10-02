/**
 * @vitest-environment jsdom
 */
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: () => "/analysis/compare",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: {
      accessToken: "tok",
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

vi.mock("@/lib/api/client", () => ({
  api: {
    analyse: vi.fn(),
    researchIntelligencePerformance: vi.fn(),
    researchIntelligenceCalibration: vi.fn(),
    researchIntelligenceTimeline: vi.fn(),
  },
}));

import { CompanyComparisonWorkspace } from "@/components/company-comparison";

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("CompanyComparisonWorkspace render", () => {
  it("renders empty decision workspace shell", () => {
    wrap(<CompanyComparisonWorkspace />);
    expect(
      screen.getByTestId("company-comparison-workspace"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Institutional Company Comparison/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/No comparison yet/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Comparison tickers/i)).toBeInTheDocument();
  });

  it("renders two-security symmetrical comparison header and Winner Matrix dynamically without hardcoding", async () => {
    const { WinnerMatrixSection } = await import(
      "@/components/company-comparison/Sections"
    );
    const { render, screen, cleanup } = await import("@testing-library/react");
    cleanup();

    // Dynamic mock model for Security 1 and Security 2
    const dynamicModel = {
      symbols: ["SEC1", "SEC2"],
      slots: [
        { symbol: "SEC1", company: "Security Alpha Corp", exchange: "NYSE", status: "ready" },
        { symbol: "SEC2", company: "Security Beta Ltd", exchange: "NASDAQ", status: "ready" },
      ],
      winnerMatrix: [
        {
          id: "valuation",
          label: "Valuation Score",
          leader: "SEC1",
          cells: [
            { symbol: "SEC1", display: "78.5", medal: "gold" as const },
            { symbol: "SEC2", display: "62.0", medal: "silver" as const },
          ],
        },
        {
          id: "missing_metric",
          label: "Growth Metric",
          leader: "Data unavailable.",
          cells: [
            { symbol: "SEC1", display: "Data unavailable.", medal: null },
            { symbol: "SEC2", display: "Data unavailable.", medal: null },
          ],
        },
      ],
      tradeOffs: [],
    } as any;

    render(<WinnerMatrixSection model={dynamicModel} />);

    // 1. Assert dynamic Security 1 and Security 2 headers
    expect(screen.getByText(/Security 1 \(SEC1\)/i)).toBeTruthy();
    expect(screen.getByText(/Security Alpha Corp/i)).toBeTruthy();
    expect(screen.getByText(/Security 2 \(SEC2\)/i)).toBeTruthy();
    expect(screen.getByText(/Security Beta Ltd/i)).toBeTruthy();

    // 2. Assert Winner / Leader table semantics and values
    expect(screen.getByRole("table", { name: /Winner comparison matrix/i })).toBeTruthy();
    expect(screen.getByText("Valuation Score")).toBeTruthy();
    expect(screen.getByText("78.5")).toBeTruthy();
    expect(screen.getByText("62.0")).toBeTruthy();
    expect(screen.getByText("SEC1")).toBeTruthy();

    // 3. Assert honest missing data / unavailable state
    expect(screen.getAllByText("Data unavailable.").length).toBeGreaterThan(0);
  });
});
