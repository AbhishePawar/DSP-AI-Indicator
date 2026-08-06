/**
 * EPIC-014 — Institutional Research Canvas section / tab registry.
 * Navigation metadata only — no scoring or research generation.
 */

export type CanvasTabId =
  | "overview"
  | "financials"
  | "valuation"
  | "bq"
  | "management"
  | "moat"
  | "risk"
  | "researchIntelligence"
  | "comparison"
  | "timeline"
  | "committee"
  | "explainability"
  | "evidence"
  | "notes";

export type CanvasTabMeta = {
  id: CanvasTabId;
  label: string;
  description: string;
  /** Deep-link into an existing institutional surface (composition). */
  href: (symbol: string | null) => string;
  shortcut: string;
  /** Feature-flag gate (checked by canvas shell). */
  requiresFlag?: "researchIntelligence" | "companyComparison";
};

export const CANVAS_TABS: readonly CanvasTabMeta[] = [
  {
    id: "overview",
    label: "Overview",
    description: "Company Analysis executive summary",
    href: (s) =>
      s ? `/analysis?symbol=${encodeURIComponent(s)}&section=summary` : "/analysis",
    shortcut: "1",
  },
  {
    id: "financials",
    label: "Financials",
    description: "Financial performance from analyse",
    href: (s) =>
      s
        ? `/analysis?symbol=${encodeURIComponent(s)}&section=financial`
        : "/analysis?section=financial",
    shortcut: "2",
  },
  {
    id: "valuation",
    label: "Valuation",
    description: "Backend valuation outputs only",
    href: (s) =>
      s
        ? `/analysis?symbol=${encodeURIComponent(s)}&section=valuation`
        : "/analysis?section=valuation",
    shortcut: "3",
  },
  {
    id: "bq",
    label: "Business Quality",
    description: "Quality aggregator pass-through",
    href: (s) =>
      s
        ? `/analysis?symbol=${encodeURIComponent(s)}&section=quality`
        : "/analysis?section=quality",
    shortcut: "4",
  },
  {
    id: "management",
    label: "Management",
    description: "Management quality stage",
    href: (s) =>
      s
        ? `/analysis?symbol=${encodeURIComponent(s)}&section=management`
        : "/analysis?section=management",
    shortcut: "5",
  },
  {
    id: "moat",
    label: "Moat",
    description: "Economic moat stage",
    href: (s) =>
      s
        ? `/analysis?symbol=${encodeURIComponent(s)}&section=moat`
        : "/analysis?section=moat",
    shortcut: "6",
  },
  {
    id: "risk",
    label: "Risk",
    description: "Risk notes and financial strength",
    href: (s) =>
      s
        ? `/analysis?symbol=${encodeURIComponent(s)}&section=risk`
        : "/analysis?section=risk",
    shortcut: "7",
  },
  {
    id: "researchIntelligence",
    label: "Research Intelligence",
    description: "Performance / calibration measurement",
    href: (s) =>
      s
        ? `/research/intelligence?symbol=${encodeURIComponent(s)}&section=timeline`
        : "/research/intelligence",
    shortcut: "I",
    requiresFlag: "researchIntelligence",
  },
  {
    id: "comparison",
    label: "Comparison",
    description: "Company Comparison decision workspace",
    href: (s) =>
      s
        ? `/analysis/compare?symbols=${encodeURIComponent(s)}`
        : "/analysis/compare",
    shortcut: "C",
    requiresFlag: "companyComparison",
  },
  {
    id: "timeline",
    label: "Timeline",
    description: "Research evolution timeline",
    href: (s) =>
      s
        ? `/analysis?symbol=${encodeURIComponent(s)}&section=timeline`
        : "/analysis?section=timeline",
    shortcut: "T",
  },
  {
    id: "committee",
    label: "Committee",
    description: "AI Committee decision surface",
    href: (s) =>
      s
        ? `/analysis?symbol=${encodeURIComponent(s)}&section=ai`
        : "/analysis?section=ai",
    shortcut: "A",
  },
  {
    id: "explainability",
    label: "Explainability",
    description: "Why the conclusion",
    href: (s) =>
      s
        ? `/analysis?symbol=${encodeURIComponent(s)}&section=explainability`
        : "/analysis?section=explainability",
    shortcut: "X",
  },
  {
    id: "evidence",
    label: "Evidence",
    description: "Supporting evidence chain",
    href: (s) =>
      s
        ? `/analysis?symbol=${encodeURIComponent(s)}&section=evidence`
        : "/analysis?section=evidence",
    shortcut: "E",
  },
  {
    id: "notes",
    label: "Notes",
    description: "User-authored research notebook",
    href: (s) =>
      s
        ? `/research/canvas?symbol=${encodeURIComponent(s)}&tab=notes`
        : "/research/canvas?tab=notes",
    shortcut: "N",
  },
] as const;

export function isCanvasTabId(value: string): value is CanvasTabId {
  return CANVAS_TABS.some((t) => t.id === value);
}

export function asCanvasTabId(value: string): CanvasTabId {
  return isCanvasTabId(value) ? value : "overview";
}

export function canvasTabMeta(id: CanvasTabId): CanvasTabMeta {
  return CANVAS_TABS.find((t) => t.id === id) ?? CANVAS_TABS[0];
}
