/**
 * P9.4 / EPIC-005 — Company Analysis Workspace section registry.
 * Navigation only — no scoring.
 */

export type AnalysisSectionId =
  | "summary"
  | "valuation"
  | "quality"
  | "management"
  | "moat"
  | "risk"
  | "financial"
  | "ai"
  | "explainability"
  | "evidence"
  | "timeline"
  | "export"
  | "ratings"
  | "valuationTransparency"
  | "research"
  | "buffett"
  | "compliance"
  | "ownership"
  | "peers"
  | "documents"
  | "news"
  | "copilot"
  | "settings";

export type AnalysisSectionMeta = {
  id: AnalysisSectionId;
  label: string;
  description: string;
  shortcut: string;
  lazy?: boolean;
};

/** Primary institutional reading order for the flagship workspace. */
export const ANALYSIS_SECTIONS: readonly AnalysisSectionMeta[] = [
  {
    id: "summary",
    label: "Executive Summary",
    description: "Company header, conclusion, recommendation state",
    shortcut: "1",
  },
  {
    id: "valuation",
    label: "Valuation",
    description: "Backend valuation outputs only",
    shortcut: "2",
    lazy: true,
  },
  {
    id: "quality",
    label: "Business Quality",
    description: "Quality aggregator and durability signals",
    shortcut: "3",
    lazy: true,
  },
  {
    id: "management",
    label: "Management",
    description: "Management quality and governance stages",
    shortcut: "4",
    lazy: true,
  },
  {
    id: "moat",
    label: "Economic Moat",
    description: "Moat stage outputs from analyse",
    shortcut: "5",
    lazy: true,
  },
  {
    id: "risk",
    label: "Risk",
    description: "Risk notes and financial strength stage",
    shortcut: "6",
    lazy: true,
  },
  {
    id: "financial",
    label: "Financial Performance",
    description: "Financial and growth stage summaries",
    shortcut: "7",
    lazy: true,
  },
  {
    id: "ai",
    label: "AI Committee",
    description: "Committee decision, rationale, dissent",
    shortcut: "8",
    lazy: true,
  },
  {
    id: "explainability",
    label: "Explainability",
    description: "Why the conclusion — evidence and confidence",
    shortcut: "9",
    lazy: true,
  },
  {
    id: "evidence",
    label: "Supporting Evidence",
    description: "Evidence chain and research objects",
    shortcut: "E",
    lazy: true,
  },
  {
    id: "timeline",
    label: "Research Timeline",
    description: "Pipeline and audit timeline",
    shortcut: "T",
    lazy: true,
  },
  {
    id: "export",
    label: "Downloads",
    description: "PDF, research report, print, and share",
    shortcut: "0",
  },
  {
    id: "ratings",
    label: "Institutional Ratings",
    description: "Unified scorecard dashboard",
    shortcut: "R",
    lazy: true,
  },
  {
    id: "valuationTransparency",
    label: "Valuation Transparency",
    description: "Methods, consensus, margin of safety detail",
    shortcut: "V",
    lazy: true,
  },
  {
    id: "research",
    label: "Research Object",
    description: "Research object and report metadata",
    shortcut: "O",
    lazy: true,
  },
  {
    id: "buffett",
    label: "Buffett Indicator",
    description: "Buffett-style report synthesis",
    shortcut: "B",
    lazy: true,
  },
  {
    id: "compliance",
    label: "Compliance",
    description: "Policy flags and limitations",
    shortcut: "C",
    lazy: true,
  },
  {
    id: "ownership",
    label: "Ownership",
    description: "Promoter holding and insider transactions",
    shortcut: "W",
    lazy: true,
  },
  {
    id: "peers",
    label: "Peers",
    description: "Qualitative peer comparison via the comparison engine",
    shortcut: "P",
    lazy: true,
  },
  {
    id: "documents",
    label: "Documents",
    description: "Annual reports, quarterly results, presentations, corporate actions",
    shortcut: "D",
    lazy: true,
  },
  {
    id: "news",
    label: "News",
    description: "Company news feed",
    shortcut: "N",
    lazy: true,
  },
  {
    id: "copilot",
    label: "AI Copilot",
    description: "Ask the AI Investment Copilot about this company",
    shortcut: "K",
    lazy: true,
  },
  {
    id: "settings",
    label: "Settings",
    description: "Workspace preferences — panels, theme, notes, tags",
    shortcut: "S",
    lazy: true,
  },
] as const;

export function isAnalysisSectionId(value: string): boolean {
  return ANALYSIS_SECTIONS.some((s) => s.id === value);
}

export function asAnalysisSectionId(value: string): AnalysisSectionId {
  return isAnalysisSectionId(value) ? (value as AnalysisSectionId) : "summary";
}
