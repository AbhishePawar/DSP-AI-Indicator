/** EPIC-005C — Portfolio analytics view-model (presentation calculations only). */

import type { AllocationSegment, PortfolioHolding } from "./model";

export type RecommendationBucket =
  | "Strong Buy"
  | "Buy"
  | "Hold"
  | "Sell"
  | "Strong Sell";

export type RecommendationDistribution = Record<RecommendationBucket, number>;

export type PortfolioQualityAnalytics = {
  averageQualityScore: string;
  averageRecommendation: string;
  companiesWithResearch: number;
  portfolioStatus: string;
};

export type ResearchCoverageAnalytics = {
  companiesAnalysed: number;
  researchAvailable: number;
  researchMissing: number;
  coveragePercent: number;
  coverageLabel: string;
};

export type DiversificationAnalytics = {
  sectorCount: number;
  exchangeCount: number;
  countryCount: number;
  largestSector: string;
  largestSectorPercent: number;
};

export type PortfolioHealthAnalytics = {
  labels: string[];
  primary: string;
  details: string;
};

export type PortfolioAnalyticsView = {
  quality: PortfolioQualityAnalytics;
  sectorAllocation: AllocationSegment[];
  recommendations: RecommendationDistribution;
  researchCoverage: ResearchCoverageAnalytics;
  diversification: DiversificationAnalytics;
  health: PortfolioHealthAnalytics;
};

const SECTOR_BUCKETS = [
  "Technology",
  "Financials",
  "Consumer",
  "Healthcare",
  "Industrials",
  "Others",
] as const;

const RECOMMENDATION_BUCKETS: RecommendationBucket[] = [
  "Strong Buy",
  "Buy",
  "Hold",
  "Sell",
  "Strong Sell",
];

function exchangeForTicker(ticker: string): string {
  const nse = new Set([
    "TCS",
    "HDFCBANK",
    "NESTLEIND",
    "INFY",
    "RELIANCE",
    "ICICIBANK",
    "ASIANPAINT",
    "TITAN",
    "HINDUNILVR",
  ]);
  return nse.has(ticker.toUpperCase()) ? "NSE" : "NASDAQ";
}

function countryForExchange(exchange: string): string {
  if (exchange === "NSE") return "India";
  if (exchange === "NASDAQ" || exchange === "NYSE") return "United States";
  return "Other";
}

function normalizeSectorBucket(sector: string): (typeof SECTOR_BUCKETS)[number] {
  const s = sector.toLowerCase();
  if (s.includes("tech") || s.includes("information")) return "Technology";
  if (s.includes("financ") || s.includes("bank")) return "Financials";
  if (s.includes("consumer") || s.includes("staples") || s.includes("discretionary")) {
    return "Consumer";
  }
  if (s.includes("health")) return "Healthcare";
  if (s.includes("industrial")) return "Industrials";
  return "Others";
}

export function normalizeRecommendation(
  recommendation: string,
): RecommendationBucket {
  const r = recommendation.trim().toLowerCase();
  if (r.includes("strong buy") || r === "strong_buy") return "Strong Buy";
  if (r.includes("strong sell") || r === "strong_sell") return "Strong Sell";
  if (r.includes("buy") || r.includes("approve")) return "Buy";
  if (r.includes("sell")) return "Sell";
  return "Hold";
}

export function buildSectorAllocationBuckets(
  holdings: PortfolioHolding[],
): AllocationSegment[] {
  const totals = new Map<string, number>();
  for (const bucket of SECTOR_BUCKETS) totals.set(bucket, 0);
  for (const holding of holdings) {
    const bucket = normalizeSectorBucket(holding.sector);
    totals.set(
      bucket,
      (totals.get(bucket) ?? 0) + holding.allocationPercent,
    );
  }
  return SECTOR_BUCKETS.map((name) => ({
    name,
    percent: Number((totals.get(name) ?? 0).toFixed(1)),
  }));
}

export function buildRecommendationDistribution(
  holdings: PortfolioHolding[],
): RecommendationDistribution {
  const counts: RecommendationDistribution = {
    "Strong Buy": 0,
    Buy: 0,
    Hold: 0,
    Sell: 0,
    "Strong Sell": 0,
  };
  for (const holding of holdings) {
    const bucket = normalizeRecommendation(holding.recommendation);
    counts[bucket] += 1;
  }
  return counts;
}

export function buildResearchCoverageAnalytics(
  holdings: PortfolioHolding[],
): ResearchCoverageAnalytics {
  const researchAvailable = holdings.filter((h) => h.researchAvailable).length;
  const researchMissing = holdings.length - researchAvailable;
  const coveragePercent =
    holdings.length > 0
      ? Math.round((researchAvailable / holdings.length) * 100)
      : 0;
  return {
    companiesAnalysed: holdings.length,
    researchAvailable,
    researchMissing,
    coveragePercent,
    coverageLabel:
      holdings.length > 0
        ? `${researchAvailable}/${holdings.length} (${coveragePercent}%)`
        : "—",
  };
}

export function buildDiversificationAnalytics(
  holdings: PortfolioHolding[],
): DiversificationAnalytics {
  const sectors = new Set(holdings.map((h) => h.sector));
  const exchanges = new Set(
    holdings.map((h) => exchangeForTicker(h.ticker)),
  );
  const countries = new Set(
    [...exchanges].map((exchange) => countryForExchange(exchange)),
  );

  const sectorWeights = new Map<string, number>();
  for (const holding of holdings) {
    sectorWeights.set(
      holding.sector,
      (sectorWeights.get(holding.sector) ?? 0) + holding.allocationPercent,
    );
  }
  const sorted = [...sectorWeights.entries()].sort((a, b) => b[1] - a[1]);
  const largest = sorted[0];

  return {
    sectorCount: sectors.size,
    exchangeCount: exchanges.size,
    countryCount: countries.size,
    largestSector: largest?.[0] ?? "—",
    largestSectorPercent: largest ? Number(largest[1].toFixed(1)) : 0,
  };
}

export function buildPortfolioQualityAnalytics(
  holdings: PortfolioHolding[],
): PortfolioQualityAnalytics {
  const research = buildResearchCoverageAnalytics(holdings);
  const distribution = buildRecommendationDistribution(holdings);

  let averageRecommendation = "—";
  if (holdings.length > 0) {
    averageRecommendation = RECOMMENDATION_BUCKETS.reduce((best, bucket) =>
      distribution[bucket] > distribution[best] ? bucket : best,
    );
  }

  let portfolioStatus = "Empty";
  if (holdings.length > 0) {
    portfolioStatus =
      research.researchMissing === 0 ? "Active · Covered" : "Active";
  }

  return {
    // Quality scores must come from backend /analyse stage summaries —
    // never invent a numeric quality score from research coverage.
    averageQualityScore: "Unavailable",
    averageRecommendation,
    companiesWithResearch: research.researchAvailable,
    portfolioStatus,
  };
}

/**
 * Deterministic health labels from holdings only — no market data.
 * Rules:
 * - Empty when no holdings
 * - Concentrated when one sector > 50% or only one sector
 * - Well Diversified when ≥3 sectors and largest ≤ 50%
 * - Research Complete / Incomplete from coverage
 */
export function buildPortfolioHealthAnalytics(
  holdings: PortfolioHolding[],
): PortfolioHealthAnalytics {
  if (holdings.length === 0) {
    return {
      labels: ["Empty"],
      primary: "Empty",
      details: "Add holdings to generate portfolio health signals.",
    };
  }

  const diversification = buildDiversificationAnalytics(holdings);
  const research = buildResearchCoverageAnalytics(holdings);
  const labels: string[] = [];

  if (
    diversification.sectorCount === 1 ||
    diversification.largestSectorPercent > 50
  ) {
    labels.push("Concentrated");
  } else if (
    diversification.sectorCount >= 3 &&
    diversification.largestSectorPercent <= 50
  ) {
    labels.push("Well Diversified");
  } else {
    labels.push("Moderately Diversified");
  }

  if (research.researchMissing === 0) {
    labels.push("Research Complete");
  } else {
    labels.push("Research Incomplete");
  }

  return {
    labels,
    primary: labels[0] ?? "Active",
    details: `Largest sector ${diversification.largestSector} at ${diversification.largestSectorPercent}%. Research coverage ${research.coveragePercent}%.`,
  };
}

export function buildPortfolioAnalytics(
  holdings: PortfolioHolding[],
): PortfolioAnalyticsView {
  return {
    quality: buildPortfolioQualityAnalytics(holdings),
    sectorAllocation: buildSectorAllocationBuckets(holdings),
    recommendations: buildRecommendationDistribution(holdings),
    researchCoverage: buildResearchCoverageAnalytics(holdings),
    diversification: buildDiversificationAnalytics(holdings),
    health: buildPortfolioHealthAnalytics(holdings),
  };
}
