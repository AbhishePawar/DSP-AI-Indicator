/** Analysis workspace view models — presentation only; no calculations. */

import type {
  ConfidenceLevel,
  SourceKind,
  ValueCategory,
} from "@/lib/trust/labels";

export type FieldPresence = "available" | "unavailable";

export type DisplayField<T = string> = {
  presence: FieldPresence;
  value: T | null;
  category: ValueCategory;
  source: SourceKind;
};

export type MetricView = {
  id: string;
  title: string;
  rating: string;
  actualValue: string;
  meaning: string;
  whyItMatters: string;
  investorTakeaway: string;
  learnMore: string;
  aiPrompts: string[];
  category: ValueCategory;
  source: SourceKind;
  available: boolean;
};

export type EvidenceView = {
  primaryEvidence: string[];
  supportingMetrics: string[];
  supportingEvidence: string[];
  contradictingEvidence: string[];
  source: string;
  methodology: string;
  confidence: string | null;
  aiReasoning: string | null;
  aiExplanation: string | null;
  limitations: string[];
  lastUpdated: string | null;
};

export type CompanySnapshotView = {
  companyName: DisplayField;
  ticker: DisplayField;
  industry: DisplayField;
  sector: DisplayField;
  exchange: DisplayField;
  currentMarketPrice: DisplayField;
  lastUpdated: DisplayField;
  marketCap: DisplayField;
  week52High: DisplayField;
  week52Low: DisplayField;
  researchStatus: DisplayField;
  researchDate: DisplayField;
};

export type ResearchConclusionView = {
  conclusion: DisplayField;
  intrinsicValueRange: DisplayField;
  marginOfSafety: DisplayField;
  researchHealth: DisplayField;
  researchConfidence: DisplayField<ConfidenceLevel | string>;
  investmentHorizon: DisplayField;
  suitableInvestor: DisplayField;
  primaryOpportunity: DisplayField;
  primaryRisk: DisplayField;
  evidence: EvidenceView;
};

export type ExecutiveSummaryView = {
  paragraphs: string[];
  available: boolean;
  category: ValueCategory;
  source: SourceKind;
};

export type InvestmentThesisView = {
  whyAttention: DisplayField;
  keyStrengths: DisplayField<string[]>;
  keyConcerns: DisplayField<string[]>;
  longTermThesis: DisplayField;
  thingsToMonitor: DisplayField<string[]>;
};

export type ValuationView = {
  currentPrice: DisplayField;
  intrinsicValueRange: DisplayField;
  marginOfSafety: DisplayField;
  summary: DisplayField;
  bull: DisplayField;
  base: DisplayField;
  bear: DisplayField;
};

export type DecisionDashboardView = {
  researchConclusion: DisplayField;
  businessScore: DisplayField;
  financialScore: DisplayField;
  valuationScore: DisplayField;
  riskScore: DisplayField;
  managementScore: DisplayField;
  growthScore: DisplayField;
  researchConfidence: DisplayField;
  topOpportunity: DisplayField;
  biggestRisk: DisplayField;
  nextInvestigation: DisplayField;
};

/** Sprint 2 — Growth insight card */
export type GrowthInsightView = {
  id: string;
  title: string;
  rating: string;
  meaning: string;
  whyItMatters: string;
  investorTakeaway: string;
  aiExplanation: string;
  learnMore: string;
  evidence: EvidenceView;
  category: ValueCategory;
  source: SourceKind;
  available: boolean;
};

export type RiskInsightView = {
  id: string;
  title: string;
  severity: string;
  probability: string;
  impact: string;
  reason: string;
  supportingEvidence: string[];
  mitigation: string;
  investorWatchpoints: string[];
  category: ValueCategory;
  source: SourceKind;
  available: boolean;
};

export type ManagementInsightView = {
  id: string;
  title: string;
  meaning: string;
  importance: string;
  evidence: string;
  aiInterpretation: string;
  confidence: ConfidenceLevel;
  learnMore: string;
  category: ValueCategory;
  source: SourceKind;
  available: boolean;
};

export type MoatInsightView = {
  id: string;
  title: string;
  rating: string;
  meaning: string;
  evidence: string;
  investorTakeaway: string;
  learnMore: string;
  category: ValueCategory;
  source: SourceKind;
  available: boolean;
};

export type CoverageStatus = "available" | "pending" | "unavailable";

export type CoverageBucket = {
  id: string;
  label: string;
  status: CoverageStatus;
  availableCount: number;
  totalCount: number;
};

export type ResearchCoverageView = {
  coveragePercent: number;
  evidenceStrength: string;
  availableMetrics: number;
  unavailableMetrics: number;
  breakdown: CoverageBucket[];
  futureSections: CoverageBucket[];
};

export type ResearchFreshnessView = {
  researchDate: string | null;
  lastUpdated: string | null;
  dataCurrency: string;
  analysisVersion: string;
  methodologyVersion: string;
  researchMode: string;
};

/** Sprint 3 — Market Intelligence */
export type AgreementLevel = "aligned" | "different_view" | "unavailable";

export type MarketIntelligenceView = {
  overallSentiment: DisplayField;
  coverageCount: DisplayField;
  consensusStrength: DisplayField;
  marketConfidence: DisplayField;
  researchCoverageNote: DisplayField;
  lastUpdated: DisplayField;
  dataAvailability: DisplayField;
  available: boolean;
};

export type AnalystConsensusView = {
  summary: DisplayField;
  trend: DisplayField;
  agreementLevel: DisplayField;
  coverage: DisplayField;
  confidence: DisplayField;
  bullCase: DisplayField;
  baseCase: DisplayField;
  bearCase: DisplayField;
  historicalTrend: DisplayField;
  consensusChanges: DisplayField;
  coverageQuality: DisplayField;
  available: boolean;
};

export type StreetComparisonRow = {
  id: string;
  dimension: string;
  dspResearch: DisplayField;
  marketConsensus: DisplayField;
  agreement: AgreementLevel;
  reasonForDifference: string;
  supportingEvidence: string[];
  investorInterpretation: string;
};

export type AiChallengeView = {
  conclusionLabel: string;
  supportingEvidence: string[];
  contradictingEvidence: string[];
  assumptions: AssumptionItem[];
  confidence: ConfidenceLevel;
  limitations: string[];
  researchGaps: string[];
  investorWatchpoints: string[];
  whatCouldInvalidate: string[];
  whatWouldChangeOpinion: string[];
  category: ValueCategory;
  source: SourceKind;
  available: boolean;
};

export type AssumptionItem = {
  id: string;
  statement: string;
  importance: string;
  category: ValueCategory;
};

export type ConfidenceMatrixRow = {
  id: string;
  label: string;
  level: ConfidenceLevel;
};

export type ConfidenceMatrixView = {
  rows: ConfidenceMatrixRow[];
  overall: ConfidenceLevel;
};

export type TimelineEvent = {
  id: string;
  label: string;
  at: string | null;
  status: "done" | "current" | "future" | "placeholder";
  detail: string;
};

export type ResearchTimelineView = {
  events: TimelineEvent[];
};

/** Sprint 4 — Explainability */
export type DecisionTraceStep = {
  id: string;
  title: string;
  summary: string;
  details: string[];
  category: ValueCategory;
  source: SourceKind;
};

export type DecisionTraceView = {
  conclusionLabel: string;
  inputs: DecisionTraceStep;
  calculations: DecisionTraceStep;
  businessRules: DecisionTraceStep;
  evidenceUsed: DecisionTraceStep;
  confidence: DecisionTraceStep;
  limitations: DecisionTraceStep;
  reasoningChain: DecisionTraceStep;
  output: DecisionTraceStep;
  available: boolean;
};

export type EvidenceExplorerItem = {
  id: string;
  title: string;
  group: ValueCategory;
  source: string;
  timestamp: string | null;
  confidence: string;
  methodology: string;
  detail: string;
};

export type EvidenceExplorerView = {
  items: EvidenceExplorerItem[];
};

export type AssumptionExplorerItem = {
  id: string;
  statement: string;
  sensitivity: string;
  impact: string;
  confidence: ConfidenceLevel;
  alternativeAssumptions: string[];
  whatChangesIfWrong: string;
  category: ValueCategory;
};

export type AssumptionExplorerView = {
  items: AssumptionExplorerItem[];
};

export type ReasoningFlowNode = {
  id: string;
  label: string;
  status: "complete" | "partial" | "unavailable";
  summary: string;
  details: string[];
};

export type ReasoningFlowView = {
  nodes: ReasoningFlowNode[];
};

export type ConfidenceBreakdownRow = {
  id: string;
  label: string;
  level: ConfidenceLevel;
  whyDifferent: string;
};

export type ConfidenceBreakdownView = {
  rows: ConfidenceBreakdownRow[];
  overall: ConfidenceLevel;
};

export type ResearchLimitationsView = {
  unavailableData: string[];
  unknownFactors: string[];
  assumptions: string[];
  externalDependencies: string[];
  pendingImprovements: string[];
};

export type MethodologyPanelView = {
  researchMethodology: string;
  analysisVersion: string;
  calculationVersion: string;
  presentationVersion: string;
  complianceVersion: string;
};

export type TransparencyPanelView = {
  knownUnknowns: string[];
  unavailableData: string[];
  estimatedFields: string[];
  aiGeneratedSections: string[];
  externalSources: string[];
};

/** Sprint 5 — Knowledge Graph */
export type KnowledgeGraphTab =
  | "business"
  | "financial"
  | "growth"
  | "risk"
  | "management"
  | "valuation"
  | "research";

export type KgNodeType =
  | "company"
  | "industry"
  | "sector"
  | "metric"
  | "financial_statement"
  | "business_quality"
  | "growth_driver"
  | "risk"
  | "management"
  | "competitive_advantage"
  | "valuation"
  | "research_conclusion"
  | "evidence"
  | "assumption"
  | "methodology"
  | "external_consensus";

export type KgEdgeType =
  | "supports"
  | "influences"
  | "depends_on"
  | "derived_from"
  | "conflicts_with"
  | "related_to"
  | "explains";

export type KnowledgeGraphNode = {
  id: string;
  label: string;
  nodeType: KgNodeType;
  confidence: ConfidenceLevel;
  evidenceCount: number;
  dataCategory: ValueCategory;
  lastUpdated: string | null;
  sourceCategory: SourceKind;
  description: string;
  evidence: string[];
  supportingMetrics: string[];
  relatedNodeIds: string[];
  researchSectionIds: string[];
  decisionTraceLinks: string[];
  tab: KnowledgeGraphTab;
  available: boolean;
  searchText: string;
};

export type KnowledgeGraphEdge = {
  id: string;
  from: string;
  to: string;
  edgeType: KgEdgeType;
  label: string;
};

export type KnowledgeGraphEmptyState = {
  whyIncomplete: string;
  missingEvidence: string[];
  futureEnrichment: string[];
};

export type KnowledgeGraphView = {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  emptyState: KnowledgeGraphEmptyState;
  version: string;
};

export type AnalysisWorkspaceView = {
  reportId: string | null;
  apiOk: boolean;
  limitations: string[];
  errors: string[];
  capability: string | null;
  platformVersion: string | null;
  rawResult: unknown;
  snapshot: CompanySnapshotView;
  conclusion: ResearchConclusionView;
  executiveSummary: ExecutiveSummaryView;
  thesis: InvestmentThesisView;
  businessQuality: MetricView[];
  financialStrength: MetricView[];
  valuation: ValuationView;
  growth: GrowthInsightView[];
  risks: RiskInsightView[];
  management: ManagementInsightView[];
  moat: MoatInsightView[];
  marketIntelligence: MarketIntelligenceView;
  analystConsensus: AnalystConsensusView;
  streetComparison: StreetComparisonRow[];
  aiChallenge: AiChallengeView;
  confidenceMatrix: ConfidenceMatrixView;
  researchTimeline: ResearchTimelineView;
  decisionTrace: DecisionTraceView;
  evidenceExplorer: EvidenceExplorerView;
  assumptionExplorer: AssumptionExplorerView;
  reasoningFlow: ReasoningFlowView;
  confidenceBreakdown: ConfidenceBreakdownView;
  researchLimitations: ResearchLimitationsView;
  methodologyPanel: MethodologyPanelView;
  transparencyPanel: TransparencyPanelView;
  knowledgeGraph: KnowledgeGraphView;
  dashboard: DecisionDashboardView;
  coverage: ResearchCoverageView;
  freshness: ResearchFreshnessView;
};

/** Full workspace TOC — Sprints 1–8 (Decision Dashboard last). */
export const WORKSPACE_SECTIONS = [
  { id: "company_snapshot", title: "Company Snapshot" },
  { id: "research_conclusion", title: "Research Conclusion" },
  { id: "executive_summary", title: "Executive Summary" },
  { id: "investment_thesis", title: "Investment Thesis" },
  { id: "business_quality", title: "Business Quality" },
  { id: "financial_strength", title: "Financial Strength" },
  { id: "valuation", title: "Valuation" },
  { id: "growth", title: "Growth Analysis" },
  { id: "risk", title: "Risk Analysis" },
  { id: "management", title: "Management Quality" },
  { id: "competitive_advantage", title: "Competitive Advantage" },
  { id: "market_intelligence", title: "Market Intelligence" },
  { id: "analyst_consensus", title: "Analyst Consensus" },
  { id: "dsp_vs_street", title: "DSP vs Street" },
  { id: "ai_challenge", title: "AI Challenge Mode" },
  { id: "decision_trace", title: "Decision Trace" },
  { id: "evidence_explorer", title: "Evidence Explorer" },
  { id: "assumption_explorer", title: "Assumption Explorer" },
  { id: "reasoning_flow", title: "Reasoning Flow" },
  { id: "confidence_breakdown", title: "Confidence Breakdown" },
  { id: "research_limitations", title: "Research Limitations" },
  { id: "knowledge_graph", title: "Knowledge Graph" },
  { id: "report_center", title: "Reports & Export" },
  { id: "saved_workspace", title: "Workspace" },
  { id: "decision_dashboard", title: "Decision Dashboard" },
] as const;

/** @deprecated use WORKSPACE_SECTIONS */
export const SPRINT1_SECTIONS = WORKSPACE_SECTIONS;
