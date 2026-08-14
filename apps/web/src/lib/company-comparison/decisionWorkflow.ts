/**
 * Decision Workspace — guided institutional review workflow.
 * Platform NEVER produces the investment decision.
 */

import type { ComparisonSectionId } from "./sections";

export type DecisionWorkflowStepId =
  | "comparison"
  | "winner"
  | "tradeOffs"
  | "contradictory"
  | "buffett"
  | "intelligence"
  | "notes"
  | "thesis"
  | "decisionMemo"
  | "export";

export type DecisionWorkflowStep = {
  id: DecisionWorkflowStepId;
  label: string;
  description: string;
  sectionId: ComparisonSectionId;
  /** User must explicitly acknowledge before treating as complete. */
  userOwned: boolean;
};

export const DECISION_WORKFLOW_STEPS: readonly DecisionWorkflowStep[] = [
  {
    id: "comparison",
    label: "Comparison",
    description: "Review the executive scorecard and what differs.",
    sectionId: "scorecard",
    userOwned: false,
  },
  {
    id: "winner",
    label: "Winner Matrix",
    description: "Inspect evidence-backed dimension leaders.",
    sectionId: "winnerMatrix",
    userOwned: false,
  },
  {
    id: "tradeOffs",
    label: "Trade-offs",
    description: "Understand why companies differ.",
    sectionId: "tradeOffs",
    userOwned: false,
  },
  {
    id: "contradictory",
    label: "Contradictory Evidence",
    description: "Surface supporting and conflicting evidence — never hide conflicts.",
    sectionId: "contradictory",
    userOwned: false,
  },
  {
    id: "buffett",
    label: "Buffett-style Preference",
    description: "Framework alignment presentation (not a buy endorsement).",
    sectionId: "buffett",
    userOwned: false,
  },
  {
    id: "intelligence",
    label: "Research Intelligence",
    description: "Historical validation overlays when available.",
    sectionId: "intelligence",
    userOwned: false,
  },
  {
    id: "notes",
    label: "Notes",
    description: "Capture user-authored research notes.",
    sectionId: "personal",
    userOwned: true,
  },
  {
    id: "thesis",
    label: "Thesis",
    description: "Record your investment thesis (user-authored).",
    sectionId: "personal",
    userOwned: true,
  },
  {
    id: "decisionMemo",
    label: "Decision Memo",
    description: "Assemble the Investment Committee memo for review.",
    sectionId: "committeeMemo",
    userOwned: true,
  },
  {
    id: "export",
    label: "Export",
    description: "Export the comparison / memo. You make the decision.",
    sectionId: "export",
    userOwned: true,
  },
] as const;

/** Institutional UX questions every comparison should answer. */
export const INSTITUTIONAL_UX_QUESTIONS: readonly string[] = [
  "What differs?",
  "Why?",
  "Evidence?",
  "Confidence?",
  "Trade-offs?",
  "Historical validation?",
  "Outstanding concerns?",
  "User decision?",
] as const;

export type ReviewModeId =
  | "standard"
  | "presentation"
  | "committee"
  | "print"
  | "fullscreen"
  | "evidence_first";

export type ReviewModeDef = {
  id: ReviewModeId;
  label: string;
  description: string;
};

export const REVIEW_MODES: readonly ReviewModeDef[] = [
  {
    id: "standard",
    label: "Standard",
    description: "Full institutional comparison workspace.",
  },
  {
    id: "presentation",
    label: "Presentation",
    description: "Larger type, focus on scorecard and winners.",
  },
  {
    id: "committee",
    label: "IC Review",
    description: "Committee memo and evidence-first layout.",
  },
  {
    id: "print",
    label: "Print",
    description: "Print-optimized view for PDF export.",
  },
  {
    id: "fullscreen",
    label: "Fullscreen",
    description: "Distraction-reduced fullscreen review.",
  },
  {
    id: "evidence_first",
    label: "Evidence-first",
    description: "Prioritize contradictory evidence and strength meters.",
  },
] as const;

export function nextWorkflowStep(
  current: DecisionWorkflowStepId,
): DecisionWorkflowStep | null {
  const idx = DECISION_WORKFLOW_STEPS.findIndex((s) => s.id === current);
  if (idx < 0 || idx >= DECISION_WORKFLOW_STEPS.length - 1) return null;
  return DECISION_WORKFLOW_STEPS[idx + 1]!;
}

export function prevWorkflowStep(
  current: DecisionWorkflowStepId,
): DecisionWorkflowStep | null {
  const idx = DECISION_WORKFLOW_STEPS.findIndex((s) => s.id === current);
  if (idx <= 0) return null;
  return DECISION_WORKFLOW_STEPS[idx - 1]!;
}
