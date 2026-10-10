/**
 * @vitest-environment jsdom
 */
import React from "react";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ZipCompanyAnalysisWorkspace } from "../ZipCompanyAnalysisWorkspace";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";

let mockSearchParams = new URLSearchParams("symbol=INFY&mode=simple");

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => mockSearchParams,
}));

beforeAll(() => {
  class MockIntersectionObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }
  Object.defineProperty(window, "IntersectionObserver", {
    writable: true,
    configurable: true,
    value: MockIntersectionObserver,
  });
});

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderWorkspace() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ZipCompanyAnalysisWorkspace />
    </QueryClientProvider>
  );
}

describe("ZipCompanyAnalysisWorkflow — Real API Lifecycle & Zero-Fabrication Guarantees", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams("symbol=INFY&mode=simple");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("automatically initiates analysis once for valid ?symbol= query parameter", async () => {
    const analyseSpy = vi.spyOn(api, "analyse").mockResolvedValue({
      ok: true,
      schema_version: "2.0.0",
      ticker: "INFY",
      exchange: "NSE",
      payload: { company: "Infosys Ltd" },
    } as unknown as AnalyseResponse);

    renderWorkspace();

    await waitFor(() => {
      expect(analyseSpy).toHaveBeenCalledTimes(1);
    });
    expect(analyseSpy).toHaveBeenCalledWith({ ticker: "INFY" });
  });

  it("transitions to loading state while request is in flight", async () => {
    let resolveAnalysis: (val: AnalyseResponse) => void = () => {};
    const analysisPromise = new Promise<AnalyseResponse>((resolve) => {
      resolveAnalysis = resolve;
    });

    vi.spyOn(api, "analyse").mockReturnValue(analysisPromise);

    renderWorkspace();

    // Loader step should be visible while pending
    expect(screen.getByText(/STAGE 1 OF 4/i)).toBeDefined();

    // Now resolve
    resolveAnalysis({
      ok: true,
      schema_version: "2.0.0",
      ticker: "INFY",
      exchange: "NSE",
      payload: { company: "Infosys Ltd" },
    } as unknown as AnalyseResponse);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "INFY" })).toBeDefined();
    });
  });

  it("renders actionable Authentication Required message and Sign In button on HTTP 401", async () => {
    vi.spyOn(api, "analyse").mockRejectedValue(
      new ApiClientError("Unauthorized", 401, {
        ok: false,
        error: "Unauthorized",
        detail: "Session expired or missing",
        message: "Session expired",
        api_version: "v1",
        status_code: 401,
      })
    );

    renderWorkspace();

    await waitFor(() => {
      expect(screen.getByText("Authentication Required")).toBeDefined();
    });
    expect(screen.getByText(/Please sign in to access stock research/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /Sign In/i })).toBeDefined();

    // Must NEVER render financial dashboard or zeroed numbers on error
    expect(screen.queryByText("Financials")).toBeNull();
  });

  it("renders actionable Access Forbidden message on HTTP 403", async () => {
    vi.spyOn(api, "analyse").mockRejectedValue(
      new ApiClientError("Forbidden", 403, {
        ok: false,
        error: "Forbidden",
        detail: "Tier permission missing",
        message: "Forbidden",
        api_version: "v1",
        status_code: 403,
      })
    );

    renderWorkspace();

    await waitFor(() => {
      expect(screen.getByText("Access Forbidden")).toBeDefined();
    });
    expect(screen.getByRole("button", { name: /Retry Analysis/i })).toBeDefined();
    expect(screen.queryByText("Financials")).toBeNull();
  });

  it("renders Request Timed Out message on HTTP 408", async () => {
    vi.spyOn(api, "analyse").mockRejectedValue(
      new ApiClientError("Request Timeout", 408, {
        ok: false,
        error: "Timeout",
        detail: "Gateway timeout",
        message: "Timeout",
        api_version: "v1",
        status_code: 408,
      })
    );

    renderWorkspace();

    await waitFor(() => {
      expect(screen.getByText("Request Timed Out")).toBeDefined();
    });
    expect(screen.getByRole("button", { name: /Retry Analysis/i })).toBeDefined();
    expect(screen.queryByText("Financials")).toBeNull();
  });

  it("never renders zeroed, fabricated or placeholder financial results on API failure", async () => {
    vi.spyOn(api, "analyse").mockRejectedValue(new Error("Network Error"));

    renderWorkspace();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeDefined();
    });
    expect(screen.getByText("Analysis Failed")).toBeDefined();

    // Ensure no financial metrics or sections are rendered
    expect(screen.queryByLabelText("Analysis sections")).toBeNull();
    expect(screen.queryByText("Executive Summary")).toBeNull();
  });
});
