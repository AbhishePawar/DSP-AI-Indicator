/** EPIC-005A/B — Portfolio view-model (presentation only). */

export type PortfolioHolding = {
  company: string;
  ticker: string;
  sector: string;
  allocationPercent: number;
  recommendation: string;
  researchAvailable: boolean;
};

export type PortfolioActivity = {
  id: string;
  label: string;
  timestamp: string;
};

export type AllocationSegment = {
  name: string;
  percent: number;
};

export type PortfolioSummary = {
  totalHoldings: number;
  sectorCount: number;
  researchCoverage: string;
  portfolioStatus: string;
  /** Placeholder presentation fields retained for foundation cards. */
  portfolioValue: string;
  cashAllocation: string;
  averageQualityScore: string;
  averageRecommendation: string;
};

export type PortfolioView = {
  summary: PortfolioSummary;
  holdings: PortfolioHolding[];
  allocations: {
    bySector: AllocationSegment[];
    byMarketCap: AllocationSegment[];
    byGeography: AllocationSegment[];
  };
  activities: PortfolioActivity[];
};

export type AddHoldingInput = {
  company: string;
  ticker: string;
  sector: string;
  recommendation?: string;
  researchAvailable?: boolean;
};
