/**
 * @vitest-environment jsdom
 */
import type { ReactNode } from "react";
import { describe, expect, it, vi, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

const resolveSecurityMock = vi.fn();
const analyseMock = vi.fn();
const statementsMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    analyse: (...args: unknown[]) => analyseMock(...args),
    resolveSecurity: (...args: unknown[]) => resolveSecurityMock(...args),
    financialStatements: (...args: unknown[]) => statementsMock(...args),
    researchIntelligencePerformance: vi.fn().mockResolvedValue(null),
    researchIntelligenceCalibration: vi.fn().mockResolvedValue(null),
    researchIntelligenceTimeline: vi.fn().mockResolvedValue(null),
    coverageCompare: vi.fn().mockResolvedValue({
      ok: true,
      available: false,
      quality_shape: null,
      message: "Data unavailable.",
    }),
  },
}));

import { RESEARCH_DISCLAIMER_ACK_KEY } from "@/lib/legal";
import { CompanyComparisonWorkspace } from "@/components/company-comparison";
import { ComparisonPairBoard } from "@/components/company-comparison/ComparisonPairBoard";
import type { ComparisonWorkspaceModel } from "@/lib/company-comparison";

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("CompanyComparisonWorkspace render", () => {
  afterEach(() => cleanup());

  it("renders empty decision workspace shell", () => {
    wrap(<CompanyComparisonWorkspace />);
    expect(
      screen.getByTestId("company-comparison-workspace"),
    ).toBeInTheDocument();
    // The "Compare" title is owned by the route-level Figma page header, so the
    // workspace must not render a second heading.
    expect(
      screen.queryByRole("heading", { name: /^Compare$/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Comparison sections/i)).toBeInTheDocument();
    expect(screen.getByText(/No comparison yet/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Security 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Security 2")).toBeInTheDocument();
  });

  it("resolves both securities before calling analyse", async () => {
    window.localStorage.setItem(RESEARCH_DISCLAIMER_ACK_KEY, "1");
    resolveSecurityMock.mockImplementation(async (query: string) => ({
      ok: true,
      status: "RESOLVED",
      query,
      identity: {
        company_name: query === "INFY" ? "Infosys" : "Tata Consultancy Services",
        ticker: query,
        isin: query === "INFY" ? "INE009A01021" : "INE467B01029",
        exchange: "NSE",
        mic: "XNSE",
        security_type: "EQ",
        eligibility: true,
      },
      candidates: [],
    }));
    statementsMock.mockResolvedValue({ available: false, periods: null });
    analyseMock.mockResolvedValue({
      research_status: "incomplete",
      recommendation: null,
    });
    wrap(<CompanyComparisonWorkspace />);
    fireEvent.change(screen.getByRole("textbox", { name: "Security 1" }), { target: { value: "INFY" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Security 2" }), { target: { value: "TCS" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Compare" })[0]!);
    await waitFor(() => expect(resolveSecurityMock).toHaveBeenCalledWith("INFY", expect.anything()));
    expect(resolveSecurityMock).toHaveBeenCalledWith("TCS", expect.anything());
    await waitFor(() => expect(analyseMock).toHaveBeenCalled());
    const body = analyseMock.mock.calls[0]?.[0] as { isin?: string; exchange?: string };
    expect(body.exchange).toBe("NSE");
    expect(body.isin).toBeTruthy();
  });

  it("draws the comparison radar without invented axis scores", () => {
    const model = {
      slots: [
        { symbol: "AAA", company: "Alpha", status: "ready" },
        { symbol: "BBB", company: "Beta", status: "ready" },
      ],
      scorecard: [],
      tradeOffs: [],
      executive: { evidenceQuality: "", confidence: "" },
      qualityModules: { businessQuality: [] },
    } as unknown as ComparisonWorkspaceModel;
    wrap(<ComparisonPairBoard model={model} />);
    expect(screen.getByRole("img", { name: /Comparison radar/i })).toBeInTheDocument();
    for (const axis of ["Profitability", "Growth", "Margins", "Valuation", "Cash Flow", "Low Debt"]) {
      expect(screen.getAllByText(axis).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByText("Data unavailable.").length).toBeGreaterThanOrEqual(6);
    expect(screen.queryByTestId("radar-polygon-left")).not.toBeInTheDocument();
  });

  it("shows a published growth score and still withholds an incomplete polygon", () => {
    const model = {
      slots: [
        { symbol: "AAA", company: "Alpha", status: "ready" },
        { symbol: "BBB", company: "Beta", status: "ready" },
      ],
      scorecard: [],
      tradeOffs: [],
      executive: { evidenceQuality: "", confidence: "" },
      qualityModules: { businessQuality: [] },
    } as unknown as ComparisonWorkspaceModel;
    wrap(
      <ComparisonPairBoard
        model={model}
        qualityShape={{
          a: {
            profitability: null,
            growth: 75,
            margins: null,
            valuation: null,
            cash_flow: null,
            low_debt: null,
          },
          b: {
            profitability: null,
            growth: null,
            margins: null,
            valuation: null,
            cash_flow: null,
            low_debt: null,
          },
        }}
      />,
    );
    expect(screen.getByText("75")).toBeInTheDocument();
    expect(screen.queryByTestId("radar-polygon-left")).not.toBeInTheDocument();
    expect(screen.queryByTestId("radar-polygon-right")).not.toBeInTheDocument();
  });
});
