/** Product mode feature flags — presentation only (PR1.0).
 *
 * Mirrors packages/compliance FeatureFlags.
 * Default: Research Mode ON; recommendation / SEBI surfaces OFF.
 */

function envBool(name: string, fallback: boolean): boolean {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  return ["1", "true", "yes", "on"].includes(raw.trim().toLowerCase());
}

export type FeatureFlags = {
  researchMode: boolean;
  recommendationMode: boolean;
  sebiMode: boolean;
  showTargetPrice: boolean;
  showBuySell: boolean;
  showModelPortfolio: boolean;
  showResearchAlerts: boolean;
};

export const featureFlags: FeatureFlags = {
  researchMode: envBool("NEXT_PUBLIC_RESEARCH_MODE", true),
  recommendationMode: envBool("NEXT_PUBLIC_RECOMMENDATION_MODE", false),
  sebiMode: envBool("NEXT_PUBLIC_SEBI_MODE", false),
  showTargetPrice: envBool("NEXT_PUBLIC_SHOW_TARGET_PRICE", false),
  showBuySell: envBool("NEXT_PUBLIC_SHOW_BUY_SELL", false),
  showModelPortfolio: envBool("NEXT_PUBLIC_SHOW_MODEL_PORTFOLIO", false),
  showResearchAlerts: envBool("NEXT_PUBLIC_SHOW_RESEARCH_ALERTS", false),
};

export function allowActionLabels(flags: FeatureFlags = featureFlags): boolean {
  return flags.recommendationMode && flags.sebiMode && flags.showBuySell;
}

export function allowOfficialTargetPrice(
  flags: FeatureFlags = featureFlags,
): boolean {
  return flags.recommendationMode && flags.sebiMode && flags.showTargetPrice;
}

export function isResearchOnly(flags: FeatureFlags = featureFlags): boolean {
  return flags.researchMode && !flags.sebiMode;
}
