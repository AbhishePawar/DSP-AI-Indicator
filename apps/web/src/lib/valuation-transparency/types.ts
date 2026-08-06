/**
 * P2.3 — Institutional Valuation Transparency (presentation only).
 * Remaps existing ResearchView / ModuleRating valuation fields — never recalculates.
 */

export type ValuationMethodStatus = "Available" | "Unavailable";

export type ValuationMethodCard = {
  methodName: string;
  purpose: string;
  status: ValuationMethodStatus;
  intrinsicValue: string;
  weight: string;
  contributionToConsensus: string;
  explanation: string;
  confidence: string;
  dataCompleteness: string;
  missingInputs: string;
  assumptionsUsed: string;
  sourceField: string;
};

export type ExecutiveValuationCard = {
  overallScoreOutOf10: string;
  grade: string;
  confidence: string;
  currentMarketPrice: string;
  intrinsicValue: string;
  marginOfSafety: string;
  valuationVerdict: string;
};

export type ConsensusPanel = {
  highestValuation: string;
  lowestValuation: string;
  consensusValue: string;
  dispersionIndicator: string;
  numberOfMethodsUsed: string;
};

export type MarginOfSafetyPanel = {
  currentPrice: string;
  consensusIntrinsicValue: string;
  marginOfSafety: string;
  valuationCategory: string;
};

export type ValuationTransparencyView = {
  kind: "valuation_transparency";
  version: string;
  disclaimer: string;
  executive: ExecutiveValuationCard;
  methods: ValuationMethodCard[];
  consensus: ConsensusPanel;
  marginOfSafety: MarginOfSafetyPanel;
};
