/** Research Mode terminology — never hard-code BUY/SELL/HOLD in UI. */

import {
  allowActionLabels,
  allowOfficialTargetPrice,
  featureFlags,
  type FeatureFlags,
} from "@/lib/featureFlags";

const ACTION_RESEARCH: Record<string, string> = {
  strong_buy: "Attractive",
  buy: "Attractive",
  hold: "Fairly Valued",
  neutral: "Fairly Valued",
  reduce: "Reduce Exposure",
  sell: "Caution",
  strong_sell: "Caution",
  watch: "Watch Closely",
  insufficient_evidence: "Insufficient Evidence",
};

const ACTION_SEBI: Record<string, string> = {
  strong_buy: "Strong Buy",
  buy: "Buy",
  hold: "Hold",
  neutral: "Hold",
  reduce: "Reduce",
  sell: "Sell",
  strong_sell: "Strong Sell",
  watch: "Watch",
  insufficient_evidence: "Insufficient Evidence",
};

const FIELD_RESEARCH: Record<string, string> = {
  target_price: "Estimated Intrinsic Value Range",
  recommendation: "Research Conclusion",
  stock_recommendation: "Investment Assessment",
  action: "DSP View",
};

const FIELD_SEBI: Record<string, string> = {
  target_price: "Official Target Price",
  recommendation: "Recommendation",
  stock_recommendation: "Stock Recommendation",
  action: "Recommendation",
};

function normalizeToken(token: string): string {
  return token.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

export function presentAction(
  token: string,
  flags: FeatureFlags = featureFlags,
): string {
  const key = normalizeToken(token);
  if (allowActionLabels(flags)) {
    return ACTION_SEBI[key] ?? token;
  }
  return ACTION_RESEARCH[key] ?? "Unclassified";
}

export function presentFieldLabel(
  fieldKey: string,
  flags: FeatureFlags = featureFlags,
): string {
  const key = normalizeToken(fieldKey);
  if (allowOfficialTargetPrice(flags) && key === "target_price") {
    return FIELD_SEBI.target_price;
  }
  if (allowActionLabels(flags)) {
    return FIELD_SEBI[key] ?? fieldKey;
  }
  return FIELD_RESEARCH[key] ?? fieldKey;
}
