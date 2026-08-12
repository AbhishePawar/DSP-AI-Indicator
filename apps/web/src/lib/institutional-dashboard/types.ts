/** Institutional Research Dashboard view models — presentation only (EPIC-W001). */

import type {
  ConfidenceLevel,
  SourceKind,
  ValueCategory,
} from "@/lib/trust/labels";

export const DATA_UNAVAILABLE = "Data unavailable.";
export const UNABLE_TO_CALCULATE = "Unable to calculate.";

export type FieldPresence = "available" | "unavailable" | "unable_to_calculate";

export type DashboardField<T = string> = {
  presence: FieldPresence;
  value: T | null;
  category: ValueCategory;
  source: SourceKind;
  /** Human display — never invent; use DATA_UNAVAILABLE / UNABLE_TO_CALCULATE. */
  display: string;
};

export type ExplainabilityBlock = {
  formula: DashboardField;
  inputs: DashboardField<string[]>;
  weights: DashboardField;
  calculation: DashboardField;
  engines: DashboardField<string[]>;
  confidence: DashboardField;
  supportingData: DashboardField<string[]>;
  reasoning: DashboardField;
  contribution: DashboardField;
};

export type ScoreCard = {
  id: string;
  title: string;
  score: DashboardField;
  label: DashboardField;
  explainability: ExplainabilityBlock;
};

export type ExecutiveHeaderView = {
  companyName: DashboardField;
  ticker: DashboardField;
  exchange: DashboardField;
  sector: DashboardField;
  industry: DashboardField;
  currentMarketPrice: DashboardField;
  intrinsicValue: DashboardField;
  marginOfSafety: DashboardField;
  fairValueRange: DashboardField;
  expectedCagr: DashboardField;
  overallScore: DashboardField;
  confidence: DashboardField;
  researchStatus: DashboardField;
  recommendation: DashboardField;
  reportTimestamp: DashboardField;
  researchVersion: DashboardField;
  engineVersion: DashboardField;
  researchMode: DashboardField;
  reportVersion: DashboardField;
};

export type MarketDataView = {
  currentPrice: DashboardField;
  open: DashboardField;
  high: DashboardField;
  low: DashboardField;
  previousClose: DashboardField;
  week52High: DashboardField;
  week52Low: DashboardField;
  volume: DashboardField;
  averageVolume: DashboardField;
  marketCap: DashboardField;
  enterpriseValue: DashboardField;
  dividendYield: DashboardField;
  sharesOutstanding: DashboardField;
  beta: DashboardField;
  timestamp: DashboardField;
  source: DashboardField;
  /** True only when at least one authenticated market feed field is present. */
  hasAuthenticatedMarketData: boolean;
};

export type StatementLine = { label: string; field: DashboardField };

export type FinancialStatementsView = {
  reportingPeriod: DashboardField;
  source: DashboardField;
  incomeStatement: StatementLine[];
  balanceSheet: StatementLine[];
  cashFlow: StatementLine[];
  growthRates: StatementLine[];
  margins: StatementLine[];
  capitalAllocation: StatementLine[];
  ratios: StatementLine[];
  historicalTrends: StatementLine[];
};

export type ValuationMethodCard = {
  id: string;
  title: string;
  value: DashboardField;
};

export type ValuationView = {
  intrinsicValue: DashboardField;
  fairValue: DashboardField;
  fairValueRange: DashboardField;
  methods: ValuationMethodCard[];
  methodContributions: DashboardField;
  sensitivity: DashboardField;
  assumptions: DashboardField<string[]>;
  engineVersion: DashboardField;
};

export type MarginOfSafetyView = {
  currentPrice: DashboardField;
  intrinsicValue: DashboardField;
  marginOfSafety: DashboardField;
  upsidePotential: DashboardField;
  downsideRisk: DashboardField;
  riskReward: DashboardField;
  valuationStatus: DashboardField;
};

export type BusinessQualityView = {
  overall: ScoreCard;
  moat: ScoreCard;
  management: ScoreCard;
  governance: ScoreCard;
  capitalAllocation: ScoreCard;
  financialStrength: ScoreCard;
  predictability: ScoreCard;
  competitivePosition: ScoreCard;
  longTermOutlook: ScoreCard;
};

export type RiskView = {
  business: ScoreCard;
  financial: ScoreCard;
  industry: ScoreCard;
  macro: ScoreCard;
  regulatory: ScoreCard;
  execution: ScoreCard;
  riskRating: DashboardField;
  keyAssumptions: DashboardField<string[]>;
};

export type ScenarioCase = {
  id: string;
  title: string;
  narrative: DashboardField;
  cagr: DashboardField;
  probability: DashboardField;
};

export type ScenarioView = {
  bull: ScenarioCase;
  base: ScenarioCase;
  bear: ScenarioCase;
  expectedCagr: DashboardField;
  sensitivity: DashboardField;
  keyDrivers: DashboardField<string[]>;
};

export type AuditView = {
  reportId: DashboardField;
  auditReference: DashboardField;
  generationTimestamp: DashboardField;
  marketDataTimestamp: DashboardField;
  financialStatementPeriod: DashboardField;
  engineVersion: DashboardField;
  researchVersion: DashboardField;
  rulesVersion: DashboardField;
  dataSources: DashboardField<string[]>;
  calculationMetadata: DashboardField;
  correlationId: DashboardField;
  packageVersions: DashboardField<string[]>;
};

export type CorporateActionEventView = {
  actionType: DashboardField;
  description: DashboardField;
  effectiveDate: DashboardField;
  exDate: DashboardField;
  recordDate: DashboardField;
  paymentDate: DashboardField;
  amount: DashboardField;
  ratio: DashboardField;
};

export type CorporateActionsView = {
  source: DashboardField;
  events: CorporateActionEventView[];
  hasAuthenticatedCorporateActions: boolean;
};

export type HistoricalBarView = {
  date: DashboardField;
  open: DashboardField;
  high: DashboardField;
  low: DashboardField;
  close: DashboardField;
  volume: DashboardField;
};

export type HistoricalSeriesView = {
  source: DashboardField;
  seriesKind: DashboardField;
  frequency: DashboardField;
  dateRange: DashboardField;
  bars: HistoricalBarView[];
  pointCount: DashboardField;
  snapshotCount: DashboardField;
  hasAuthenticatedHistoricalSeries: boolean;
};

export type RsValidationResult = {
  standard: string;
  ok: boolean;
  detail: string;
};

export type InstitutionalDashboardView = {
  executive: ExecutiveHeaderView;
  market: MarketDataView;
  financial: FinancialStatementsView;
  corporateActions: CorporateActionsView;
  historical: HistoricalSeriesView;
  valuation: ValuationView;
  marginOfSafety: MarginOfSafetyView;
  businessQuality: BusinessQualityView;
  risk: RiskView;
  scenarios: ScenarioView;
  /** Flattened explainability index for RS-009 panel. */
  explainabilityScores: ScoreCard[];
  audit: AuditView;
  rsValidation: RsValidationResult[];
  researchMode: boolean;
  ticker: string;
  confidenceLevel: ConfidenceLevel | null;
};
