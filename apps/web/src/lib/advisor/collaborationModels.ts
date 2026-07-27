/**
 * Team collaboration overview — reuses existing advisor demo data only.
 */

import { demoResearchEnvelopes } from "./advisorResearchModels";
import { listAdvisorResearchTimeline } from "./advisorResearchViewModel";
import { seedModelPortfolioLibrary } from "./modelPortfolioManager";
import { seedPresentations } from "./presentationModels";
import { seedReviews } from "./reviewModels";
import type {
  CollaborationActivityItem,
  CollaborationPinnedItem,
} from "./collaborationTypes";

export const COLLAB_TRUST =
  "Team Collaboration Foundation is a presentation shell — reuses existing DSP advisor demos only. Never modifies research conclusions, Evidence, Confidence, Methodology, or Limitations. No real-time sync, auth, or persistence.";

export function buildCollaborationOverview() {
  const researchCount = demoResearchEnvelopes.length;
  const reviewCount = seedReviews.filter((r) => r.status !== "archived").length;
  const portfolioCount = seedModelPortfolioLibrary.length;
  const presentationCount = seedPresentations.filter((p) => p.lifecycle === "active").length;

  return {
    workspaceSummary:
      "Session collaboration shell for advisors — My Workspace and Shared Workspace views.",
    researchSummary: `${researchCount} demo research envelopes available for shared organization.`,
    reviewSummary: `${reviewCount} active/upcoming client reviews in demo session.`,
    portfolioSummary: `${portfolioCount} model portfolio library items (demo allocations).`,
    presentationSummary: `${presentationCount} active presentation packs in session.`,
    sessionStateSummary:
      "Sidebar collapse, pins, filters, and recent nav are session-only (not persisted).",
  };
}

export function buildRecentActivity(): CollaborationActivityItem[] {
  const timeline = listAdvisorResearchTimeline().slice(0, 3);
  const items: CollaborationActivityItem[] = timeline.map((t) => ({
    id: `act-${t.id}`,
    label: t.label,
    kind: "research",
    at: t.occurredAt,
    href: "/advisor/team/shared-research",
  }));
  const review = seedReviews.find((r) => r.status === "in_progress") ?? seedReviews[0];
  if (review) {
    items.push({
      id: `act-${review.id}`,
      label: `Review — ${review.title}`,
      kind: "review",
      at: review.updatedAt,
      href: "/advisor/team/shared-reviews",
    });
  }
  items.push({
    id: "act-portfolio",
    label: `Model portfolio library — ${seedModelPortfolioLibrary[0]?.name ?? "demo"}`,
    kind: "portfolio",
    at: "2026-07-22T10:00:00.000Z",
    href: "/advisor/team/shared-portfolios",
  });
  items.push({
    id: "act-pres",
    label: `Presentation — ${seedPresentations[0]?.title ?? "demo pack"}`,
    kind: "presentation",
    at: seedPresentations[0]?.updatedAt ?? "2026-07-22T09:00:00.000Z",
    href: "/advisor/presentations",
  });
  return items.sort((a, b) => b.at.localeCompare(a.at));
}

export const collaborationPinnedCatalog: CollaborationPinnedItem[] = [
  {
    id: "pin-research",
    label: "Shared Research Library",
    href: "/advisor/team/shared-research",
    kind: "research",
  },
  {
    id: "pin-review",
    label: "Shared Reviews",
    href: "/advisor/team/shared-reviews",
    kind: "review",
  },
  {
    id: "pin-portfolio",
    label: "Shared Portfolios",
    href: "/advisor/team/shared-portfolios",
    kind: "portfolio",
  },
  {
    id: "pin-discussions",
    label: "Discussions (placeholder)",
    href: "/advisor/team/discussions",
    kind: "discussion",
  },
  {
    id: "pin-assignments",
    label: "Assignments (board)",
    href: "/advisor/team/shared-reviews/board",
    kind: "assignment",
  },
];
