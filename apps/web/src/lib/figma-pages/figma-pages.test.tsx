/**
 * @vitest-environment jsdom
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import type {
  DashboardOverviewResponse,
  InstitutionalResponse,
  MarketIndicesResponse,
  PortfolioHoldingRow,
  PortfolioResponse,
  ProfileResponse,
} from "@/lib/api/workspaceTypes";
import type { ArchivedResearchSession } from "@/lib/copilot/sessionArchive";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";
import type { PortfolioHolding } from "@/lib/portfolio/model";

import {
  formToPayload,
  gaugeNeedle,
  primaryCtaLabel,
  profileToForm,
  scoreRows,
  zoneColor,
} from "./clientProfileView";
import {
  buildWatchlistSymbols,
  formatQuoteChange,
  MARKET_BAR_PLACEHOLDERS,
  mapMarketIndices,
  mapRecentResearch,
  mapServerRecentResearch,
  mapServerWatchlistRow,
  mapSignals,
  mapWatchlistRow,
  ratingForSymbol,
  relativeTime,
} from "./dashboardView";
import {
  buildPortfolioSummaryCards,
  buildSectorSlices,
  donutSegments,
  formatCompactInr,
  mapHoldingRow,
  sortHoldings,
} from "./portfolioView";
import {
  analysisHref,
  buildSavedResearch,
  filterSavedResearch,
  mapServerSavedResearch,
  mergeSavedResearch,
  normaliseResearchSymbol,
  RESEARCH_TEMPLATES,
} from "./researchHubView";

const quoteMock = vi.fn();
const marketIndicesMock = vi.fn();
const dashboardMock = vi.fn();
const portfolioMock = vi.fn();
const institutionalMock = vi.fn();
const savedResearchMock = vi.fn();
const profileMock = vi.fn();
let mockHoldings: PortfolioHolding[] = [];

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: { accessToken: "tok" },
    user: { displayName: "Ada" },
  }),
}));

vi.mock("@/lib/portfolio/PortfolioProvider", () => ({
  usePortfolio: () => ({
    view: { holdings: mockHoldings, allocations: { bySector: [], byMarketCap: [], byGeography: [] }, summary: {}, activities: [] },
    holdings: mockHoldings,
    isEmpty: mockHoldings.length === 0,
    hasTicker: () => false,
    addHolding: vi.fn(),
    removeHolding: vi.fn(),
    recordResearchOpened: vi.fn(),
    clearPortfolio: vi.fn(),
  }),
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    marketQuote: (...args: unknown[]) => quoteMock(...args),
    marketIndices: (...args: unknown[]) => marketIndicesMock(...args),
    workspaceDashboard: (...args: unknown[]) => dashboardMock(...args),
    workspacePortfolio: (...args: unknown[]) => portfolioMock(...args),
    workspaceHoldingUpsert: vi.fn(),
    workspaceHoldingRemove: vi.fn(),
    workspaceHoldingsClear: vi.fn(),
    workspaceSavedResearch: (...args: unknown[]) => savedResearchMock(...args),
    workspaceProfile: (...args: unknown[]) => profileMock(...args),
    workspaceProfileSave: vi.fn(),
    coverageInstitutional: (...args: unknown[]) => institutionalMock(...args),
  },
}));

// Synthetic engine response — test fixture only.
function response(decision: string): AnalyseResponse {
  return {
    ok: true,
    capability: "compose_intelligence",
    api_version: "0.2.0",
    platform_version: "0.7.1",
    pipeline_version: "1.0.0",
    correlation_id: "c",
    limitations: [],
    errors: [],
    payload: {
      ok: true,
      recommendation_summary: { decision, confidence: 0.7 },
      committee_summary: { decision: "APPROVE" },
      stage_summaries: [
        { stage: "business_quality_aggregator", status: "succeeded", has_result: true, label: "High", score: 0.8 },
      ],
    },
  };
}

function session(ticker: string, decision: string, analysedAt: string): ArchivedResearchSession {
  return { ticker, exchange: "NSE", company: `${ticker} Ltd`, analysedAt, request: SAMPLE_ANALYSE_REQUEST, response: response(decision) };
}

const holding = (ticker: string, sector: string, allocationPercent: number): PortfolioHolding => ({
  company: `${ticker} Co`,
  ticker,
  sector,
  allocationPercent,
  recommendation: "Data unavailable.",
  researchAvailable: false,
});

const quote = (price: number | null, change_percent: number | null = null) => ({
  price,
  change: null,
  change_percent,
  previous_close: null,
  currency: "INR",
  provenance: null,
  available: price !== null,
});

function serverHolding(symbol: string, sector: string, qty: number, avg: number, cmp: number | null): PortfolioHoldingRow {
  const invested = qty * avg;
  const current = cmp === null ? null : qty * cmp;
  return {
    holding_id: `h-${symbol}`,
    symbol,
    exchange: "NSE",
    company_name: `${symbol} Ltd`,
    sector,
    rating: "A",
    business_quality_score: 82,
    quantity: qty,
    average_cost: avg,
    invested,
    cmp,
    current_value: current,
    pnl: current === null ? null : current - invested,
    return_pct: current === null ? null : (current - invested) / invested,
    weight: null,
    quote: quote(cmp),
    updated_at: "2026-09-01T00:00:00Z",
  };
}

function portfolioResponse(holdings: PortfolioHoldingRow[]): PortfolioResponse {
  const priced = holdings.filter((h) => h.cmp !== null);
  const complete = priced.length === holdings.length;
  const invested = holdings.reduce((a, h) => a + h.invested, 0);
  const current = complete ? holdings.reduce((a, h) => a + (h.current_value ?? 0), 0) : null;
  return {
    ok: true,
    summary: {
      holdings: holdings.length,
      priced_holdings: priced.length,
      complete,
      total_invested: invested,
      current_value: current,
      total_pnl: current === null ? null : current - invested,
      return_pct: current === null ? null : (current - invested) / invested,
      formula: {},
    },
    holdings,
    sector_allocation: complete
      ? [
          { sector: "Technology", value: 60, weight: 0.6 },
          { sector: "Financials", value: 40, weight: 0.4 },
        ]
      : [],
    message: complete ? null : "Data unavailable. One or more holdings have no authenticated price.",
  };
}

const EMPTY_PORTFOLIO = portfolioResponse([]);

const INDICES: MarketIndicesResponse = {
  ok: true,
  available: true,
  authenticated: true,
  provider_id: "test-provider",
  indices: [
    { index_id: "NIFTY50", label: "NIFTY 50", exchange: "NSE", currency: "INR", available: true, authenticated: true, value: 24831.5, change: 96.2, change_percent: 0.39, previous_close: 24735.3, sparkline: [1, 2, 3, 4], as_of: "2026-09-25T10:00:00Z", provenance: null },
    { index_id: "SENSEX", label: "SENSEX", exchange: "BSE", currency: "INR", available: false, authenticated: false, value: null, change: null, change_percent: null, previous_close: null, sparkline: [], as_of: null, provenance: null },
  ],
};

const DASHBOARD: DashboardOverviewResponse = {
  ok: true,
  watchlist: [
    { symbol: "ABC", exchange: "NSE", company_name: "ABC Ltd", sector: "IT", rating: "A+", business_quality_score: 92, rated_at: "2026-09-01T00:00:00Z", quote: quote(100, 1.5), added_at: "2026-09-01T00:00:00Z" },
  ],
  recent_research: [
    { symbol: "ABC", company_name: "ABC Ltd", rating: "A+", recommendation: "BUY", timestamp: "2026-09-01T00:00:00Z", research_id: "r1" },
  ],
  signals: [
    { signal_id: "s1", symbol: "ABC", company_name: "ABC Ltd", sector: "IT", timestamp: "2026-09-02T00:00:00Z", research_id: "r2", type: "upgrade", label: "Rating upgrade", text: "B+ → A+", from_rating: "B+", to_rating: "A+" },
    { signal_id: "s2", symbol: "DEF", company_name: null, sector: null, timestamp: "2026-09-02T00:00:00Z", research_id: null, type: "risk", label: "Risk score rose", text: "0.2 → 0.4", from_value: 0.2, to_value: 0.4 },
  ],
};

const INSTITUTIONAL: InstitutionalResponse = {
  ok: true,
  stats: { securities_covered: 2, dsp_rated: 2, a_rated: 1, a_plus_rated: 1, last_updated: "2026-09-02T00:00:00Z" },
  screener: [
    { symbol: "ABC", company_name: "ABC Ltd", rating: "A+", business_quality_score: 92, sector: "IT", pe: 27.4, roe: 0.512, revenue_growth: 0.124, price: 100, market_cap: 1e12, as_of: "2026-09-02T00:00:00Z", research_id: "r2" },
    { symbol: "DEF", company_name: null, rating: "B", business_quality_score: 61, sector: null, pe: null, roe: null, revenue_growth: null, price: null, market_cap: null, as_of: "2026-09-01T00:00:00Z", research_id: null },
  ],
  coverage_growth: [
    { month: "Aug", period: "2026-08", covered: 1, rated: 1 },
    { month: "Sep", period: "2026-09", covered: 2, rated: 2 },
  ],
  rating_distribution: [
    { rating: "A+", count: 1 },
    { rating: "A", count: 0 },
    { rating: "B+", count: 0 },
    { rating: "B", count: 1 },
    { rating: "C", count: 0 },
    { rating: "D", count: 0 },
    { rating: "F", count: 0 },
  ],
  sectors: ["IT"],
  message: null,
};

const PROFILE: ProfileResponse = {
  ok: true,
  profile: { full_name: "Ada", email: "ada@example.com", monthly_income: 150000, health_insurance: 1000000, primary_goal: "retirement", no_outstanding_debt: false, investments: [] },
  completeness: { percent: 24, filled: 5, total: 21, missing: [] },
  health: {
    version: "fhs-1.0.0",
    status: "complete",
    score: 766,
    max: 1000,
    category: "Excellent",
    components: [
      { key: "income_strength", label: "Income Strength", score: 82, max: 100, formula: "f", inputs: {}, note: "n" },
      { key: "savings_investments", label: "Savings & Investments", score: 76, max: 100, formula: "f", inputs: {}, note: "n" },
      { key: "debt_management", label: "Debt Management", score: 71, max: 100, formula: "f", inputs: {}, note: "n" },
      { key: "emergency_protection", label: "Emergency Protection", score: 80, max: 100, formula: "f", inputs: {}, note: "n" },
      { key: "goal_readiness", label: "Goal Readiness", score: 74, max: 100, formula: "f", inputs: {}, note: "n" },
    ],
    insight: "Excellent financial health (766/1000).",
    missing_inputs: [],
    completeness: { percent: 24, filled: 5, total: 21, missing: [] },
  },
};

describe("dashboardView", () => {
  it("market cards copy provider index values and stay unavailable per index otherwise", () => {
    expect(MARKET_BAR_PLACEHOLDERS).toHaveLength(4);
    for (const card of MARKET_BAR_PLACEHOLDERS) expect(card.value).toBe("Data unavailable.");
    expect(mapMarketIndices(undefined)).toEqual(MARKET_BAR_PLACEHOLDERS);
    const cards = mapMarketIndices(INDICES);
    expect(cards[0]).toMatchObject({ label: "NIFTY 50", change: "+0.39%", direction: "up", sparkline: [1, 2, 3, 4], available: true });
    expect(cards[0].value).toContain("24,831.5");
    expect(cards[1]).toMatchObject({ label: "SENSEX", value: "Data unavailable.", change: null, sparkline: [], available: false });
    expect(mapMarketIndices({ ...INDICES, indices: [], capability: "INVESTMENT_DATA_UNAVAILABLE" })).toEqual(MARKET_BAR_PLACEHOLDERS);
  });

  it("maps server watchlist, recent research and signals without derivation", () => {
    const row = mapServerWatchlistRow(DASHBOARD.watchlist[0]);
    expect(row).toMatchObject({ symbol: "ABC", origin: "watchlist", change: "+1.5%", direction: "up", rating: "A+", quoteStatus: "available" });
    expect(row.price).toContain("100");
    expect(mapServerRecentResearch(DASHBOARD.recent_research)[0]).toMatchObject({ symbol: "ABC", company: "ABC Ltd", recommendation: "A+" });
    const signals = mapSignals(DASHBOARD.signals);
    expect(signals[0]).toMatchObject({ symbol: "ABC", from: "B+", to: "A+", color: "var(--c-profit)" });
    expect(signals[1]).toMatchObject({ symbol: "DEF", from: null, color: "var(--c-risk)" });
    expect(mapSignals(undefined)).toEqual([]);
  });

  it("builds the session watchlist from session companies only, de-duplicated and capped", () => {
    const sessions = [session("ABC", "BUY", "2026-09-01T00:00:00Z")];
    const symbols = buildWatchlistSymbols(sessions, [holding("abc", "IT", 50), holding("XYZ", "IT", 50)]);
    expect(symbols.map((s) => s.symbol)).toEqual(["ABC", "XYZ"]);
    expect(symbols[0].origin).toBe("research");
    expect(symbols[1].origin).toBe("portfolio");
    expect(buildWatchlistSymbols([], [], 8)).toEqual([]);
  });

  it("uses provider change fields only and never derives change from prices", () => {
    const priceOnly = { current_price: 110, previous_close: 100 } as unknown as Parameters<typeof formatQuoteChange>[0];
    expect(formatQuoteChange(priceOnly)).toEqual({ text: "Data unavailable.", direction: null });
    expect(formatQuoteChange({ change_percent: 1.25 })).toEqual({ text: "+1.25%", direction: "up" });
    expect(formatQuoteChange({ change_percent: -0.5 })).toEqual({ text: "-0.5%", direction: "down" });
    expect(formatQuoteChange({ change: 0 })).toEqual({ text: "0", direction: "flat" });
  });

  it("maps a session watchlist row from the authenticated quote and the engine recommendation", () => {
    const sessions = [session("ABC", "BUY", "2026-09-01T00:00:00Z")];
    const row = mapWatchlistRow(
      { symbol: "ABC", name: "ABC Ltd", exchange: "NSE", origin: "research" },
      { available: true, currency: "INR", fields: { current_price: 100, change_percent: 2 } },
      "available",
      sessions,
    );
    expect(row.price).toContain("100");
    expect(row.change).toBe("+2%");
    expect(row.rating).toBe("BUY");
    expect(ratingForSymbol("NOPE", sessions)).toBe("—");
    const unavailable = mapWatchlistRow({ symbol: "ABC", name: null, exchange: null, origin: "research" }, { available: false }, "unavailable", []);
    expect(unavailable.price).toBe("Data unavailable.");
    expect(unavailable.quoteStatus).toBe("unavailable");
  });

  it("maps recent research and relative time without inventing entries", () => {
    expect(mapRecentResearch([])).toEqual([]);
    const rows = mapRecentResearch([{ ticker: "abc", company: "ABC Ltd", exchange: "NSE", recommendation: "HOLD", analysedAt: "2026-09-01T00:00:00Z" }]);
    expect(rows[0]).toMatchObject({ symbol: "ABC", company: "ABC Ltd", recommendation: "HOLD" });
    const now = new Date("2026-09-25T12:00:00Z");
    expect(relativeTime("2026-09-25T11:58:00Z", now)).toBe("2 min ago");
    expect(relativeTime("2026-09-25T09:00:00Z", now)).toBe("3 hr ago");
    expect(relativeTime("2026-09-24T09:00:00Z", now)).toBe("Yesterday");
    expect(relativeTime("not-a-date", now)).toBe("—");
  });
});

describe("portfolioView", () => {
  it("formats compact INR like the Figma summary cards", () => {
    expect(formatCompactInr(1250000)).toBe("₹12.5L");
    expect(formatCompactInr(84000, { signed: true })).toBe("+₹84.0K");
    expect(formatCompactInr(-5000)).toBe("−₹5.0K");
    expect(formatCompactInr(25000000)).toBe("₹2.50Cr");
  });

  it("copies server totals into the summary cards and keeps them unavailable when incomplete", () => {
    expect(buildPortfolioSummaryCards(EMPTY_PORTFOLIO).map((c) => c.label)).toEqual(["Current Value", "Total Invested", "Total Gain", "Returns"]);
    for (const c of buildPortfolioSummaryCards(undefined)) expect(c.value).toBe("Data unavailable.");

    const complete = buildPortfolioSummaryCards(portfolioResponse([serverHolding("ABC", "IT", 10, 100, 120)]));
    expect(complete.map((c) => c.value)).toEqual(["₹1.2K", "₹1.0K", "+₹200", "+20%"]);
    expect(complete[2].tone).toBe("profit");

    const partial = buildPortfolioSummaryCards(portfolioResponse([serverHolding("ABC", "IT", 10, 100, 120), serverHolding("DEF", "IT", 5, 50, null)]));
    expect(partial[0].value).toBe("Data unavailable.");
    expect(partial[1].value).toBe("₹1.3K");
    expect(partial[2].value).toBe("Data unavailable.");
    expect(partial[3].value).toBe("Data unavailable.");
    expect(partial[0].note).toContain("1 of 2 holdings");
  });

  it("maps a holding row from server figures only", () => {
    const row = mapHoldingRow(serverHolding("ABC", "IT", 10, 100, 120));
    expect(row).toMatchObject({ symbol: "ABC", sector: "IT", quantity: "10", pnl: "+₹200", pnlDirection: "up", returnPct: "+20%", rating: "A", priced: true });
    expect(row.cmp).toContain("120");
    const unpriced = mapHoldingRow(serverHolding("DEF", "IT", 5, 50, null));
    expect(unpriced).toMatchObject({ cmp: "Data unavailable.", pnl: "Data unavailable.", returnPct: "Data unavailable.", priced: false });
  });

  it("sorts on server values; unpriced rows sink", () => {
    const hs = [serverHolding("BBB", "IT", 1, 100, 110), serverHolding("AAA", "IT", 1, 100, 150), serverHolding("CCC", "IT", 1, 100, null)];
    expect(sortHoldings(hs, "symbol").map((h) => h.symbol)).toEqual(["AAA", "BBB", "CCC"]);
    expect(sortHoldings(hs, "value").map((h) => h.symbol)).toEqual(["AAA", "BBB", "CCC"]);
    expect(sortHoldings(hs, "gain").map((h) => h.symbol)).toEqual(["AAA", "BBB", "CCC"]);
  });

  it("builds sector slices and donut geometry from server weights only", () => {
    const slices = buildSectorSlices([
      { sector: "IT", value: 60, weight: 0.6 },
      { sector: "Banks", value: 40, weight: 0.4 },
      { sector: "Empty", value: 0, weight: 0 },
      { sector: "Unpriced", value: 0, weight: null },
    ]);
    expect(slices.map((s) => s.name)).toEqual(["IT", "Banks"]);
    expect(slices[0].percent).toBeCloseTo(60);
    const segments = donutSegments(slices);
    expect(segments).toHaveLength(2);
    expect(segments[0].path.startsWith("M")).toBe(true);
    expect(donutSegments([])).toEqual([]);
    expect(buildSectorSlices(undefined)).toEqual([]);
  });
});

describe("researchHubView", () => {
  it("builds saved research from real sessions with engine tags, newest first", () => {
    const rows = buildSavedResearch(
      [session("ABC", "BUY", "2026-09-01T00:00:00Z"), session("XYZ", "HOLD", "2026-09-05T00:00:00Z")],
      [{ ticker: "ABC", company: "ABC Ltd", exchange: "NSE", recommendation: "BUY", analysedAt: "2026-09-01T00:00:00Z" }],
    );
    expect(rows.map((r) => r.symbol)).toEqual(["XYZ", "ABC"]);
    expect(rows[1].tags).toEqual(["BUY", "Quality: High", "Committee: APPROVE"]);
    expect(rows[1].title).toBe("ABC Ltd — Company Analysis");
    expect(rows[1].origin).toBe("session");
    expect(buildSavedResearch([], [])).toEqual([]);
    expect(filterSavedResearch(rows, "xyz").map((r) => r.symbol)).toEqual(["XYZ"]);
    expect(filterSavedResearch(rows, "")).toHaveLength(2);
  });

  it("server-saved research takes precedence and carries conversation turns", () => {
    const server = mapServerSavedResearch([
      { saved_id: "s1", symbol: "abc", title: "ABC deep dive", tags: ["Valuation"], turns: 12, research_id: null, created_at: "2026-09-01T00:00:00Z", updated_at: "2026-09-10T00:00:00Z" },
    ]);
    expect(server[0]).toMatchObject({ id: "saved:s1", symbol: "ABC", turns: 12, origin: "server", tags: ["Valuation"] });
    const merged = mergeSavedResearch(server, buildSavedResearch([session("ABC", "BUY", "2026-09-02T00:00:00Z"), session("XYZ", "HOLD", "2026-09-03T00:00:00Z")], []));
    expect(merged.map((r) => `${r.symbol}:${r.origin}`)).toEqual(["ABC:server", "XYZ:session"]);
  });

  it("templates are navigation presets — no prototype tickers", () => {
    expect(RESEARCH_TEMPLATES.map((t) => t.title)).toEqual(["Full Financial Analysis", "Quick Quality Check", "Valuation Assessment", "Risk Profile", "Peer Comparison"]);
    expect(JSON.stringify(RESEARCH_TEMPLATES)).not.toMatch(/TCS|INFY|HDFC/);
  });

  it("normalises the start-research input and builds analysis links", () => {
    expect(normaliseResearchSymbol(" hdfcbank ")).toBe("HDFCBANK");
    expect(normaliseResearchSymbol("")).toBeNull();
    expect(normaliseResearchSymbol("bad symbol!")).toBeNull();
    expect(analysisHref("ABC")).toBe("/analysis?symbol=ABC");
    expect(analysisHref("ABC", "NSE")).toBe("/analysis?symbol=ABC&exchange=NSE");
  });
});

describe("clientProfileView", () => {
  it("round-trips the server profile through the form and never sends locked fields", () => {
    const form = profileToForm(PROFILE.profile);
    expect(form.values.full_name).toBe("Ada");
    expect(form.values.monthly_income).toBe("1,50,000");
    expect(form.values.health_insurance).toBe("10,00,000");
    expect(form.primaryGoal).toBe("retirement");
    const out = formToPayload({ ...form, values: { ...form.values, monthly_expenses: "₹ 32,000", age: "28" } });
    expect(out.ok).toBe(true);
    if (out.ok) {
      expect(out.payload).not.toHaveProperty("full_name");
      expect(out.payload.monthly_income).toBe(150000);
      expect(out.payload.monthly_expenses).toBe(32000);
      expect(out.payload.age).toBe(28);
      expect(out.payload.monthly_emi).toBeNull();
      expect(out.payload.primary_goal).toBe("retirement");
    }
    const bad = formToPayload({ ...form, values: { ...form.values, total_savings: "lots" } });
    expect(bad.ok).toBe(false);
    if (!bad.ok) expect(bad.errors.total_savings).toBeTruthy();
  });

  it("renders server score components only — placeholders when incomplete", () => {
    expect(scoreRows(PROFILE.health).map((r) => r.value)).toEqual([82, 76, 71, 80, 74]);
    expect(scoreRows(undefined).every((r) => r.value === null)).toBe(true);
    expect(scoreRows(undefined).map((r) => r.label)).toEqual(["Income Strength", "Savings & Investments", "Debt Management", "Emergency Protection", "Goal Readiness"]);
    expect(primaryCtaLabel(PROFILE.health)).toBe("Update Financial Profile");
    expect(primaryCtaLabel(undefined)).toBe("Calculate My Financial Health Score");
    expect(zoneColor("Excellent")).toBe("#10b981");
    expect(zoneColor(null)).toBe("var(--muted)");
    const left = gaugeNeedle(0);
    const right = gaugeNeedle(1000);
    expect(left.x).toBeLessThan(right.x);
    expect(Math.abs(left.y - right.y)).toBeLessThan(1e-6);
  });
});

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("Figma page components", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    mockHoldings = [];
    for (const m of [quoteMock, marketIndicesMock, dashboardMock, portfolioMock, institutionalMock, savedResearchMock, profileMock]) m.mockReset();
    quoteMock.mockResolvedValue({ available: true, currency: "INR", fields: { current_price: 100, change_percent: 1.5 } });
    marketIndicesMock.mockResolvedValue(INDICES);
    dashboardMock.mockResolvedValue(DASHBOARD);
    portfolioMock.mockResolvedValue(EMPTY_PORTFOLIO);
    institutionalMock.mockResolvedValue(INSTITUTIONAL);
    savedResearchMock.mockResolvedValue({ ok: true, items: [], count: 0 });
    profileMock.mockResolvedValue(PROFILE);
  });
  afterEach(() => cleanup());

  it("Dashboard renders Figma market cards, server watchlist, recent research and signals", async () => {
    const { DashboardOverview } = await import("@/components/pages/DashboardOverview");
    const { container } = wrap(<DashboardOverview />);
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeTruthy();
    expect(screen.getByText("Watchlist")).toBeTruthy();
    expect(screen.getByText("Recent Research")).toBeTruthy();
    expect(screen.getByText("DSP Signals")).toBeTruthy();
    expect(screen.getByText("NIFTY 50")).toBeTruthy();
    expect(await screen.findByText(/24,831.5/)).toBeTruthy();
    expect(screen.getByText("+0.39%")).toBeTruthy();
    const row = (await screen.findAllByText("ABC")).map((el) => el.closest("tr")).find((tr) => tr !== null)!;
    expect(within(row).getByText("+1.5%")).toBeTruthy();
    expect(within(row).getByText("A+")).toBeTruthy();
    expect(await screen.findByText(/Rating upgrade/)).toBeTruthy();
    expect(screen.getByText(/B\+ → A\+/)).toBeTruthy();
    expect(container.textContent).not.toMatch(/TCS|INFY|₹3,842/);
    expect(quoteMock).not.toHaveBeenCalled();
  });

  it("Dashboard is an honest empty state when the server has nothing", async () => {
    marketIndicesMock.mockResolvedValue({ ok: true, available: false, authenticated: false, indices: [], capability: "INVESTMENT_DATA_UNAVAILABLE" });
    dashboardMock.mockResolvedValue({ ok: true, watchlist: [], recent_research: [], signals: [] });
    const { DashboardOverview } = await import("@/components/pages/DashboardOverview");
    wrap(<DashboardOverview />);
    expect(await screen.findByText("No companies on your watchlist yet.")).toBeTruthy();
    expect(screen.getAllByText("Data unavailable.").length).toBeGreaterThanOrEqual(4);
  });

  it("Portfolio renders server-computed summary cards, Figma columns and sector donut", async () => {
    portfolioMock.mockResolvedValue(portfolioResponse([serverHolding("ABC", "Technology", 10, 100, 120), serverHolding("DEF", "Financials", 5, 200, 180)]));
    const { PortfolioHoldings } = await import("@/components/pages/PortfolioHoldings");
    const { container } = wrap(<PortfolioHoldings />);
    expect(screen.getByRole("heading", { name: "Portfolio" })).toBeTruthy();
    expect(await screen.findByText("Holdings (2)")).toBeTruthy();
    expect(screen.getByText("Sector Allocation")).toBeTruthy();
    expect(screen.getByRole("img", { name: /Sector allocation/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sort by symbol" })).toBeTruthy();
    for (const label of ["Current Value", "Total Invested", "Total Gain", "Returns"]) expect(screen.getByText(label)).toBeTruthy();
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["Symbol", "Qty", "Avg Cost", "CMP", "P&L", "Return", "DSP", ""]);
    const abc = screen.getByText("ABC").closest("tr")!;
    expect(within(abc).getByText("+₹200")).toBeTruthy();
    expect(within(abc).getByText("+20%")).toBeTruthy();
    expect(within(abc).getByText("A")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Remove ABC from portfolio" })).toBeNull();
    expect(screen.queryByRole("form", { name: "Add holding" })).toBeNull();
    expect(container.textContent).not.toMatch(/₹12,45,000|₹3,842/);
  });

  it("Portfolio empty state never seeds demo holdings", async () => {
    const { PortfolioHoldings } = await import("@/components/pages/PortfolioHoldings");
    wrap(<PortfolioHoldings />);
    expect(await screen.findByText("No holdings yet.")).toBeTruthy();
    expect(screen.getByText("Holdings (0)")).toBeTruthy();
  });

  it("Research Hub renders hero, saved research (server + session) and templates", async () => {
    savedResearchMock.mockResolvedValue({
      ok: true,
      count: 1,
      items: [{ saved_id: "s1", symbol: "XYZ", title: "XYZ valuation notes", tags: ["Valuation"], turns: 7, research_id: null, created_at: "2026-09-01T00:00:00Z", updated_at: "2026-09-10T00:00:00Z" }],
    });
    const { archiveResearchSession } = await import("@/lib/copilot/sessionArchive");
    archiveResearchSession(session("ABC", "BUY", "2026-09-01T00:00:00Z"));
    const { ResearchHub } = await import("@/components/pages/ResearchHub");
    const { container } = wrap(<ResearchHub />);
    expect(screen.getByRole("heading", { name: "Research Hub" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Start new research" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Saved Research" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Research Templates" })).toBeTruthy();
    expect(await screen.findByText("XYZ valuation notes")).toBeTruthy();
    expect(screen.getByText("7 conversation turns")).toBeTruthy();
    expect(await screen.findByText("ABC Ltd — Company Analysis")).toBeTruthy();
    expect(screen.getByText("Full Financial Analysis")).toBeTruthy();
    expect(container.textContent).not.toMatch(/TCS Full Financial Analysis|Infosys vs TCS/);
    expect(screen.getByText(/Enter a ticker above/)).toBeTruthy();
  });

  it("Institutional renders server coverage stats, screener metrics and both charts", async () => {
    const { InstitutionalResearch } = await import("@/components/pages/InstitutionalResearch");
    const { container } = wrap(<InstitutionalResearch />);
    expect(screen.getByRole("heading", { name: "Institutional Research" })).toBeTruthy();
    for (const label of ["Securities Covered", "DSP Rated", "A / A+ Rated", "Last Updated"]) expect(screen.getByText(label)).toBeTruthy();
    expect(screen.getByText("Quality Screener")).toBeTruthy();
    const headers = (await screen.findAllByRole("columnheader")).map((h) => h.textContent);
    expect(headers).toEqual(["Symbol", "DSP Rating", "Sector", "P/E", "ROE", "Rev Growth"]);
    const abc = screen.getByText("ABC").closest("tr")!;
    expect(within(abc).getByText("27.4×")).toBeTruthy();
    expect(within(abc).getByText("51.2%")).toBeTruthy();
    expect(within(abc).getByText("+12.4%")).toBeTruthy();
    const def = screen.getByText("DEF").closest("tr")!;
    expect(within(def).getAllByText("Data unavailable.").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByRole("img", { name: /Coverage growth: Aug covered 1/ })).toBeTruthy();
    expect(screen.getByRole("img", { name: /Rating distribution: A\+ 1/ })).toBeTruthy();
    for (const f of ["All", "A+", "A", "B+", "B"]) expect(screen.getByRole("button", { name: f })).toBeTruthy();
    expect(container.textContent).not.toMatch(/5,024|3,841|621/);
  });

  it("Client Profile renders Figma sections and the server Financial Health Score", async () => {
    const { ClientProfile } = await import("@/components/pages/ClientProfile");
    wrap(<ClientProfile />);
    expect(screen.getByRole("heading", { name: "Your Financial Profile" })).toBeTruthy();
    for (const title of ["Personal Information", "Monthly Cash Flow", "Savings & Investments", "Debt & Protection", "Primary Financial Goal"]) {
      expect(screen.getByRole("heading", { name: title })).toBeTruthy();
    }
    expect(await screen.findByText("Profile 24% complete")).toBeTruthy();
    expect(screen.getByText("766")).toBeTruthy();
    expect(screen.getByText("EXCELLENT")).toBeTruthy();
    expect(screen.getByText("82 / 100")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Update Financial Profile" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Save & Continue Later" })).toBeTruthy();
    expect((screen.getByLabelText(/Full Name/) as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByLabelText("Monthly Income") as HTMLInputElement).value).toBe("1,50,000");
    expect(screen.getByRole("radio", { name: /Retirement/ }).getAttribute("aria-checked")).toBe("true");
  });
});
