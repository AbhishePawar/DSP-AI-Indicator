/** @vitest-environment jsdom */

import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ValidationBanner } from "@/components/intelligence/ValidationBanner";
import { PipelineTimeline } from "@/components/intelligence/PipelineTimeline";
import { HealthIndicator } from "@/components/intelligence/HealthIndicator";

afterEach(() => {
  cleanup();
});

describe("ValidationBanner", () => {
  it("shows validation errors and retry", () => {
    const onRetry = vi.fn();
    render(
      React.createElement(ValidationBanner, {
        apiError: "Request failed",
        correlationId: "corr-1",
        onRetry,
      }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Request failed");
    expect(screen.getByText(/corr-1/)).toBeTruthy();
    screen.getByRole("button", { name: /retry/i }).click();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("shows success validation state", () => {
    render(
      React.createElement(ValidationBanner, {
        valid: true,
        errors: [],
        warnings: ["exchange not provided"],
      }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Validation passed");
  });
});

describe("PipelineTimeline", () => {
  it("renders stage statuses accessibly", () => {
    render(
      React.createElement(PipelineTimeline, {
        stages: [
          {
            stage: "financial",
            status: "succeeded",
            has_result: true,
            label: "Complete",
          },
        ],
      }),
    );
    expect(screen.getByLabelText("Pipeline stages")).toBeTruthy();
    expect(screen.getByText("financial")).toBeTruthy();
    expect(screen.getByText("succeeded")).toBeTruthy();
  });
});

describe("HealthIndicator", () => {
  it("announces ready status", () => {
    render(
      React.createElement(HealthIndicator, {
        ready: true,
        status: "pass",
        platformVersion: "0.7.1",
        pipelineVersion: "1.0.0-epic-001",
      }),
    );
    expect(screen.getByLabelText("API health")).toHaveTextContent("API ready");
  });
});
