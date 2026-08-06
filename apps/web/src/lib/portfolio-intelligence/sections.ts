/**
 * P9.5 / EPIC-006 — Portfolio Intelligence Workspace section registry.
 * Navigation only — no portfolio scoring.
 */

export type PortfolioSectionId =
  | "summary"
  | "allocation"
  | "performance"
  | "quality"
  | "valuation"
  | "risk"
  | "research"
  | "watchlist"
  | "opportunities"
  | "rebalancing"
  | "explainability"
  | "export"
  | "holdings"
  | "compliance"
  /** EPIC-015 — Portfolio Intelligence 2.0 */
  | "scenarios"
  | "drift"
  | "timeline"
  | "integrations"
  /** Portfolio Intelligence Analytics module (additive) */
  | "correlation"
  | "efficient-frontier"
  | "monte-carlo"
  | "stress-testing"
  | "scenario-impact"
  | "tax-optimization"
  | "position-limits"
  | "factor-exposure";

export type PortfolioSectionMeta = {
  id: PortfolioSectionId;
  label: string;
  description: string;
  shortcut: string;
  lazy?: boolean;
};

/** Primary institutional reading order. */
export const PORTFOLIO_SECTIONS: readonly PortfolioSectionMeta[] = [
  {
    id: "summary",
    label: "Executive Summary",
    description: "Portfolio header and health overview",
    shortcut: "1",
  },
  {
    id: "allocation",
    label: "Asset Allocation",
    description: "Session holding counts by classification",
    shortcut: "2",
    lazy: true,
  },
  {
    id: "performance",
    label: "Performance",
    description: "Returns require backend feeds",
    shortcut: "3",
    lazy: true,
  },
  {
    id: "quality",
    label: "Portfolio Quality",
    description: "Quality pass-through from intelligence API",
    shortcut: "4",
    lazy: true,
  },
  {
    id: "valuation",
    label: "Portfolio Valuation",
    description: "MoS pass-through — no client weighting",
    shortcut: "5",
    lazy: true,
  },
  {
    id: "risk",
    label: "Portfolio Risk",
    description: "Concentration and risk pass-through",
    shortcut: "6",
    lazy: true,
  },
  {
    id: "research",
    label: "Research Activity",
    description: "Coverage and recent reports",
    shortcut: "7",
    lazy: true,
  },
  {
    id: "watchlist",
    label: "Watchlist",
    description: "Local watchlist integration",
    shortcut: "8",
    lazy: true,
  },
  {
    id: "opportunities",
    label: "Opportunities",
    description: "Investigation candidates from available data",
    shortcut: "9",
    lazy: true,
  },
  {
    id: "rebalancing",
    label: "Rebalancing",
    description: "Review queue and alerts",
    shortcut: "R",
    lazy: true,
  },
  {
    id: "explainability",
    label: "Explainability",
    description: "Why portfolio summary — evidence chain",
    shortcut: "E",
    lazy: true,
  },
  {
    id: "export",
    label: "Downloads",
    description: "Export and share session snapshot",
    shortcut: "0",
  },
  {
    id: "holdings",
    label: "Holdings Table",
    description: "Searchable session holdings",
    shortcut: "H",
    lazy: true,
  },
  {
    id: "compliance",
    label: "Compliance",
    description: "Policy flags presentation",
    shortcut: "C",
    lazy: true,
  },
  {
    id: "scenarios",
    label: "Scenarios",
    description: "Bull / Base / Bear — API pass-through only",
    shortcut: "S",
    lazy: true,
  },
  {
    id: "drift",
    label: "Drift",
    description: "Allocation drift when feeds exist",
    shortcut: "D",
    lazy: true,
  },
  {
    id: "timeline",
    label: "Portfolio Timeline",
    description: "Session activity + research coverage history",
    shortcut: "L",
    lazy: true,
  },
  {
    id: "integrations",
    label: "Research Links",
    description: "Company Research · Comparison · RI · Evidence · Committee",
    shortcut: "G",
    lazy: true,
  },
  {
    id: "correlation",
    label: "Correlation Matrix",
    description: "Pairwise return correlation across session holdings",
    shortcut: "X",
    lazy: true,
  },
  {
    id: "efficient-frontier",
    label: "Efficient Frontier",
    description: "Mean-variance random-weight sampling — approximation only",
    shortcut: "F",
    lazy: true,
  },
  {
    id: "monte-carlo",
    label: "Monte Carlo",
    description: "Bootstrap-resampled terminal return percentiles",
    shortcut: "M",
    lazy: true,
  },
  {
    id: "stress-testing",
    label: "Stress Testing",
    description: "Historical crash-window replay (2008 / 2020)",
    shortcut: "T",
    lazy: true,
  },
  {
    id: "scenario-impact",
    label: "Scenario Analysis",
    description: "Caller-defined shock applied via beta sensitivity",
    shortcut: "N",
    lazy: true,
  },
  {
    id: "tax-optimization",
    label: "Tax Optimization",
    description: "Unrealized gain/loss and loss-harvesting candidates",
    shortcut: "U",
    lazy: true,
  },
  {
    id: "position-limits",
    label: "Position Limits",
    description: "Breach checks against caller-supplied limits",
    shortcut: "P",
    lazy: true,
  },
  {
    id: "factor-exposure",
    label: "Factor Exposure",
    description: "Weighted rollup of Value/Quality/Momentum/Size/Low-vol",
    shortcut: "V",
    lazy: true,
  },
] as const;

export function isPortfolioSectionId(value: string): value is PortfolioSectionId {
  return PORTFOLIO_SECTIONS.some((s) => s.id === value);
}

export function asPortfolioSectionId(value: string): PortfolioSectionId {
  return isPortfolioSectionId(value) ? value : "summary";
}
