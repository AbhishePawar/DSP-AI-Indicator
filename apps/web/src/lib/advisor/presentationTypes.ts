/**
 * Sprint 5 — Advisor Presentation packs (session-only, presentation layer).
 */

export type PresentationId = string;
export type PresentationSectionId =
  | "executive_summary"
  | "investment_objectives"
  | "client_profile"
  | "research_summary"
  | "model_portfolio"
  | "portfolio_allocation"
  | "top_opportunities"
  | "risk_review"
  | "research_timeline"
  | "advisor_notes"
  | "disclosures";

export type PresentationLifecycle = "active" | "archived";

export type PreviewMode = "desktop" | "tablet" | "print" | "present";

export type PresentationTemplateId =
  | "tpl-initial-consultation"
  | "tpl-quarterly-review"
  | "tpl-annual-review"
  | "tpl-investment-proposal"
  | "tpl-portfolio-update"
  | "tpl-market-commentary"
  | "tpl-custom";

export type PresentationSectionDef = {
  id: PresentationSectionId;
  label: string;
  visible: boolean;
};

export type AdvisorPresentation = {
  id: PresentationId;
  title: string;
  clientAlias: string;
  templateId: PresentationTemplateId;
  lifecycle: PresentationLifecycle;
  sections: PresentationSectionDef[];
  modelPortfolioId: string;
  envelopeIds: string[];
  updatedAt: string;
};

export type CommentaryKind = "meeting" | "action" | "suitability" | "review";

export type AdvisorCommentary = {
  id: string;
  kind: CommentaryKind;
  title: string;
  body: string;
};

export const DEFAULT_SECTION_ORDER: PresentationSectionId[] = [
  "executive_summary",
  "investment_objectives",
  "client_profile",
  "research_summary",
  "model_portfolio",
  "portfolio_allocation",
  "top_opportunities",
  "risk_review",
  "research_timeline",
  "advisor_notes",
  "disclosures",
];

export const SECTION_LABELS: Record<PresentationSectionId, string> = {
  executive_summary: "Executive Summary",
  investment_objectives: "Investment Objectives",
  client_profile: "Client Profile",
  research_summary: "Research Summary",
  model_portfolio: "Model Portfolio",
  portfolio_allocation: "Portfolio Allocation",
  top_opportunities: "Top Opportunities",
  risk_review: "Risk Review",
  research_timeline: "Research Timeline",
  advisor_notes: "Advisor Notes",
  disclosures: "Disclosures",
};
