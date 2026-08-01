/**
 * EPIC-F007 — Research Workspace section registry.
 */

export type ResearchSectionId =
  | "library"
  | "viewer"
  | "ratings"
  | "valuationTransparency"
  | "archive"
  | "diff"
  | "ai"
  | "buffett"
  | "compliance"
  | "export";

export type ResearchSectionMeta = {
  id: ResearchSectionId;
  label: string;
  description: string;
  shortcut: string;
};

export const RESEARCH_SECTIONS: readonly ResearchSectionMeta[] = [
  {
    id: "library",
    label: "Library",
    description: "Browse local research history",
    shortcut: "1",
  },
  {
    id: "viewer",
    label: "Viewer",
    description: "Inspect mapped research outputs",
    shortcut: "2",
  },
  {
    id: "ratings",
    label: "Institutional Ratings",
    description: "Unified scorecard and investment rating dashboard",
    shortcut: "3",
  },
  {
    id: "valuationTransparency",
    label: "Valuation Transparency",
    description: "Institutional valuation methods, consensus, and margin of safety",
    shortcut: "4",
  },
  {
    id: "archive",
    label: "Archive",
    description: "Local session archive browser",
    shortcut: "5",
  },
  {
    id: "diff",
    label: "Diff",
    description: "Research comparison",
    shortcut: "6",
  },
  {
    id: "ai",
    label: "AI & Committee",
    description: "Committee and evidence display",
    shortcut: "7",
  },
  {
    id: "buffett",
    label: "Buffett Indicator",
    description: "Buffett-style report synthesis from existing outputs",
    shortcut: "8",
  },
  {
    id: "compliance",
    label: "Compliance",
    description: "Policy flags and limitations",
    shortcut: "9",
  },
  {
    id: "export",
    label: "Export",
    description: "Export mapped research snapshot",
    shortcut: "0",
  },
] as const;

export function isResearchSectionId(value: string): value is ResearchSectionId {
  return RESEARCH_SECTIONS.some((s) => s.id === value);
}
