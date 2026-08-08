/** RC1 M8 — template catalogue (IDs match backend TEMPLATE_IDS). */

export const RESEARCH_WORKSPACE_TEMPLATES = [
  { id: "investment_memo", label: "Investment Memo" },
  { id: "company_report", label: "Company Report" },
  { id: "quarterly_review", label: "Quarterly Review" },
  { id: "management_review", label: "Management Review" },
  { id: "bull_case", label: "Bull Case" },
  { id: "bear_case", label: "Bear Case" },
  { id: "base_case", label: "Base Case" },
  { id: "meeting_notes", label: "Meeting Notes" },
  { id: "checklist", label: "Checklist" },
] as const;

export const RESEARCH_WORKSPACE_AI_ACTIONS = [
  { id: "summarize", instruction: "Summarize this research note." },
  { id: "improve", instruction: "Improve the writing while preserving facts." },
  {
    id: "memo",
    instruction: "Generate an investment memo shell from this note.",
  },
  { id: "checklist", instruction: "Generate a research checklist." },
  { id: "thesis", instruction: "Expand the investment thesis." },
  { id: "risks", instruction: "Explain risks using existing research only." },
  {
    id: "valuation",
    instruction: "Explain valuation and margin of safety from attached research.",
  },
  {
    id: "rewrite",
    instruction: "Rewrite this note professionally without inventing numbers.",
  },
] as const;

export const PUBLISH_STATUSES = [
  "draft",
  "review",
  "approved",
  "published",
  "archived",
] as const;
