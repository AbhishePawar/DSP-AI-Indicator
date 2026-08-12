/** Shared Copilot types — presentation / explainability only. No LLM. */

export type CopilotRole = "user" | "assistant" | "system";

export type ResearchCitationId =
  | "Valuation"
  | "Economic Moat"
  | "Management Quality"
  | "Financial Strength"
  | "Earnings Quality"
  | "Growth Quality"
  | "Investment Committee"
  | "Recommendation"
  | "Overview";

export type CopilotSourceRef = {
  engine?: string;
  detail?: string | null;
  note?: string | null;
};

export type CopilotMessage = {
  id: string;
  role: CopilotRole;
  content: string;
  createdAt: string;
  citations?: ResearchCitationId[];
  /** RC1 M7 — engine source references from Copilot 2.0 */
  sources?: CopilotSourceRef[];
  markdown?: boolean;
};

export type ConversationContextState = {
  lastIntent: CopilotIntent | null;
  lastTicker: string | null;
};

export type CopilotConversation = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: CopilotMessage[];
  context: ConversationContextState;
};

export type CopilotIntent =
  | "explain_valuation"
  | "explain_recommendation"
  | "explain_moat"
  | "explain_management"
  | "summarise_strengths"
  | "summarise_weaknesses"
  | "explain_committee"
  | "explain_financial_strength"
  | "explain_earnings_quality"
  | "explain_growth_quality"
  | "explain_margin_of_safety"
  | "compare_companies"
  | "explain_risk"
  | "analyze_portfolio"
  | "document_qa"
  | "investment_memo"
  | "buffett"
  | "unknown";

/** Legacy suggested question ids mapped onto CopilotIntent. */
export type SuggestedQuestionId =
  | "why_buy"
  | "explain_valuation"
  | "explain_moat"
  | "summarise_strengths"
  | "summarise_risks"
  | "explain_committee"
  | "explain_management"
  | "explain_financial_strength"
  | "explain_earnings_quality"
  | "explain_growth_quality"
  | "explain_margin_of_safety"
  | "compare_companies"
  | "explain_risk"
  | "analyze_portfolio"
  | "document_qa"
  | "investment_memo"
  | "buffett";

export type SuggestedQuestion = {
  id: SuggestedQuestionId;
  label: string;
  intent: CopilotIntent;
};

export type StageFieldSummary = {
  status: string | null;
  label: string | null;
  decision: string | null;
  score: number | null;
  confidence: number | null;
  available: boolean;
};

export type CopilotCompanyContext = {
  company: string;
  ticker: string;
  exchange: string | null;
  recommendation: string;
  recommendationConfidence: number | null;
  intrinsicValue: number | null;
  currentPrice: number | null;
  marginOfSafety: number | null;
  economicMoat: StageFieldSummary;
  managementQuality: StageFieldSummary;
  financialStrength: StageFieldSummary;
  earningsQuality: StageFieldSummary;
  growthQuality: StageFieldSummary;
  businessQualityLabel: string;
  businessQualityScore: number | null;
  committeeDecision: string;
  committeeConfidence: number | null;
  committeeConsensus: string | null;
  strengths: string[];
  weaknesses: string[];
  risks: string[];
  minorityNotes: string[];
  hasSession: boolean;
};

export type CopilotComposedAnswer = {
  content: string;
  citations: ResearchCitationId[];
  intent: CopilotIntent;
  unavailable: boolean;
};

export type CopilotResearchContext = {
  ticker: string | null;
  company: string | null;
  exchange: string | null;
  hasSession: boolean;
  comparableTickers: string[];
  canCompare: boolean;
};
