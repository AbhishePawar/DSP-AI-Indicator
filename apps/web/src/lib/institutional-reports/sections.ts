/**
 * P9.6 / EPIC-007 — Institutional Research Reports workspace section registry.
 * Navigation only — no scoring or recommendation logic.
 */

export type ReportSectionId =
  | "cover"
  | "summary"
  | "valuation"
  | "quality"
  | "management"
  | "moat"
  | "risk"
  | "ai"
  | "explainability"
  | "evidence"
  | "timeline"
  | "export"
  | "audit";

export type ReportSectionMeta = {
  id: ReportSectionId;
  label: string;
  description: string;
  shortcut: string;
  lazy?: boolean;
};

export type ReportMode = "interactive" | "print" | "pdf";

/** Official publishing reading order for institutional research reports. */
export const REPORT_SECTIONS: readonly ReportSectionMeta[] = [
  {
    id: "cover",
    label: "Report Cover",
    description: "Company, ticker, version, coverage, status",
    shortcut: "1",
  },
  {
    id: "summary",
    label: "Executive Summary",
    description: "Conclusion, recommendation state, positives and risks",
    shortcut: "2",
  },
  {
    id: "valuation",
    label: "Valuation",
    description: "IV, DCF, Relative, Residual Income, EPV, MoS",
    shortcut: "3",
    lazy: true,
  },
  {
    id: "quality",
    label: "Business Quality",
    description: "REP-002 Book 04 concept labels",
    shortcut: "4",
    lazy: true,
  },
  {
    id: "management",
    label: "Management",
    description: "REP-002 Book 05 concept labels",
    shortcut: "5",
    lazy: true,
  },
  {
    id: "moat",
    label: "Economic Moat",
    description: "REP-002 Book 06 concept labels",
    shortcut: "6",
    lazy: true,
  },
  {
    id: "risk",
    label: "Risk",
    description: "REP-002 Book 07 concept labels",
    shortcut: "7",
    lazy: true,
  },
  {
    id: "ai",
    label: "AI Committee",
    description: "Decision, reasoning, confidence, dissent",
    shortcut: "8",
    lazy: true,
  },
  {
    id: "explainability",
    label: "Explainability",
    description: "Trust ladder, evidence chain, confidence",
    shortcut: "9",
    lazy: true,
  },
  {
    id: "evidence",
    label: "Supporting Evidence",
    description: "Research objects, documents, evidence cards",
    shortcut: "E",
    lazy: true,
  },
  {
    id: "timeline",
    label: "Timeline",
    description: "Historical reports, recommendations, events",
    shortcut: "T",
    lazy: true,
  },
  {
    id: "export",
    label: "Downloads",
    description: "Print, PDF layout, share, research export",
    shortcut: "0",
  },
  {
    id: "audit",
    label: "Audit Metadata",
    description: "Versions, timestamps, data freshness",
    shortcut: "A",
    lazy: true,
  },
] as const;

export function isReportSectionId(value: string): value is ReportSectionId {
  return REPORT_SECTIONS.some((s) => s.id === value);
}

export function asReportSectionId(value: string): ReportSectionId {
  return isReportSectionId(value) ? value : "cover";
}

export function isReportMode(value: string): value is ReportMode {
  return value === "interactive" || value === "print" || value === "pdf";
}

export function asReportMode(value: string): ReportMode {
  return isReportMode(value) ? value : "interactive";
}
