/**
 * Team Review fixtures — assignment metadata over existing ClientReview demos.
 * Never mutates research conclusions or portfolio calculations.
 */

import { seedReviews, checklistCompletionPct } from "./reviewModels";
import { seedPresentations } from "./presentationModels";
import { listAdvisorResearchTimeline } from "./advisorResearchViewModel";
import type { ClientReview } from "./reviewTypes";
import type {
  AssignmentColumnId,
  AssignmentPriority,
  TeamAssignmentMeta,
  TeamReviewActivityItem,
} from "./teamReviewTypes";

export const TEAM_REVIEW_TRUST =
  "Team Review & Assignment coordinates existing Client Review demos only — never modifies research conclusions, portfolio calculations, Evidence, Confidence, Methodology, or Limitations. Session presentation layer.";

export function defaultColumnForReview(review: ClientReview): AssignmentColumnId {
  if (review.status === "completed") return "completed";
  if (review.status === "archived") return "deferred";
  if (review.status === "in_progress") {
    const pct = checklistCompletionPct(review);
    return pct >= 70 ? "ready" : "in_progress";
  }
  const hasOwner = review.actions.some((a) => a.owner && a.owner !== "Unassigned");
  return hasOwner ? "assigned" : "unassigned";
}

export function defaultOwnerForReview(review: ClientReview): string {
  return review.actions[0]?.owner ?? "Unassigned";
}

export function defaultPriorityForReview(review: ClientReview): AssignmentPriority {
  if (review.status === "in_progress") return "p0";
  if (review.status === "upcoming") return "p1";
  if (review.status === "completed") return "p3";
  return "p2";
}

export function seedTeamAssignments(): TeamAssignmentMeta[] {
  return seedReviews.map((r) => ({
    reviewId: r.id,
    column: defaultColumnForReview(r),
    owner: defaultOwnerForReview(r),
    priority: defaultPriorityForReview(r),
  }));
}

export function seedTeamReviewActivity(): TeamReviewActivityItem[] {
  const items: TeamReviewActivityItem[] = [
    {
      id: "tr-act-1",
      kind: "assignment",
      label: "Assigned — Client Beta Income Proposal → Alex Rivera (Demo)",
      at: "2026-07-22T08:00:00.000Z",
      reviewId: "rev-progress-1",
    },
    {
      id: "tr-act-2",
      kind: "status_change",
      label: "Status — Client Beta moved to In Progress",
      at: "2026-07-22T08:30:00.000Z",
      reviewId: "rev-progress-1",
    },
    {
      id: "tr-act-3",
      kind: "review_opened",
      label: "Opened — Client Alpha Quarterly Review",
      at: "2026-07-21T10:00:00.000Z",
      reviewId: "rev-upcoming-1",
    },
    {
      id: "tr-act-4",
      kind: "review_completed",
      label: "Completed — Client Epsilon Thematic Review",
      at: "2026-07-02T12:00:00.000Z",
      reviewId: "rev-done-1",
    },
    {
      id: "tr-act-5",
      kind: "portfolio_reviewed",
      label: "Portfolio reviewed — Income Focus linked to Client Beta",
      at: "2026-07-22T07:00:00.000Z",
      reviewId: "rev-progress-1",
    },
  ];

  for (const p of seedPresentations.slice(0, 2)) {
    items.push({
      id: `tr-pres-${p.id}`,
      kind: "presentation_generated",
      label: `Presentation generated — ${p.title}`,
      at: p.updatedAt,
    });
  }

  for (const t of listAdvisorResearchTimeline().slice(0, 2)) {
    items.push({
      id: `tr-res-${t.id}`,
      kind: "research_viewed",
      label: t.label,
      at: t.occurredAt,
    });
  }

  return items.sort((a, b) => b.at.localeCompare(a.at));
}

export const FILTER_CLIENTS = [
  ...new Set(seedReviews.map((r) => r.clientAlias)),
].sort();

export const FILTER_MEETING_TYPES = [
  ...new Set(seedReviews.map((r) => r.templateId)),
].sort();

export const FILTER_PORTFOLIOS = [
  ...new Set(seedReviews.map((r) => r.modelPortfolioId)),
].sort();
