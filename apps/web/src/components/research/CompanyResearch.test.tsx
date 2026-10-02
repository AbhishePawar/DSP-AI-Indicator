/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { CompanyHeader } from "./CompanyHeader";
import { CompanyResearchLayout } from "./CompanyResearchLayout";
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
    correlation_id: "corr-test-12345",
    limitations: ["Preliminary filing audit limitation"],
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
        {
          stage: "valuation",
          status: "succeeded",
          has_result: true,
          label: "DCF Model",
          confidence: 0.75,
        },
        {
          stage: "economic_moat",
          status: "succeeded",
          has_result: true,
          label: "Wide",
          decision: "Durable",
          score: 0.9,
        },
        {
          stage: "investment_recommendation",
          status: "succeeded",
          has_result: true,
          decision: "BUY",
        },
        {
          stage: "investment_committee",
          status: "succeeded",
          has_result: true,
          decision: "APPROVE",
        },
      ],
      metadata: {
        total_elapsed_ms: 120,
        execution_order: ["financial", "valuation", "economic_moat"],
        evidence_counts: { total: 5 },
        confidence_summary: { overall: 0.85 },
      },
    },
  };
}

describe("CompanyHeader Component", () => {
  it("renders company identity, audit correlation id, and Deep Research boundary badge", () => {
    const view = mapResearchView(
      mockAnalyseResponse(),
      SAMPLE_ANALYSE_REQUEST,
      "2026-10-02T12:00:00.000Z",
    );

    render(<CompanyHeader view={view} />);

    expect(screen.getByText("Acme Research Corp")).toBeTruthy();
    expect(screen.getByText(/ACM · NYSE/i)).toBeTruthy();
    expect(screen.getByText(/Deep Research: Provider Unavailable/i)).toBeTruthy();
    expect(screen.getByText(/Pipeline Succeeded/i)).toBeTruthy();
    expect(screen.getByText(/Correlation ID: corr-test-12345/i)).toBeTruthy();
    expect(screen.getByText(/Pipeline Version/i)).toBeTruthy();
  });
});

describe("CompanyResearchLayout Component", () => {
  it("renders executive summary hierarchy, evidence sources, and progressive disclosure", () => {
    const view = mapResearchView(
      mockAnalyseResponse(),
      SAMPLE_ANALYSE_REQUEST,
      "2026-10-02T12:00:00.000Z",
    );

    render(<CompanyResearchLayout view={view} />);

    // 1. Executive Summary & Thesis
    expect(screen.getByText("Executive Research Summary")).toBeTruthy();
    expect(screen.getByText(/Investment Thesis & Research Question/i)).toBeTruthy();
    expect(screen.getAllByText("Strong Moat and Pricing Power").length).toBeGreaterThan(0);

    // 2. AI / Deep Research Boundary
    expect(screen.getByText("Deep Research & AI Boundary")).toBeTruthy();
    expect(screen.getAllByText(/Provider Unavailable/i).length).toBeGreaterThan(0);

    // 3. Evidence & Sources section
    expect(screen.getByText("Evidence Provenance & Sources")).toBeTruthy();
    expect(screen.getByText("Primary Financials")).toBeTruthy();
    expect(screen.getByText(/Authenticated 10-K \/ Annual Filings/i)).toBeTruthy();
    expect(screen.getByText(/External AI Citations/i)).toBeTruthy();
    expect(screen.getAllByText(/Source unavailable/i).length).toBeGreaterThan(0);

    // 4. Progressive disclosure toggle
    const auditBtn = screen.getByRole("button", { name: /Show Audit & Provenance Metadata/i });
    expect(auditBtn).toBeTruthy();
    expect(auditBtn.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(auditBtn);
    expect(auditBtn.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText(/120 ms/i)).toBeTruthy();
  });
});
