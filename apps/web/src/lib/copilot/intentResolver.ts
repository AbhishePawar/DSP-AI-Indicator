/**
 * IntentResolver — structured intent handling for Copilot questions.
 * Deterministic pattern matching only — not an LLM.
 */

import type { CopilotIntent, SuggestedQuestionId } from "./types";

const SUGGESTED_TO_INTENT: Record<SuggestedQuestionId, CopilotIntent> = {
  why_buy: "explain_recommendation",
  explain_valuation: "explain_valuation",
  explain_moat: "explain_moat",
  summarise_strengths: "summarise_strengths",
  summarise_risks: "summarise_weaknesses",
  explain_committee: "explain_committee",
  explain_management: "explain_management",
  explain_financial_strength: "explain_financial_strength",
  explain_earnings_quality: "explain_earnings_quality",
  explain_growth_quality: "explain_growth_quality",
  explain_margin_of_safety: "explain_margin_of_safety",
  compare_companies: "compare_companies",
};

type IntentRule = {
  intent: CopilotIntent;
  patterns: RegExp[];
};

const RULES: IntentRule[] = [
  {
    intent: "compare_companies",
    patterns: [/\bcompar(e|ison|ing)\b/i, /\bvs\.?\b/i, /\bversus\b/i],
  },
  {
    intent: "explain_margin_of_safety",
    patterns: [/\bmargin of safety\b/i, /\bmos\b/i],
  },
  {
    intent: "explain_valuation",
    patterns: [/\bvaluat/i, /\bintrinsic\b/i, /\bfair value\b/i],
  },
  {
    intent: "explain_moat",
    patterns: [/\bmoat\b/i, /\bcompetitive advantage\b/i],
  },
  {
    intent: "explain_management",
    patterns: [/\bmanagement\b/i, /\bgovernance\b/i, /\bcapital allocation\b/i],
  },
  {
    intent: "explain_financial_strength",
    patterns: [/\bfinancial strength\b/i, /\bdebt\b/i, /\bliquidity\b/i],
  },
  {
    intent: "explain_earnings_quality",
    patterns: [/\bearnings quality\b/i, /\bcash conversion\b/i],
  },
  {
    intent: "explain_growth_quality",
    patterns: [/\bgrowth quality\b/i, /\breinvestment\b/i],
  },
  {
    intent: "explain_committee",
    patterns: [/\bcommittee\b/i, /\bconsensus\b/i],
  },
  {
    intent: "summarise_strengths",
    patterns: [/\bstrength/i, /\bhighlight/i, /\bpositive/i],
  },
  {
    intent: "summarise_weaknesses",
    patterns: [/\bweakness/i, /\brisk/i, /\bconcern/i],
  },
  {
    intent: "explain_recommendation",
    patterns: [
      /\brecommend/i,
      /\brated\b/i,
      /\bwhy .*\bbuy\b/i,
      /\bwhy .*\bhold\b/i,
      /\boverall decision\b/i,
    ],
  },
];

export function intentFromSuggestedId(
  id: SuggestedQuestionId,
): CopilotIntent {
  return SUGGESTED_TO_INTENT[id];
}

/**
 * Resolve intent from freeform text, optional suggested id, and prior intent
 * for follow-ups like "tell me more" / "explain that".
 */
export function resolveIntent(
  text: string,
  options?: {
    suggestedId?: SuggestedQuestionId;
    lastIntent?: CopilotIntent | null;
  },
): CopilotIntent {
  if (options?.suggestedId) {
    return intentFromSuggestedId(options.suggestedId);
  }

  const trimmed = text.trim();
  if (!trimmed) return "unknown";

  for (const rule of RULES) {
    if (rule.patterns.some((pattern) => pattern.test(trimmed))) {
      return rule.intent;
    }
  }

  const followUp =
    /^(tell me more|explain (that|this|it)|and\b|what about|go deeper|more detail)/i.test(
      trimmed,
    );
  if (followUp && options?.lastIntent && options.lastIntent !== "unknown") {
    return options.lastIntent;
  }

  return "unknown";
}
