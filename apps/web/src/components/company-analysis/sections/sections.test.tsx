/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach } from "vitest";

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    session: { accessToken: "tok" },
  }),
}));

const corporateActionsMock = vi.fn();
const copilotCompleteMock = vi.fn();
const analyzeCompanyMock = vi.fn();
const compareMock = vi.fn();
const newsMock = vi.fn();
const filingsMock = vi.fn();
const ownershipMock = vi.fn();
const insiderTradingMock = vi.fn();
const transcriptsMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    corporateActions: (...args: unknown[]) => corporateActionsMock(...args),
    copilotComplete: (...args: unknown[]) => copilotCompleteMock(...args),
    analyzeCompany: (...args: unknown[]) => analyzeCompanyMock(...args),
    compare: (...args: unknown[]) => compareMock(...args),
    news: (...args: unknown[]) => newsMock(...args),
    filings: (...args: unknown[]) => filingsMock(...args),
    ownership: (...args: unknown[]) => ownershipMock(...args),
    insiderTrading: (...args: unknown[]) => insiderTradingMock(...args),
    transcripts: (...args: unknown[]) => transcriptsMock(...args),
  },
}));

import { buildDemoAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import { useWorkspacePrefsStore } from "@/lib/company-analysis";
import { ThemeProvider } from "@/providers/ThemeProvider";

import { PeersSection } from "./PeersSection";
import { AiCopilotSection } from "./AiCopilotSection";
import { OwnershipSection } from "./OwnershipSection";
import { DocumentsSection } from "./DocumentsSection";
import { NewsSection } from "./NewsSection";
import { SettingsSection } from "./SettingsSection";

const sampleResponse: AnalyseResponse = {
  ok: true,
  capability: "analyse",
  limitations: [],
  errors: [],
  api_version: "v1",
  platform_version: "1.0.0",
  pipeline_version: "1.0.0",
  correlation_id: "corr-1",
  payload: { ok: true, stage_summaries: [] },
};

function buildView() {
  const request = buildDemoAnalyseRequest("AAPL", {
    company: "Apple",
    exchange: "NASDAQ",
  });
  return mapResearchView(sampleResponse, request, "2026-07-28T12:00:00.000Z");
}

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider>{ui}</ThemeProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  corporateActionsMock.mockReset();
  copilotCompleteMock.mockReset();
  analyzeCompanyMock.mockReset();
  compareMock.mockReset();
  newsMock.mockReset().mockResolvedValue({ ok: true, available: false, authenticated: false });
  filingsMock.mockReset().mockResolvedValue({ ok: true, available: false, authenticated: false });
  ownershipMock.mockReset().mockResolvedValue({ ok: true, available: false, authenticated: false });
  insiderTradingMock
    .mockReset()
    .mockResolvedValue({ ok: true, available: false, authenticated: false });
  transcriptsMock
    .mockReset()
    .mockResolvedValue({ ok: true, available: false, authenticated: false });
  useWorkspacePrefsStore.setState({
    activeSection: "summary",
    leftOpen: true,
    rightOpen: true,
    notes: [],
    tags: [],
  });
});

afterEach(() => {
  cleanup();
});

describe("PeersSection", () => {
  it("requires at least one peer ticker before comparing", () => {
    const view = buildView();
    wrap(<PeersSection view={view} />);
    expect(
      screen.getByRole("button", { name: "Compare" }),
    ).toBeDisabled();
  });
});

describe("AiCopilotSection", () => {
  it("prompts the user to run analysis before asking questions", () => {
    const view = buildView();
    wrap(
      <AiCopilotSection view={view} analyseRequest={null} analyseResponse={null} />,
    );
    expect(
      screen.getByText(/Run an analysis first/i),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("calls the backend copilot engine for a suggested question", async () => {
    copilotCompleteMock.mockResolvedValue({
      content: "The valuation uses DCF and Relative methods.",
      citations: ["Valuation"],
      intent: "explain_valuation",
      unavailable: false,
      provider_id: "test",
      limitations: [],
    });
    const view = buildView();
    const request = buildDemoAnalyseRequest("AAPL");
    wrap(
      <AiCopilotSection
        view={view}
        analyseRequest={request}
        analyseResponse={sampleResponse}
      />,
    );
    screen.getByRole("button", { name: /Explain the valuation/i }).click();
    await waitFor(() => expect(copilotCompleteMock).toHaveBeenCalled());
    expect(
      await screen.findByText("The valuation uses DCF and Relative methods."),
    ).toBeTruthy();
  });
});

describe("Honest empty-state sections", () => {
  it("OwnershipSection reports no connected data source by default", async () => {
    wrap(<OwnershipSection view={buildView()} />);
    await waitFor(() => expect(ownershipMock).toHaveBeenCalled());
    await waitFor(() =>
      expect(
        screen.getAllByText("Data unavailable — no data source connected.")
          .length,
      ).toBeGreaterThanOrEqual(3),
    );
  });

  it("NewsSection reports no connected data source by default", async () => {
    wrap(<NewsSection view={buildView()} />);
    await waitFor(() => expect(newsMock).toHaveBeenCalled());
    expect(
      await screen.findByText("Data unavailable — no data source connected."),
    ).toBeTruthy();
  });

  it("DocumentsSection shows real Corporate Actions plus honest placeholders", async () => {
    corporateActionsMock.mockResolvedValue({
      ok: true,
      available: false,
      authenticated: false,
      events: null,
    });
    wrap(<DocumentsSection view={buildView()} />);
    expect(screen.getByText("Annual Reports")).toBeTruthy();
    expect(screen.getByText("Corporate Actions")).toBeTruthy();
    await waitFor(() => expect(corporateActionsMock).toHaveBeenCalled());
    await waitFor(() => expect(filingsMock).toHaveBeenCalled());
    await waitFor(() => expect(transcriptsMock).toHaveBeenCalled());
  });

  it("SettingsSection reuses the workspace prefs store", () => {
    wrap(<SettingsSection view={buildView()} />);
    expect(screen.getByText("Appearance")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Hide navigation/i })).toBeTruthy();
  });
});
