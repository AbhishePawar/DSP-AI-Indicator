import type { SuggestedQuestion } from "./types";

export const SUGGESTED_QUESTIONS: readonly SuggestedQuestion[] = [
  {
    id: "why_buy",
    label: "Why is this company recommended?",
    intent: "explain_recommendation",
  },
  {
    id: "explain_valuation",
    label: "Explain the valuation.",
    intent: "explain_valuation",
  },
  {
    id: "explain_margin_of_safety",
    label: "Explain the margin of safety.",
    intent: "explain_margin_of_safety",
  },
  {
    id: "explain_moat",
    label: "Explain the economic moat.",
    intent: "explain_moat",
  },
  {
    id: "explain_management",
    label: "Summarise management quality.",
    intent: "explain_management",
  },
  {
    id: "explain_financial_strength",
    label: "Explain financial strength.",
    intent: "explain_financial_strength",
  },
  {
    id: "explain_earnings_quality",
    label: "Explain earnings quality.",
    intent: "explain_earnings_quality",
  },
  {
    id: "explain_growth_quality",
    label: "Explain growth quality.",
    intent: "explain_growth_quality",
  },
  {
    id: "summarise_strengths",
    label: "Summarise strengths.",
    intent: "summarise_strengths",
  },
  {
    id: "summarise_risks",
    label: "Summarise weaknesses.",
    intent: "summarise_weaknesses",
  },
  {
    id: "explain_committee",
    label: "Explain the committee decision.",
    intent: "explain_committee",
  },
  {
    id: "compare_companies",
    label: "Compare companies.",
    intent: "compare_companies",
  },
] as const;

export const UNAVAILABLE_ANSWER =
  "This information is not currently available.";
