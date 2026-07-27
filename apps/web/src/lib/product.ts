/** Product identity & analysis IA (PR1.0) — presentation constants only. */

export const PRODUCT = {
  name: "DSP AI Indicator",
  primaryTagline: "Complex Analysis. Simple Decisions.",
  secondaryTagline: "Professional Investment Research for Everyone.",
  mission:
    "Help investors understand businesses before making investment decisions.",
  philosophy:
    "Explainable AI Investment Research Platform — not a stock tip service.",
} as const;

/** Design principle — every screen must answer these. */
export const SCREEN_QUESTIONS = [
  "What is happening?",
  "Why is it happening?",
  "Why should I care?",
  "What should I do next?",
] as const;

/** Canonical Company Analysis page order (PR1.1 PXB). Sprint 1 implements a subset. */
export const ANALYSIS_PAGE_ORDER = [
  { id: "company_snapshot", title: "Company Snapshot" },
  { id: "research_conclusion", title: "Research Conclusion" },
  { id: "executive_summary", title: "Executive Summary" },
  { id: "investment_thesis", title: "Investment Thesis" },
  { id: "business_quality", title: "Business Quality" },
  { id: "financial_strength", title: "Financial Strength" },
  { id: "growth", title: "Growth" },
  { id: "valuation", title: "Valuation" },
  { id: "risk_analysis", title: "Risk" },
  { id: "management", title: "Management" },
  { id: "competitive_advantage", title: "Competitive Advantage" },
  { id: "market_consensus", title: "Market Analyst Consensus" },
  { id: "dsp_vs_street", title: "DSP vs Street" },
  { id: "ai_challenge", title: "AI Challenge Mode" },
  { id: "knowledge_graph", title: "Knowledge Graph" },
  { id: "ai_copilot", title: "AI Copilot" },
  { id: "decision_dashboard", title: "Decision Dashboard" },
  { id: "evidence", title: "Evidence" },
  { id: "export", title: "Export" },
] as const;

export const RESEARCH_DISCLAIMER =
  "DSP provides investment research and decision support. In Research Mode it does not issue Buy, Sell, or Hold recommendations. You remain responsible for your own investment decisions.";
