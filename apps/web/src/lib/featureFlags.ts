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
  /** EPIC-011B — Research Intelligence & Validation Platform (presentation only) */
  researchIntelligence: boolean;
  /** EPIC-012/013 — Institutional Company Comparison workspace (presentation only) */
  companyComparison: boolean;
  /** EPIC-014 — Institutional Research Canvas / Research OS shell (presentation only) */
  researchCanvas: boolean;
  /** EPIC-015 — Portfolio Intelligence 2.0 enhancements (presentation only) */
  portfolioIntelligenceV2: boolean;
  /** P5.1 — closed beta programme */
  closedBeta: boolean;
  betaBanner: boolean;
  betaInvitationOnly: boolean;
  betaReadOnlySafeguards: boolean;
  /** EPS-002 — Enterprise Customer Portal (presentation only) */
  enterprisePortal: boolean;
  /** EPS-002 — Enterprise Admin / Ops surfaces (presentation only) */
  enterpriseAdmin: boolean;
  enterpriseOps: boolean;
  /** RC1 Milestone 6 — role-specific enterprise dashboards (presentation only) */
  enterpriseDashboards: boolean;
  /** RC1 Milestone 8 — institutional Research Workspace (orchestration UI only) */
  researchWorkspacePlatform: boolean;
  /** RC1 Milestone 9 — Commercial SaaS Platform (orchestration UI only) */
  saasPlatform: boolean;
  /** RC1 Milestone 10 — Production Operations dashboard (presentation only) */
  productionOps: boolean;
  /** RC1 Milestone 11 — Super Admin Control Center (presentation only) */
  controlCenter: boolean;
};

export const featureFlags: FeatureFlags = {
  researchMode: envBool("NEXT_PUBLIC_RESEARCH_MODE", true),
  recommendationMode: envBool("NEXT_PUBLIC_RECOMMENDATION_MODE", false),
  sebiMode: envBool("NEXT_PUBLIC_SEBI_MODE", false),
  showTargetPrice: envBool("NEXT_PUBLIC_SHOW_TARGET_PRICE", false),
  showBuySell: envBool("NEXT_PUBLIC_SHOW_BUY_SELL", false),
  showModelPortfolio: envBool("NEXT_PUBLIC_SHOW_MODEL_PORTFOLIO", false),
  showResearchAlerts: envBool("NEXT_PUBLIC_SHOW_RESEARCH_ALERTS", false),
  researchIntelligence: envBool("NEXT_PUBLIC_RESEARCH_INTELLIGENCE", true),
  companyComparison: envBool("NEXT_PUBLIC_COMPANY_COMPARISON", true),
  researchCanvas: envBool("NEXT_PUBLIC_RESEARCH_CANVAS", true),
  portfolioIntelligenceV2: envBool(
    "NEXT_PUBLIC_PORTFOLIO_INTELLIGENCE_V2",
    true,
  ),
  closedBeta: envBool("NEXT_PUBLIC_CLOSED_BETA", false),
  betaBanner: envBool("NEXT_PUBLIC_BETA_BANNER", true),
  betaInvitationOnly: envBool("NEXT_PUBLIC_BETA_INVITATION_ONLY", true),
  betaReadOnlySafeguards: envBool("NEXT_PUBLIC_BETA_READ_ONLY_SAFEGUARDS", true),
  enterprisePortal: envBool("NEXT_PUBLIC_ENTERPRISE_PORTAL", true),
  enterpriseAdmin: envBool("NEXT_PUBLIC_ENTERPRISE_ADMIN", true),
  enterpriseOps: envBool("NEXT_PUBLIC_ENTERPRISE_OPS", true),
  enterpriseDashboards: envBool("NEXT_PUBLIC_ENTERPRISE_DASHBOARDS", true),
  researchWorkspacePlatform: envBool(
    "NEXT_PUBLIC_RESEARCH_WORKSPACE_PLATFORM",
    true,
  ),
  saasPlatform: envBool("NEXT_PUBLIC_SAAS_PLATFORM", true),
  productionOps: envBool("NEXT_PUBLIC_PRODUCTION_OPS", true),
  controlCenter: envBool("NEXT_PUBLIC_CONTROL_CENTER", true),
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
