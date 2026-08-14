/** @vitest-environment jsdom */

import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { InstitutionalResearchDashboard } from "@/components/institutional-dashboard/InstitutionalResearchDashboard";
import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { mapInstitutionalDashboard } from "@/lib/institutional-dashboard/mapInstitutionalDashboard";
import { DATA_UNAVAILABLE } from "@/lib/institutional-dashboard/types";
import { unavailableField } from "@/lib/institutional-dashboard/display";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";

afterEach(() => {
  cleanup();
});

function sampleResponse(): AnalyseResponse {
  return {
    ok: true,
    capability: "analyse",
    payload: {
      ok: true,
      metadata: { pipeline_version: "1.0.0", platform_version: "0.7.1" },
      stage_summaries: [
        {
          stage: "business_quality_aggregator",
          status: "succeeded",
          has_result: true,
          score: 70,
          label: "Good",
          confidence: 0.7,
        },
      ],
      recommendation_summary: { decision: "hold_for_research", confidence: 0.6 },
    },
    correlation_id: "corr-ui-1",
    errors: [],
    limitations: [],
    api_version: "v1",
    platform_version: "0.7.1",
    pipeline_version: "1.0.0",
  };
}

describe("MetricCell", () => {
  it("renders Data unavailable. for missing values", () => {
    render(
      React.createElement(MetricCell, {
        label: "Current price",
        field: unavailableField(),
      }),
    );
    expect(screen.getByText(DATA_UNAVAILABLE)).toBeTruthy();
    expect(screen.getByText("Current price")).toBeTruthy();
  });
});

describe("InstitutionalResearchDashboard", () => {
  it("renders mandatory RS sections and MoS prominence", () => {
    const view = mapInstitutionalDashboard({
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
      analysedAt: "2026-07-28T12:00:00.000Z",
    });

    render(React.createElement(InstitutionalResearchDashboard, { view }));

    expect(
      screen.getByRole("navigation", { name: /research dashboard sections/i }),
    ).toBeTruthy();
    expect(screen.getByRole("heading", { name: /executive summary/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /margin of safety/i })).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: /authenticated market data/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: /financial statement analysis/i }),
    ).toBeTruthy();
    expect(screen.getByRole("heading", { name: /^valuation$/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /business quality/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /risk analysis/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /scenario analysis/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /^explainability$/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /audit & provenance/i })).toBeTruthy();
    expect(screen.getAllByText(DATA_UNAVAILABLE).length).toBeGreaterThan(0);
  });

  it("exposes keyboard-focusable section links", () => {
    const view = mapInstitutionalDashboard({
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
      analysedAt: null,
    });
    render(React.createElement(InstitutionalResearchDashboard, { view }));
    const link = screen.getByRole("link", { name: /^executive$/i });
    expect(link.getAttribute("href")).toBe("#rs-001-executive");
  });
});
