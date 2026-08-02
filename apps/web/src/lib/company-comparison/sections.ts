/** EPIC-012/013 — Comparison workspace section registry. */

export type ComparisonSectionId =
  | "summary"
  | "winnerMatrix"
  | "tradeOffs"
  | "valuation"
  | "businessQuality"
  | "management"
  | "moat"
  | "risk"
  | "financial"
  | "evidence"
  | "explainability"
  | "intelligence"
  | "buffett"
  | "heatmap"
  | "scenarios"
  | "portfolioFit"
  | "personal"
  | "export"
  | "architecture";

export type ComparisonSectionDef = {
  id: ComparisonSectionId;
  label: string;
  description: string;
  star?: boolean;
};

export const COMPARISON_SECTIONS: readonly ComparisonSectionDef[] = [
  {
    id: "summary",
    label: "Executive Summary",
    description: "Overall institutional comparison summary",
  },
  {
    id: "winnerMatrix",
    label: "Winner Matrix",
    description: "Evidence-backed dimension leaders",
    star: true,
  },
  {
    id: "tradeOffs",
    label: "Trade-off Analysis",
    description: "Why companies differ on research outputs",
    star: true,
  },
  {
    id: "valuation",
    label: "Valuation Comparison",
    description: "IV, price, MoS, method cards",
  },
  {
    id: "businessQuality",
    label: "Business Quality",
    description: "Engine-supplied BQ stage fields",
  },
  {
    id: "management",
    label: "Management",
    description: "Engine-supplied management fields",
  },
  {
    id: "moat",
    label: "Moat",
    description: "Engine-supplied moat fields",
  },
  {
    id: "risk",
    label: "Risk",
    description: "Engine-supplied risk fields only",
  },
  {
    id: "financial",
    label: "Financial Strength",
    description: "Engine-supplied financial strength fields",
  },
  {
    id: "evidence",
    label: "Evidence Comparison",
    description: "Evidence, confidence, coverage, freshness",
    star: true,
  },
  {
    id: "explainability",
    label: "Explainability",
    description: "Side-by-side explainability summaries",
    star: true,
  },
  {
    id: "intelligence",
    label: "Research Intelligence",
    description: "EPIC-011B accuracy, calibration, timeline",
    star: true,
  },
  {
    id: "buffett",
    label: "Buffett-style Preference",
    description: "Framework alignment — never buy advice",
    star: true,
  },
  {
    id: "heatmap",
    label: "Decision Heatmap",
    description: "Visual intensity from existing scores",
  },
  {
    id: "scenarios",
    label: "Scenario Comparison",
    description: "Bull / Base / Bear when present",
  },
  {
    id: "portfolioFit",
    label: "Portfolio Fit",
    description: "Style tags — not personalised advice",
  },
  {
    id: "personal",
    label: "Personal Research",
    description: "User notes, thesis, watch, decisions",
    star: true,
  },
  {
    id: "export",
    label: "Institutional Export",
    description: "JSON / CSV / print / share",
  },
  {
    id: "architecture",
    label: "Future Architecture",
    description: "Extensible comparison engine abstraction",
  },
] as const;

export function isComparisonSectionId(id: string): id is ComparisonSectionId {
  return COMPARISON_SECTIONS.some((s) => s.id === id);
}
