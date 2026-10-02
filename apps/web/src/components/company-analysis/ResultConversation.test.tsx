/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ResultConversation } from "./ResultConversation";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";

vi.mock("@/lib/portfolio/PortfolioProvider", () => ({
  usePortfolio: () => ({
    recordResearchOpened: vi.fn(),
  }),
}));

vi.mock("@/components/portfolio/AddToPortfolioButton", () => ({
  AddToPortfolioButton: (props: any) => (
    <button type="button" aria-label="Add to portfolio" data-ticker={props.ticker}>
      Add to portfolio
    </button>
  ),
}));

vi.mock("@/components/market/MarketDataCard", () => ({
  MarketDataCard: ({ ticker }: { ticker: string }) => (
    <div data-testid="market-data-card">{ticker} market quote</div>
  ),
}));

function mockAnalyseResponse(): AnalyseResponse {
  return {
    ok: true,
    capability: "compose_intelligence",
    api_version: "0.2.0",
    platform_version: "1.0.0",
    pipeline_version: "1.0.0",
    correlation_id: "corr-test-copilot",
    limitations: [],
    errors: [],
    payload: {
      ok: true,
      has_valuation: true,
      has_business_quality: true,
      has_investment_recommendation: true,
      has_investment_committee: true,
      recommendation_summary: {
        decision: "BUY",
        confidence: 0.85,
        margin_of_safety: 0.25,
      },
      committee_summary: {
        decision: "APPROVE",
        confidence: 0.8,
        consensus: "Strong Moat and Pricing Power",
        rationale: "High recurring revenue base",
      },
      stage_summaries: [
        {
          stage: "financial",
          status: "succeeded",
          has_result: true,
          score: 0.8,
          label: "Strong",
        },
      ],
      metadata: {
        total_elapsed_ms: 120,
        execution_order: ["financial"],
        evidence_counts: { total: 5 },
        confidence_summary: { overall: 0.85 },
      },
    },
  };
}

describe("ResultConversation Component", () => {
  it("renders research hierarchy: result, copilot context, suggestions, and accessible input", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const view = mapResearchView(
      mockAnalyseResponse(),
      SAMPLE_ANALYSE_REQUEST,
      "2026-10-02T12:00:00.000Z",
    );

    render(
      <QueryClientProvider client={queryClient}>
        <ResultConversation
          view={view}
          analyseRequest={SAMPLE_ANALYSE_REQUEST}
          analyseResponse={mockAnalyseResponse()}
          onShare={vi.fn()}
          onRefresh={vi.fn()}
        />
      </QueryClientProvider>,
    );

    // 1. Authoritative Header & Result
    expect(screen.getByText("Acme Research Corp")).toBeTruthy();
    expect(screen.getByText(/1. Authoritative Research Result/i)).toBeTruthy();

    // 2. Copilot Section & Context awareness
    expect(
      screen.getByText(/2. Research Interaction & Follow-up Copilot/i),
    ).toBeTruthy();
    expect(screen.getByText(/Context:/i)).toBeTruthy();
    expect(screen.getByText("ACM")).toBeTruthy();
    expect(
      screen.getByText(/AI Provider: Bounded \(Deterministic Engine\)/i),
    ).toBeTruthy();

    // 3. Suggested Follow-up Actions
    expect(screen.getByText("Explain the valuation")).toBeTruthy();
    expect(screen.getByText("Why is margin of safety low?")).toBeTruthy();
    expect(screen.getByText("Explain the key risks")).toBeTruthy();
    expect(screen.getByText("Run DSP Buffett-style analysis")).toBeTruthy();

    // 4. Accessible Composer Input
    const textarea = screen.getByLabelText(/Ask a follow-up question/i);
    expect(textarea).toBeTruthy();
    expect(screen.getByRole("button", { name: /Send inquiry/i })).toBeTruthy();
  });
});
