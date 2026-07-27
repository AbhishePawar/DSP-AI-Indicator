/**
 * Sprint 7.4 — Team Review & Assignment types (presentation / session only).
 */

export type AssignmentColumnId =
  | "unassigned"
  | "assigned"
  | "in_progress"
  | "ready"
  | "completed"
  | "deferred";

export type AssignmentPriority = "p0" | "p1" | "p2" | "p3";

export type TeamReviewFilterState = {
  query: string;
  owner: string;
  priority: AssignmentPriority | "";
  client: string;
  status: string;
  meetingType: string;
  portfolio: string;
  researchStatus: "" | "linked" | "missing";
  presentationStatus: "" | "ready" | "missing";
  upcomingOnly: boolean;
  completedOnly: boolean;
};

export type TeamReviewActivityKind =
  | "assignment"
  | "status_change"
  | "review_opened"
  | "review_completed"
  | "presentation_generated"
  | "research_viewed"
  | "portfolio_reviewed"
  | "discussion";

export type TeamReviewActivityItem = {
  id: string;
  kind: TeamReviewActivityKind;
  label: string;
  at: string;
  reviewId?: string;
};

export type TeamAssignmentMeta = {
  reviewId: string;
  column: AssignmentColumnId;
  owner: string;
  priority: AssignmentPriority;
};

export type ReviewDiscussionDraft = {
  reviewId: string;
  reviewNotes: string;
  researchNotes: string;
  portfolioNotes: string;
  meetingNotes: string;
  questions: string;
  followUpNotes: string;
  updatedAt: string;
};

export const ASSIGNMENT_COLUMNS: {
  id: AssignmentColumnId;
  label: string;
}[] = [
  { id: "unassigned", label: "Unassigned" },
  { id: "assigned", label: "Assigned" },
  { id: "in_progress", label: "In Progress" },
  { id: "ready", label: "Ready" },
  { id: "completed", label: "Completed" },
  { id: "deferred", label: "Deferred" },
];

export const DEFAULT_TEAM_REVIEW_FILTERS: TeamReviewFilterState = {
  query: "",
  owner: "",
  priority: "",
  client: "",
  status: "",
  meetingType: "",
  portfolio: "",
  researchStatus: "",
  presentationStatus: "",
  upcomingOnly: false,
  completedOnly: false,
};

export const TEAM_REVIEW_NAV = [
  { href: "/advisor/team/shared-reviews", label: "Overview", exact: true },
  { href: "/advisor/team/shared-reviews/board", label: "Assignment Board" },
  { href: "/advisor/team/shared-reviews/discussion", label: "Discussion" },
  { href: "/advisor/team/shared-reviews/timeline", label: "Timeline" },
  { href: "/advisor/team/shared-reviews/progress", label: "Progress" },
  { href: "/advisor/team/shared-reviews/activity", label: "Activity" },
] as const;

export const DEMO_OWNERS = [
  "Unassigned",
  "Alex Rivera (Demo)",
  "Research Desk (Demo)",
  "Coverage (Demo)",
  "Jordan Lee (Demo)",
] as const;
