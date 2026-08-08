/** Map suggested question ids → Copilot 2.0 modes. */

import type { SuggestedQuestionId } from "./types";

export function modeForQuestion(
  questionId: SuggestedQuestionId | "freeform",
): string | undefined {
  switch (questionId) {
    case "explain_valuation":
    case "explain_margin_of_safety":
      return "valuation";
    case "explain_committee":
      return "committee";
    case "explain_risk":
    case "summarise_risks":
      return "risk";
    case "analyze_portfolio":
      return "portfolio";
    case "compare_companies":
      return "comparison";
    case "document_qa":
      return "document";
    case "investment_memo":
      return "memo";
    case "buffett":
      return "buffett";
    case "why_buy":
      return "company";
    default:
      return undefined;
  }
}
