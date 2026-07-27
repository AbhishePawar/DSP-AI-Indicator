import type {
  AllocationSegment,
  PortfolioActivity,
  PortfolioHolding,
  PortfolioSummary,
  PortfolioView,
  AddHoldingInput,
} from "./model";

export const DEMO_HOLDINGS: PortfolioHolding[] = [
  {
    company: "Apple",
    ticker: "AAPL",
    sector: "Technology",
    allocationPercent: 18,
    recommendation: "Hold",
    researchAvailable: true,
  },
  {
    company: "Microsoft",
    ticker: "MSFT",
    sector: "Technology",
    allocationPercent: 16,
    recommendation: "Buy",
    researchAvailable: true,
  },
  {
    company: "TCS",
    ticker: "TCS",
    sector: "Technology",
    allocationPercent: 14,
    recommendation: "Buy",
    researchAvailable: true,
  },
  {
    company: "HDFC Bank",
    ticker: "HDFCBANK",
    sector: "Financials",
    allocationPercent: 12,
    recommendation: "Hold",
    researchAvailable: true,
  },
  {
    company: "Nestle India",
    ticker: "NESTLEIND",
    sector: "Consumer Staples",
    allocationPercent: 10,
    recommendation: "Hold",
    researchAvailable: true,
  },
  {
    company: "NVIDIA",
    ticker: "NVDA",
    sector: "Technology",
    allocationPercent: 8,
    recommendation: "Buy",
    researchAvailable: true,
  },
];

export const DEMO_ACTIVITIES: PortfolioActivity[] = [
  {
    id: "act-1",
    label: "Added Apple",
    timestamp: "2026-07-26T10:30:00.000Z",
  },
  {
    id: "act-2",
    label: "Opened TCS Research",
    timestamp: "2026-07-25T14:15:00.000Z",
  },
  {
    id: "act-3",
    label: "Viewed Microsoft",
    timestamp: "2026-07-24T09:00:00.000Z",
  },
  {
    id: "act-4",
    label: "Portfolio Created",
    timestamp: "2026-07-20T08:00:00.000Z",
  },
];

function groupAllocation(
  holdings: PortfolioHolding[],
  key: (holding: PortfolioHolding) => string,
): AllocationSegment[] {
  const totals = new Map<string, number>();
  for (const holding of holdings) {
    const label = key(holding);
    totals.set(label, (totals.get(label) ?? 0) + holding.allocationPercent);
  }
  return Array.from(totals.entries())
    .map(([name, percent]) => ({ name, percent }))
    .sort((a, b) => b.percent - a.percent);
}

function deriveMarketCapSegment(ticker: string): string {
  const largeCap = new Set([
    "AAPL",
    "MSFT",
    "TCS",
    "HDFCBANK",
    "NESTLEIND",
    "NVDA",
    "GOOGL",
    "AMZN",
  ]);
  return largeCap.has(ticker) ? "Large Cap" : "Mid Cap";
}

function deriveGeography(exchange: string): string {
  if (exchange === "NSE") return "India";
  if (exchange === "NASDAQ" || exchange === "NYSE") return "United States";
  return "Other";
}

function exchangeForTicker(ticker: string): string {
  const nse = new Set([
    "TCS",
    "HDFCBANK",
    "NESTLEIND",
    "INFY",
    "RELIANCE",
    "ICICIBANK",
  ]);
  return nse.has(ticker) ? "NSE" : "NASDAQ";
}

/** Rebalance allocations equally across holdings (presentation only). */
export function rebalanceHoldings(
  holdings: PortfolioHolding[],
): PortfolioHolding[] {
  if (holdings.length === 0) return [];
  const share = Number((100 / holdings.length).toFixed(1));
  const allocated = share * holdings.length;
  const remainder = Number((100 - allocated).toFixed(1));
  return holdings.map((holding, index) => ({
    ...holding,
    allocationPercent:
      index === 0 ? Number((share + remainder).toFixed(1)) : share,
  }));
}

export function buildPortfolioSummary(
  holdings: PortfolioHolding[],
  cashAllocation = "12%",
): PortfolioSummary {
  const buyCount = holdings.filter((h) => h.recommendation === "Buy").length;
  const holdCount = holdings.filter((h) => h.recommendation === "Hold").length;
  const researchCount = holdings.filter((h) => h.researchAvailable).length;
  const sectorCount = new Set(holdings.map((h) => h.sector)).size;

  let recommendation = "—";
  if (buyCount > holdCount) recommendation = "Buy";
  else if (holdCount > buyCount) recommendation = "Hold";
  else if (holdings.length > 0) recommendation = "Mixed";

  const researchCoverage =
    holdings.length > 0
      ? `${researchCount}/${holdings.length} (${Math.round(
          (researchCount / holdings.length) * 100,
        )}%)`
      : "—";

  let portfolioStatus = "Empty";
  if (holdings.length > 0) {
    portfolioStatus =
      researchCount === holdings.length ? "Active · Covered" : "Active";
  }

  return {
    totalHoldings: holdings.length,
    sectorCount,
    researchCoverage,
    portfolioStatus,
    portfolioValue: holdings.length > 0 ? "₹12,45,000" : "—",
    cashAllocation: holdings.length > 0 ? cashAllocation : "—",
    // Company quality scores come from /api/v1/analyse — never invented here.
    averageQualityScore: "Unavailable",
    averageRecommendation: recommendation,
  };
}

export function buildAllocations(holdings: PortfolioHolding[]) {
  return {
    bySector: groupAllocation(holdings, (h) => h.sector),
    byMarketCap: groupAllocation(holdings, (h) =>
      deriveMarketCapSegment(h.ticker),
    ),
    byGeography: groupAllocation(holdings, (h) =>
      deriveGeography(exchangeForTicker(h.ticker)),
    ),
  };
}

export function createActivity(label: string): PortfolioActivity {
  return {
    id: `act-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    label,
    timestamp: new Date().toISOString(),
  };
}

export function buildPortfolioView(
  holdings: PortfolioHolding[],
  activities: PortfolioActivity[],
): PortfolioView {
  const balanced = rebalanceHoldings(holdings);
  return {
    summary: buildPortfolioSummary(balanced),
    holdings: balanced,
    allocations: buildAllocations(balanced),
    activities,
  };
}

export function holdingFromInput(input: AddHoldingInput): PortfolioHolding {
  return {
    company: input.company,
    ticker: input.ticker.trim().toUpperCase(),
    sector: input.sector || "Unknown",
    allocationPercent: 0,
    recommendation: input.recommendation ?? "Hold",
    researchAvailable: input.researchAvailable ?? true,
  };
}

export function getDemoPortfolio(): PortfolioView {
  return buildPortfolioView(DEMO_HOLDINGS, DEMO_ACTIVITIES);
}

export function getEmptyPortfolio(): PortfolioView {
  return buildPortfolioView([], [
    createActivity("Portfolio Created"),
  ]);
}

export function isPortfolioEmpty(view: PortfolioView): boolean {
  return view.holdings.length === 0;
}

export function hasHolding(
  holdings: PortfolioHolding[],
  ticker: string,
): boolean {
  const normalized = ticker.trim().toUpperCase();
  return holdings.some((h) => h.ticker.toUpperCase() === normalized);
}

/** Pure add — returns null when ticker already present (duplicate prevention). */
export function addHoldingToView(
  view: PortfolioView,
  input: AddHoldingInput,
): PortfolioView | null {
  if (hasHolding(view.holdings, input.ticker)) return null;
  const nextHoldings = [...view.holdings, holdingFromInput(input)];
  const activities = [
    createActivity(`Added ${input.company}`),
    ...view.activities,
  ];
  return buildPortfolioView(nextHoldings, activities);
}

/** Pure remove — returns null when ticker is not present. */
export function removeHoldingFromView(
  view: PortfolioView,
  ticker: string,
): PortfolioView | null {
  const normalized = ticker.trim().toUpperCase();
  const target = view.holdings.find(
    (h) => h.ticker.toUpperCase() === normalized,
  );
  if (!target) return null;
  const nextHoldings = view.holdings.filter(
    (h) => h.ticker.toUpperCase() !== normalized,
  );
  const activities = [
    createActivity(`Removed ${target.company}`),
    ...view.activities,
  ];
  return buildPortfolioView(nextHoldings, activities);
}
