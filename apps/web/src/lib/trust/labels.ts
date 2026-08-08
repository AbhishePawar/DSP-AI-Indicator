/** Trust labels — User Trust Standard (epistemic honesty). */

export type SourceKind =
  | "verified_financial_statement"
  | "authenticated_market_data"
  | "calculated_metric"
  | "estimated_value"
  | "ai_interpretation"
  | "external_consensus"
  | "user_input"
  | "unavailable";

export type ValueCategory =
  | "verified_fact"
  | "calculated"
  | "estimated"
  | "ai_interpretation"
  | "external_consensus"
  | "user_input"
  | "unknown"
  | "unavailable";

export type ConfidenceLevel =
  | "very_high"
  | "high"
  | "moderate"
  | "low"
  | "insufficient_evidence";

export const SOURCE_LABELS: Record<SourceKind, string> = {
  verified_financial_statement: "Verified Financial Statement",
  authenticated_market_data: "Authenticated Market Data",
  calculated_metric: "Calculated Metric",
  estimated_value: "Estimated Value",
  ai_interpretation: "AI Interpretation",
  external_consensus: "External Consensus",
  user_input: "User Input",
  unavailable: "Unavailable",
};

export const CATEGORY_LABELS: Record<ValueCategory, string> = {
  verified_fact: "Verified Fact",
  calculated: "Calculated",
  estimated: "Estimated",
  ai_interpretation: "AI Interpretation",
  external_consensus: "External Consensus",
  user_input: "User Input",
  unknown: "Unknown",
  unavailable: "Unavailable",
};

export const CONFIDENCE_LABELS: Record<ConfidenceLevel, string> = {
  very_high: "Very High",
  high: "High",
  moderate: "Moderate",
  low: "Low",
  insufficient_evidence: "Insufficient Evidence",
};
