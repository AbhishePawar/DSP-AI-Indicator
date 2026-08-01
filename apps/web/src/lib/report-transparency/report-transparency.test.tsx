/**
 * @vitest-environment jsdom
 */
/**
 * P2.1 — Report transparency tests.
 */

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  buildReportId,
  mapDataFreshness,
  mapReportTransparency,
} from "@/lib/report-transparency";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { buildAnalyseRequestForTicker } from "@/lib/research/buildAnalyseRequest";
import { researchViewToCsv, researchViewToJson } from "@/lib/company-analysis";
import { ReportInformationCard } from "@/components/company-analysis/ReportInformationCard";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";

const sampleResponse: AnalyseResponse = {
  ok: true,
  capability: "analyse",
  payload: {
    ok: true,
    metadata: {
      pipeline_version: "1.0.0-test",
      platform_version: "1.0.0",
      package_versions: { investment_recommendation: "0.1.0" },
    },
    stage_summaries: [
      {
        stage: "financial",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Ok",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "economic_moat",
        status: "succeeded",
        has_result: true,
        score: 75,
        label: "Narrow",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "management_quality",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Ok",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "financial_strength",
        status: "succeeded",
        has_result: true,
        score: 72,
        label: "Ok",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "earnings_quality",
        status: "succeeded",
        has_result: true,
        score: 71,
        label: "Ok",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "growth_quality",
        status: "succeeded",
        has_result: true,
        score: 68,
        label: "Ok",
        confidence: 0.6,
        error: null,
        warnings: [],
      },
      {
        stage: "business_quality_aggregator",
        status: "succeeded",
        has_result: true,
        score: 73,
        label: "Good",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "investment_recommendation",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Hold",
        decision: "hold",
        confidence: 0.66,
        error: null,
        warnings: [],
      },
      {
        stage: "investment_committee",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Hold",
        decision: "hold",
        confidence: 0.6,
        error: null,
        warnings: [],
      },
    ],
    recommendation_summary: {
      decision: "hold",
      confidence: 0.66,
      margin_of_safety: 0.1,
    },
    committee_summary: { decision: "hold", confidence: 0.6 },
  },
  limitations: [],
  errors: [],
  api_version: "v1",
  platform_version: "1.0.0",
  pipeline_version: "1.0.0-test",
  correlation_id: "corr-p21",
};

describe("P2.1 report transparency", () => {
  it("builds a stable report id for identical inputs", () => {
    const a = buildReportId({
      ticker: "AAPL",
      exchange: "NASDAQ",
      analysedAt: "2026-07-28T12:00:00.000Z",
      correlationId: "corr-p21",
      pipelineVersion: "1.0.0-test",
      platformVersion: "1.0.0",
      frontendVersion: "1.3.0",
    });
    const b = buildReportId({
      ticker: "AAPL",
      exchange: "NASDAQ",
      analysedAt: "2026-07-28T12:00:00.000Z",
      correlationId: "corr-p21",
      pipelineVersion: "1.0.0-test",
      platformVersion: "1.0.0",
      frontendVersion: "1.3.0",
    });
    expect(a).toBe(b);
    expect(a.startsWith("DSP-RPT-")).toBe(true);
  });

  it("never guesses data freshness", () => {
    expect(mapDataFreshness(null)).toBe("Unavailable");
    expect(mapDataFreshness("open")).toBe("Unavailable");
    expect(mapDataFreshness("delayed quote")).toBe("Delayed");
    expect(mapDataFreshness("live feed")).toBe("Latest Available");
  });

  it("maps transparency from ResearchView without inventing period", () => {
    const request = buildAnalyseRequestForTicker("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    expect(view.transparency.kind).toBe("report_transparency");
    expect(view.transparency.dataInformation.financialPeriodUsed).toBe(
      "Unavailable",
    );
    expect(view.transparency.transparency.recommendationEngineVersion).toBe(
      "0.1.0",
    );
    expect(view.transparency.qualityBadges.length).toBe(6);
  });

  it("renders Report Information card", () => {
    const request = buildAnalyseRequestForTicker("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    render(
      <ReportInformationCard
        transparency={mapReportTransparency(view, { marketStatus: "live" })}
      />,
    );
    expect(screen.getByText("Report Information")).toBeTruthy();
    expect(screen.getByText("Latest Available")).toBeTruthy();
    expect(screen.getByText(view.transparency.reportId)).toBeTruthy();
  });

  it("includes report information in exports", () => {
    const request = buildAnalyseRequestForTicker("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    expect(researchViewToJson(view)).toContain("reportInformation");
    expect(researchViewToCsv(view)).toContain("reportId");
  });
});
