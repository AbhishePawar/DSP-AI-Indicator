/**
 * In-memory Team Review & Assignment session (no persistence).
 * Layers assignment/discussion over existing ClientReview demos via reviewSession.
 */

import {
  checklistCompletionPct,
  buildReviewSummary,
  seedReviews,
} from "./reviewModels";
import {
  getReviewSnapshot,
  setReviewStatus,
  subscribeReviews,
  updateSessionReview,
} from "./reviewSession";
import type { ClientReview, ReviewStatus } from "./reviewTypes";
import {
  seedTeamAssignments,
  seedTeamReviewActivity,
} from "./teamReviewModels";
import {
  ASSIGNMENT_COLUMNS,
  DEFAULT_TEAM_REVIEW_FILTERS,
  type AssignmentColumnId,
  type AssignmentPriority,
  type ReviewDiscussionDraft,
  type TeamAssignmentMeta,
  type TeamReviewActivityItem,
  type TeamReviewFilterState,
} from "./teamReviewTypes";
import { seedModelPortfolioLibrary } from "./modelPortfolioManager";
import { getEnvelope } from "./advisorResearchViewModel";

export type TeamReviewSnapshot = {
  assignments: TeamAssignmentMeta[];
  filters: TeamReviewFilterState;
  activity: TeamReviewActivityItem[];
  discussions: Record<string, ReviewDiscussionDraft>;
  activeDiscussionId: string;
  reviews: ClientReview[];
};

let assignments = seedTeamAssignments();
let filters: TeamReviewFilterState = { ...DEFAULT_TEAM_REVIEW_FILTERS };
let activity = seedTeamReviewActivity();
let discussions: Record<string, ReviewDiscussionDraft> = Object.fromEntries(
  seedReviews.slice(0, 3).map((r) => [
    r.id,
    {
      reviewId: r.id,
      reviewNotes: r.advisorNotes,
      researchNotes: `Linked envelopes: ${r.envelopeIds.join(", ")} (demo — not regenerated).`,
      portfolioNotes: `Model ${r.modelPortfolioId} — existing allocation reused.`,
      meetingNotes: `Scheduled ${r.scheduledAt}`,
      questions: r.clientQuestions.join("\n"),
      followUpNotes: r.actions
        .filter((a) => a.status === "open" || a.status === "waiting")
        .map((a) => a.title)
        .join("\n"),
      updatedAt: r.updatedAt,
    } satisfies ReviewDiscussionDraft,
  ]),
);
let activeDiscussionId =
  seedReviews.find((r) => r.status === "in_progress")?.id ?? seedReviews[0]?.id ?? "";

const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

// Keep in sync when underlying review session changes
subscribeReviews(() => emit());

function pushActivity(
  kind: TeamReviewActivityItem["kind"],
  label: string,
  reviewId?: string,
) {
  activity = [
    {
      id: `tr-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      kind,
      label,
      at: new Date().toISOString(),
      reviewId,
    },
    ...activity,
  ].slice(0, 50);
}

export function subscribeTeamReview(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getTeamReviewSnapshot(): TeamReviewSnapshot {
  const { reviews } = getReviewSnapshot();
  return {
    assignments,
    filters,
    activity,
    discussions,
    activeDiscussionId,
    reviews,
  };
}

export function setTeamReviewFilters(patch: Partial<TeamReviewFilterState>) {
  filters = { ...filters, ...patch };
  emit();
}

export function resetTeamReviewFilters() {
  filters = { ...DEFAULT_TEAM_REVIEW_FILTERS };
  emit();
}

export function getAssignment(reviewId: string): TeamAssignmentMeta | undefined {
  return assignments.find((a) => a.reviewId === reviewId);
}

function mapColumnToReviewStatus(column: AssignmentColumnId): ReviewStatus | null {
  switch (column) {
    case "completed":
      return "completed";
    case "in_progress":
    case "ready":
      return "in_progress";
    case "unassigned":
    case "assigned":
      return "upcoming";
    case "deferred":
      return "archived";
    default:
      return null;
  }
}

export function moveAssignment(reviewId: string, column: AssignmentColumnId) {
  const review = getReviewSnapshot().reviews.find((r) => r.id === reviewId);
  if (!review) return;
  const prev = getAssignment(reviewId);
  assignments = assignments.map((a) =>
    a.reviewId === reviewId ? { ...a, column } : a,
  );
  if (!assignments.some((a) => a.reviewId === reviewId)) {
    assignments = [
      ...assignments,
      {
        reviewId,
        column,
        owner: "Unassigned",
        priority: "p2",
      },
    ];
  }
  const status = mapColumnToReviewStatus(column);
  if (status) setReviewStatus(reviewId, status);
  pushActivity(
    "status_change",
    `Status — ${review.title} → ${ASSIGNMENT_COLUMNS.find((c) => c.id === column)?.label ?? column}`,
    reviewId,
  );
  if (column === "completed") {
    pushActivity("review_completed", `Completed — ${review.title}`, reviewId);
  }
  if (prev?.column === "unassigned" && column === "assigned") {
    pushActivity("assignment", `Assigned — ${review.title}`, reviewId);
  }
  emit();
}

export function setAssignmentOwner(reviewId: string, owner: string) {
  const review = getReviewSnapshot().reviews.find((r) => r.id === reviewId);
  if (!review) return;
  assignments = assignments.map((a) =>
    a.reviewId === reviewId ? { ...a, owner } : a,
  );
  if (owner !== "Unassigned") {
    const meta = getAssignment(reviewId);
    if (meta?.column === "unassigned") {
      assignments = assignments.map((a) =>
        a.reviewId === reviewId ? { ...a, column: "assigned" } : a,
      );
    }
  }
  pushActivity("assignment", `Owner — ${review.title} → ${owner}`, reviewId);
  emit();
}

export function setAssignmentPriority(reviewId: string, priority: AssignmentPriority) {
  assignments = assignments.map((a) =>
    a.reviewId === reviewId ? { ...a, priority } : a,
  );
  emit();
}

export function openTeamReview(reviewId: string) {
  const review = getReviewSnapshot().reviews.find((r) => r.id === reviewId);
  if (!review) return;
  pushActivity("review_opened", `Opened — ${review.title}`, reviewId);
  activeDiscussionId = reviewId;
  emit();
}

export function setActiveDiscussionId(id: string) {
  activeDiscussionId = id;
  emit();
}

export function updateReviewDiscussion(
  reviewId: string,
  patch: Partial<Omit<ReviewDiscussionDraft, "reviewId">>,
) {
  const review = getReviewSnapshot().reviews.find((r) => r.id === reviewId);
  if (!review) return;
  const prev = discussions[reviewId] ?? {
    reviewId,
    reviewNotes: "",
    researchNotes: "",
    portfolioNotes: "",
    meetingNotes: "",
    questions: "",
    followUpNotes: "",
    updatedAt: new Date().toISOString(),
  };
  discussions = {
    ...discussions,
    [reviewId]: {
      ...prev,
      ...patch,
      reviewId,
      updatedAt: new Date().toISOString(),
    },
  };
  pushActivity("discussion", `Discussion updated — ${review.title}`, reviewId);
  emit();
}

export function filterTeamReviews(
  snap: TeamReviewSnapshot = getTeamReviewSnapshot(),
): ClientReview[] {
  const f = snap.filters;
  const q = f.query.trim().toLowerCase();

  return snap.reviews.filter((r) => {
    const meta = snap.assignments.find((a) => a.reviewId === r.id);
    if (q && !r.title.toLowerCase().includes(q) && !r.clientAlias.toLowerCase().includes(q)) {
      return false;
    }
    if (f.owner && meta?.owner !== f.owner) return false;
    if (f.priority && meta?.priority !== f.priority) return false;
    if (f.client && r.clientAlias !== f.client) return false;
    if (f.status && r.status !== f.status) return false;
    if (f.meetingType && r.templateId !== f.meetingType) return false;
    if (f.portfolio && r.modelPortfolioId !== f.portfolio) return false;
    if (f.researchStatus === "linked" && r.envelopeIds.length === 0) return false;
    if (f.researchStatus === "missing" && r.envelopeIds.length > 0) return false;
    if (f.presentationStatus === "ready" && !r.presentationId) return false;
    if (f.presentationStatus === "missing" && r.presentationId) return false;
    if (f.upcomingOnly && r.status !== "upcoming") return false;
    if (f.completedOnly && r.status !== "completed") return false;
    return true;
  });
}

export function reviewsByColumn(
  column: AssignmentColumnId,
  snap: TeamReviewSnapshot = getTeamReviewSnapshot(),
): ClientReview[] {
  const filtered = filterTeamReviews(snap);
  return filtered.filter((r) => {
    const meta = snap.assignments.find((a) => a.reviewId === r.id);
    return (meta?.column ?? "unassigned") === column;
  });
}

export function buildTeamReviewOverview(
  snap: TeamReviewSnapshot = getTeamReviewSnapshot(),
) {
  const reviews = snap.reviews;
  const assigned = snap.assignments.filter((a) => a.owner !== "Unassigned").length;
  const completed = reviews.filter((r) => r.status === "completed").length;
  const pending = reviews.filter(
    (r) => r.status === "upcoming" || r.status === "in_progress",
  ).length;
  const active = reviews.filter((r) => r.status !== "archived");
  const avg =
    active.length === 0
      ? 0
      : Math.round(
          active.reduce((s, r) => s + checklistCompletionPct(r), 0) / active.length,
        );
  const outstanding = snap.assignments.filter(
    (a) => a.column !== "completed" && a.column !== "deferred",
  ).length;
  const upcomingMeetings = reviews.filter((r) => r.status === "upcoming").length;

  return {
    totalReviews: reviews.length,
    assignedReviews: assigned,
    completedReviews: completed,
    pendingReviews: pending,
    averageCompletion: `${avg}%`,
    outstandingAssignments: outstanding,
    upcomingMeetings,
    overallTeamProgress: `${avg}% checklist avg across active reviews`,
  };
}

export function buildReviewProgress(review: ClientReview) {
  const pct = checklistCompletionPct(review);
  const outstanding = review.actions.filter(
    (a) => a.status === "open" || a.status === "waiting",
  );
  const checklistDone = review.checklist.filter((c) => c.done).length;
  const meetingReady = review.checklist.find((c) => c.id === "meeting_complete")?.done
    ? "Ready"
    : review.checklist.find((c) => c.id === "presentation_ready")?.done
      ? "Nearly ready"
      : "Not ready";
  const presentationReady = review.presentationId
    ? review.checklist.find((c) => c.id === "presentation_ready")?.done
      ? "Pack linked · checklist ready"
      : "Pack linked · checklist pending"
    : "No presentation linked";
  const researchCurrency =
    review.envelopeIds.length > 0
      ? `${review.envelopeIds.length} envelopes linked (demo freshness via viewedAt)`
      : "No research linked";
  const portfolio =
    seedModelPortfolioLibrary.find((p) => p.id === review.modelPortfolioId)?.name ??
    review.modelPortfolioId;

  return {
    completionPct: pct,
    outstandingTasks: outstanding.map((a) => a.title),
    checklistProgress: `${checklistDone}/${review.checklist.length}`,
    meetingReadiness: meetingReady,
    presentationReadiness: presentationReady,
    researchCurrency,
    portfolioCurrency: `Model “${portfolio}” — existing demo allocation`,
    summary: buildReviewSummary(review).executiveSummary,
  };
}

export function laneReviews(snap: TeamReviewSnapshot = getTeamReviewSnapshot()) {
  return {
    pending: snap.reviews.filter((r) => r.status === "upcoming"),
    assigned: snap.reviews.filter((r) => {
      const m = snap.assignments.find((a) => a.reviewId === r.id);
      return m?.column === "assigned" || (m?.owner && m.owner !== "Unassigned");
    }),
    inProgress: snap.reviews.filter((r) => r.status === "in_progress"),
    readyForMeeting: snap.reviews.filter((r) => {
      const m = snap.assignments.find((a) => a.reviewId === r.id);
      return m?.column === "ready";
    }),
    completed: snap.reviews.filter((r) => r.status === "completed"),
    archived: snap.reviews.filter((r) => r.status === "archived"),
  };
}

/** Ensure assignment rows exist for session-created reviews */
export function ensureAssignmentForReview(reviewId: string) {
  if (assignments.some((a) => a.reviewId === reviewId)) return;
  assignments = [
    ...assignments,
    {
      reviewId,
      column: "unassigned",
      owner: "Unassigned",
      priority: "p2",
    },
  ];
  emit();
}

export { getEnvelope, updateSessionReview, ASSIGNMENT_COLUMNS };
