/**
 * @vitest-environment jsdom
 */
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { acknowledgeResearchDisclaimer } from "@/lib/legal";
import { CompanyAnalysisWorkspace } from "./CompanyAnalysisWorkspace";

const push = vi.fn();
const replace = vi.fn();
const navigationState = { search: "symbol=TCS&mode=simple&intent=company" };

vi.mock("next/navigation", () => ({
  usePathname: () => "/analysis",
  useRouter: () => ({ push, replace }),
  useSearchParams: () => new URLSearchParams(navigationState.search),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: { accessToken: "test-token" },
    user: { subject: "u1", role: "analyst" },
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
const financialStatementsMock = vi.fn();
const corporateActionsMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    analyse: (...args: unknown[]) => analyseMock(...args),
    marketQuote: (...args: unknown[]) => marketQuoteMock(...args),
    financialStatements: (...args: unknown[]) => financialStatementsMock(...args),
    corporateActions: (...args: unknown[]) => corporateActionsMock(...args),
  },
}));

function renderWorkspace() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <CompanyAnalysisWorkspace />
    </QueryClientProvider>,
  );
}

describe("CompanyAnalysisWorkspace research mode navigation", () => {
  beforeEach(() => {
    cleanup();
    push.mockReset();
    replace.mockReset();
    analyseMock.mockReset().mockResolvedValue({
      ok: true,
      capability: "analyse",
      limitations: [],
      errors: [],
      api_version: "v1",
      platform_version: "1.0.0",
      pipeline_version: "1.0.0",
    });
    marketQuoteMock.mockReset().mockResolvedValue({ ok: true, available: false });
    financialStatementsMock.mockReset().mockResolvedValue({ ok: true, available: false });
    corporateActionsMock.mockReset().mockResolvedValue({ ok: true, available: false });
    acknowledgeResearchDisclaimer();
  });

  it("A. preserves Simple Research mode when changing company (TCS -> INFY)", async () => {
    navigationState.search = "symbol=TCS&mode=simple&intent=company";
    renderWorkspace();

    const input = screen.getByTestId("analysis-symbol");
    fireEvent.change(input, { target: { value: "INFY" } });

    const form = screen.getByTestId("analysis-search-form");
    fireEvent.submit(form);

    expect(replace).toHaveBeenCalledTimes(1);
    expect(replace).toHaveBeenCalledWith("/analysis?symbol=INFY&mode=simple&intent=company");
  });

  it("B. preserves Full DSP Buffett mode when changing company (TCS -> INFY)", async () => {
    navigationState.search = "symbol=TCS&mode=full&intent=dsp_indicator";
    renderWorkspace();

    const input = screen.getByTestId("analysis-symbol");
    fireEvent.change(input, { target: { value: "INFY" } });

    const form = screen.getByTestId("analysis-search-form");
    fireEvent.submit(form);

    expect(replace).toHaveBeenCalledTimes(1);
    expect(replace).toHaveBeenCalledWith("/analysis?symbol=INFY&mode=full&intent=dsp_indicator");
  });

  it("C. switches mode from Simple to Full while preserving symbol (TCS)", async () => {
    navigationState.search = "symbol=TCS&mode=simple&intent=company";
    renderWorkspace();

    const switchBtn = screen.getByTestId("analysis-switch-mode");
    expect(switchBtn.textContent).toContain("Open full analysis");
    fireEvent.click(switchBtn);

    expect(replace).toHaveBeenCalledTimes(1);
    expect(replace).toHaveBeenCalledWith("/analysis?symbol=TCS&mode=full&intent=dsp_indicator");
  });

  it("D. switches mode from Full to Simple while preserving symbol (TCS)", async () => {
    navigationState.search = "symbol=TCS&mode=full&intent=dsp_indicator";
    renderWorkspace();

    const switchBtn = screen.getByTestId("analysis-switch-mode");
    expect(switchBtn.textContent).toContain("Switch to simple research");
    fireEvent.click(switchBtn);

    expect(replace).toHaveBeenCalledTimes(1);
    expect(replace).toHaveBeenCalledWith("/analysis?symbol=TCS&mode=simple&intent=company");
  });

  it("E. preserves safe default (full) when mode is missing from URL", async () => {
    navigationState.search = "symbol=TCS";
    renderWorkspace();

    const input = screen.getByTestId("analysis-symbol");
    fireEvent.change(input, { target: { value: "INFY" } });

    const form = screen.getByTestId("analysis-search-form");
    fireEvent.submit(form);

    expect(replace).toHaveBeenCalledTimes(1);
    expect(replace).toHaveBeenCalledWith("/analysis?symbol=INFY&mode=full&intent=dsp_indicator");
  });
});
