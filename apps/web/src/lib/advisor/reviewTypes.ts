/**
 * Sprint 6 — Client Review Workflow types (session-only presentation layer).
 */

export type ReviewId = string;

export type ReviewStatus = "upcoming" | "in_progress" | "completed" | "archived";

export type ReviewChecklistItemId =
  | "client_information"
  | "research_updated"
  | "portfolio_reviewed"
  | "risk_discussion"
  | "action_items"
  | "presentation_ready"
  | "meeting_complete";

export type ReviewTemplateId =
  | "tpl-initial-consultation"
  | "tpl-quarterly"
  | "tpl-half-year"
  | "tpl-annual"
  | "tpl-special"
  | "tpl-custom";

export type ReviewActionStatus = "open" | "waiting" | "completed" | "deferred";

export type ReviewTimelineKind =
  | "previous_review"
  | "current_review"
  | "upcoming_review"
  | "meeting"
  | "research"
  | "portfolio_change";

export type ReviewChecklistItem = {
  id: ReviewChecklistItemId;
  label: string;
  done: boolean;
};

export type ReviewAction = {
  id: string;
  title: string;
  status: ReviewActionStatus;
  owner: string;
};

export type ReviewTimelineEvent = {
  id: string;
  kind: ReviewTimelineKind;
  label: string;
  occurredAt: string;
};

export type ClientReview = {
  id: ReviewId;
  title: string;
  clientAlias: string;
  status: ReviewStatus;
  templateId: ReviewTemplateId;
  scheduledAt: string;
  presentationId: string | null;
  modelPortfolioId: string;
  envelopeIds: string[];
  checklist: ReviewChecklistItem[];
  actions: ReviewAction[];
  clientQuestions: string[];
  advisorNotes: string;
  updatedAt: string;
};

export const CHECKLIST_LABELS: Record<ReviewChecklistItemId, string> = {
  client_information: "Client Information",
  research_updated: "Research Updated",
  portfolio_reviewed: "Portfolio Reviewed",
  risk_discussion: "Risk Discussion",
  action_items: "Action Items",
  presentation_ready: "Presentation Ready",
  meeting_complete: "Meeting Complete",
};

export const DEFAULT_CHECKLIST_ORDER: ReviewChecklistItemId[] = [
  "client_information",
  "research_updated",
  "portfolio_reviewed",
  "risk_discussion",
  "action_items",
  "presentation_ready",
  "meeting_complete",
];
