/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: { accessToken: "tok" },
  }),
}));

const shareResearch = vi.fn();
vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>(
    "@/lib/api/client",
  );
  return {
    ...actual,
    api: {
      ...actual.api,
      shareResearch: (...args: unknown[]) => shareResearch(...args),
    },
  };
});

import { ShareResearchPanel } from "@/components/share-research/ShareResearchPanel";

afterEach(() => {
  cleanup();
  shareResearch.mockReset();
});

function wrap(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

describe("ShareResearchPanel", () => {
  it("renders current verified shares", async () => {
    shareResearch.mockResolvedValue({
      ok: true,
      api_version: "v1",
      limitations: [],
      result: {
        status: "CURRENT",
        company: "Tata Consultancy Services Limited",
        ticker: "TCS",
        isin: "INE467B01029",
        exchange: "NSE",
        mic: "XNSE",
        outstanding_shares: 3618087518,
        as_of: "2026-06-30",
        current_through: "2026-09-06",
        last_verified_at: "2026-09-06T12:00:00+00:00",
        confidence: "HIGH",
        identity_check: "PASS",
        corporate_action_check: "PASS",
        cross_check: "PASS",
        valuation_eligible: true,
        gemini_invoked: false,
        reason: "proven",
        unresolved_issues: [],
        stored_vs_fresh: {
          stored: "3618087518",
          fresh: "3618087518",
          result: "MATCH",
        },
        evidence: [
          {
            url: "https://www.tcs.com/investor-relations/investor-faqs",
            label: "tcs.com",
            accepted: true,
            reason: "issuer",
          },
        ],
        corporate_actions: [],
        research_history: [],
        research_method: "Stored DSP research record proven current at lookup horizon",
      },
    });
    render(wrap(<ShareResearchPanel ticker="TCS" exchange="NSE" />));
    fireEvent.click(screen.getByRole("button", { name: /Research TCS/i }));
    expect(
      await screen.findByText(/Verified — current through 6 September 2026/),
    ).toBeTruthy();
    expect(screen.getByText(/Share count accepted for valuation/)).toBeTruthy();
  });

  it("renders unknown fail-closed copy", async () => {
    shareResearch.mockResolvedValue({
      ok: false,
      api_version: "v1",
      limitations: [],
      result: {
        status: "UNKNOWN",
        company: "Infosys Limited",
        ticker: "INFY",
        isin: "INE009A01021",
        exchange: "NSE",
        mic: "XNSE",
        outstanding_shares: null,
        as_of: null,
        current_through: null,
        last_verified_at: "2026-09-06T12:00:00+00:00",
        confidence: "LOW",
        identity_check: "PASS",
        corporate_action_check: "UNRESOLVED",
        cross_check: "FAIL",
        valuation_eligible: false,
        gemini_invoked: true,
        reason: "could not establish",
        unresolved_issues: ["no approved primary source URL"],
        stored_vs_fresh: { stored: null, fresh: null, result: "N/A" },
        evidence: [],
        corporate_actions: [],
        research_history: [],
        research_method: "Gemini primary-source research with DSP validation",
      },
    });
    render(wrap(<ShareResearchPanel ticker="INFY" />));
    fireEvent.click(screen.getByRole("button", { name: /Research INFY/i }));
    expect(
      await screen.findByText(/Current outstanding shares could not be established/),
    ).toBeTruthy();
    expect(screen.getAllByText(/Valuation unavailable/i).length).toBeGreaterThan(0);
  });

  it("renders conflict fail-closed copy", async () => {
    shareResearch.mockResolvedValue({
      ok: false,
      api_version: "v1",
      limitations: [],
      result: {
        status: "CONFLICT",
        company: "Reliance Industries Limited",
        ticker: "RELIANCE",
        isin: "INE002A01018",
        exchange: "NSE",
        mic: "XNSE",
        outstanding_shares: null,
        as_of: "2026-06-30",
        current_through: null,
        last_verified_at: "2026-09-06T12:00:00+00:00",
        confidence: "LOW",
        identity_check: "PASS",
        corporate_action_check: "PASS",
        cross_check: "FAIL",
        valuation_eligible: false,
        gemini_invoked: true,
        reason: "conflicting authoritative evidence",
        unresolved_issues: [],
        stored_vs_fresh: { stored: null, fresh: null, result: "N/A" },
        evidence: [],
        corporate_actions: [],
        research_history: [],
        research_method: "Gemini primary-source research with DSP validation",
      },
    });
    render(wrap(<ShareResearchPanel ticker="RELIANCE" />));
    fireEvent.click(screen.getByRole("button", { name: /Research RELIANCE/i }));
    expect(
      await screen.findByText(/Conflicting evidence/i),
    ).toBeTruthy();
    expect(screen.getAllByText(/Valuation unavailable/i).length).toBeGreaterThan(0);
  });

  it("renders refresh-required fail-closed copy", async () => {
    shareResearch.mockResolvedValue({
      ok: false,
      api_version: "v1",
      limitations: [],
      result: {
        status: "REFRESH_REQUIRED",
        company: "Tata Consultancy Services Limited",
        ticker: "TCS",
        isin: "INE467B01029",
        exchange: "NSE",
        mic: "XNSE",
        outstanding_shares: 3618087518,
        as_of: "2026-06-30",
        current_through: "2026-09-05",
        last_verified_at: "2026-09-05T12:00:00+00:00",
        confidence: "LOW",
        identity_check: "PASS",
        corporate_action_check: "PASS",
        cross_check: "PASS",
        valuation_eligible: false,
        gemini_invoked: false,
        reason: "coverage stale",
        unresolved_issues: [],
        stored_vs_fresh: {
          stored: "3618087518",
          fresh: "3618087518",
          result: "MATCH",
        },
        evidence: [],
        corporate_actions: [],
        research_history: [],
        research_method: "Stored DSP research record proven current at lookup horizon",
      },
    });
    render(wrap(<ShareResearchPanel ticker="TCS" />));
    fireEvent.click(screen.getByRole("button", { name: /Research TCS/i }));
    expect(await screen.findByText(/Verification required/)).toBeTruthy();
    expect(screen.getAllByText(/Valuation unavailable/i).length).toBeGreaterThan(0);
  });
});
