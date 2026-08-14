/**
 * EPIC-010 / GA-003 — Performance automation catalogue (thin-client UI only).
 */

/** Flagship product routes that must keep route-level code splitting. */
export const FLAGSHIP_DYNAMIC_ROUTES = [
  "src/app/analysis/page.tsx",
  "src/app/portfolio/page.tsx",
  "src/app/research/page.tsx",
  "src/app/research/institutional/page.tsx",
  "src/app/research/institutional/dashboard/page.tsx",
  "src/app/settings/page.tsx",
] as const;

/** Workspaces that must use React.lazy / dynamic import for heavy modules. */
export const LAZY_WORKSPACE_MODULES = [
  "src/components/portfolio-intelligence/PortfolioIntelligenceWorkspace.tsx",
  "src/components/research-workspace/ResearchWorkspace.tsx",
  "src/components/institutional-reports/InstitutionalReportsWorkspace.tsx",
] as const;

/** Advisory gzip-ish size budgets for post-build static chunks (bytes). */
export const BUNDLE_BUDGETS = {
  /** Soft advisory — warn in docs; script fails only on hardMax. */
  advisoryTotalStaticJsBytes: 3_500_000,
  /** Hard gate for CI budget script when .next exists. */
  hardMaxTotalStaticJsBytes: 6_000_000,
  /** Shared first-load posture from RC3 (~103 kB reported) — documented baseline. */
  documentedSharedFirstLoadKb: 103,
} as const;

export const PERFORMANCE_AUTOMATION_SCOPE = [
  "route-dynamic-imports",
  "workspace-react-lazy",
  "skeleton-loading-fallbacks",
  "bundle-analyzer-script",
  "lighthouse-ci-config",
  "static-js-size-budget",
] as const;
