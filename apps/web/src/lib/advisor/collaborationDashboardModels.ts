/**
 * Sprint 7.5 — Collaboration Dashboard aggregators (presentation only).
 * Reuses existing session snapshots — never mutates engine outputs.
 */

import { listResearchEnvelopes } from "./advisorResearchViewModel";
import { getCollaborationSnapshot } from "./collaborationSession";
import { ADVISOR_SECTIONS } from "./advisorWorkspace";
import { seedModelPortfolioLibrary } from "./modelPortfolioManager";
import { seedPresentations } from "./presentationModels";
import { checklistCompletionPct } from "./reviewModels";
import { getSharedPortfolioSnapshot } from "./sharedPortfolioSession";
import { buildSharedOverview, getSharedResearchSnapshot } from "./sharedResearchSession";
import { buildTeamReviewOverview, getTeamReviewSnapshot } from "./teamReviewSession";
import { listTasks } from "./advisorViewModel";

export const COLLAB_DASHBOARD_TRUST =
  "Collaboration Dashboard aggregates existing Team Collaboration session demos only — never modifies research conclusions, portfolio calculations, Evidence, Confidence, Methodology, or Limitations.";

export type WorkspaceHealthStatus = "healthy" | "watch" | "empty";

export type WorkspaceHealthItem = {
  id: string;
  label: string;
  href: string;
  status: WorkspaceHealthStatus;
  detail: string;
};

export type ValidationItem = {
  id: string;
  label: string;
  status: "pass" | "watch" | "n/a";
  note: string;
};

export function buildWorkspaceHealth(): WorkspaceHealthItem[] {
  const research = getSharedResearchSnapshot();
  const portfolios = getSharedPortfolioSnapshot();
  const reviews = getTeamReviewSnapshot();
  const collab = getCollaborationSnapshot();

  return [
    {
      id: "team",
      label: "Team Workspace",
      href: "/advisor/team",
      status: "healthy",
      detail: `Session shell · ${collab.pinnedItemIds.length} pins · sidebar ${collab.sidebarCollapsed ? "collapsed" : "open"}`,
    },
    {
      id: "research",
      label: "Shared Research",
      href: "/advisor/team/shared-research",
      status: research.bookmarkedIds.length > 0 ? "healthy" : "watch",
      detail: `${listResearchEnvelopes().length} envelopes · ${research.bookmarkedIds.length} bookmarks · ${research.comparisonSessionCount} compare sessions`,
    },
    {
      id: "portfolios",
      label: "Shared Portfolios",
      href: "/advisor/team/shared-portfolios",
      status: "healthy",
      detail: `${seedModelPortfolioLibrary.length} models · ${portfolios.favoriteIds.length} favorites · ${portfolios.comparisonSessionCount} compare sessions`,
    },
    {
      id: "reviews",
      label: "Shared Reviews",
      href: "/advisor/team/shared-reviews",
      status: reviews.reviews.some((r) => r.status === "in_progress") ? "healthy" : "watch",
      detail: `${reviews.reviews.length} reviews · ${reviews.assignments.filter((a) => a.owner !== "Unassigned").length} assigned`,
    },
    {
      id: "assignments",
      label: "Assignments",
      href: "/advisor/team/shared-reviews/board",
      status: "healthy",
      detail: "Assignment board linked to Client Review demos",
    },
    {
      id: "presentations",
      label: "Presentations",
      href: "/advisor/presentations",
      status: seedPresentations.some((p) => p.lifecycle === "active") ? "healthy" : "empty",
      detail: `${seedPresentations.filter((p) => p.lifecycle === "active").length} active packs (demo)`,
    },
  ];
}

export function buildTeamMetrics() {
  const research = buildSharedOverview();
  const portfolioSnap = getSharedPortfolioSnapshot();
  const reviewOverview = buildTeamReviewOverview();
  const reviews = getTeamReviewSnapshot().reviews;
  const activeReviews = reviews.filter((r) => r.status !== "archived");
  const avgReview =
    activeReviews.length === 0
      ? 0
      : Math.round(
          activeReviews.reduce((s, r) => s + checklistCompletionPct(r), 0) /
            activeReviews.length,
        );
  const openTasks = listTasks().filter((t) => t.status !== "done").length;
  const presentationReady = seedPresentations.filter((p) => p.lifecycle === "active").length;
  const meetingReady = reviews.filter((r) =>
    r.checklist.some((c) => c.id === "presentation_ready" && c.done),
  ).length;

  const coverageBits = [
    research.researchCount > 0 ? 1 : 0,
    seedModelPortfolioLibrary.length > 0 ? 1 : 0,
    reviews.length > 0 ? 1 : 0,
    presentationReady > 0 ? 1 : 0,
  ];
  const overall = Math.round((coverageBits.reduce((a, b) => a + b, 0) / coverageBits.length) * 100);

  return {
    researchCoverage: `${research.researchCount} envelopes · ${research.collectionsCount} collections`,
    portfolioCoverage: `${seedModelPortfolioLibrary.length} models · ${portfolioSnap.pinnedIds.length} pinned`,
    reviewCompletion: reviewOverview.averageCompletion,
    assignmentDistribution: `${reviewOverview.assignedReviews} assigned · ${reviewOverview.outstandingAssignments} outstanding`,
    presentationReadiness: `${presentationReady} active packs`,
    meetingReadiness: `${meetingReady} reviews with presentation checklist ready`,
    outstandingWork: `${openTasks} open tasks · ${reviewOverview.pendingReviews} pending reviews`,
    overallCompletionPct: overall,
  };
}

export function buildActivityOverview() {
  const research = getSharedResearchSnapshot();
  const portfolios = getSharedPortfolioSnapshot();
  const reviews = getTeamReviewSnapshot();

  return {
    researchActivity: research.activity.slice(0, 4).map((a) => ({
      id: a.id,
      label: a.label,
      at: a.at,
      href: "/advisor/team/shared-research/activity",
    })),
    portfolioActivity: portfolios.activity.slice(0, 4).map((a) => ({
      id: a.id,
      label: a.label,
      at: a.at,
      href: "/advisor/team/shared-portfolios/activity",
    })),
    reviewActivity: reviews.activity.slice(0, 4).map((a) => ({
      id: a.id,
      label: a.label,
      at: a.at,
      href: "/advisor/team/shared-reviews/activity",
    })),
  };
}

export function buildRecentSessions() {
  const collab = getCollaborationSnapshot();
  const fromNav = collab.recentNavigation.map((n) => ({
    id: `nav-${n.href}-${n.at}`,
    label: n.label,
    at: n.at,
    href: n.href,
  }));
  const defaults = [
    {
      id: "sess-research",
      label: "Shared Research compare session",
      at: "2026-07-22T09:00:00.000Z",
      href: "/advisor/team/shared-research/compare",
    },
    {
      id: "sess-portfolio",
      label: "Shared Portfolio scenario review",
      at: "2026-07-22T08:30:00.000Z",
      href: "/advisor/team/shared-portfolios/scenarios",
    },
    {
      id: "sess-review",
      label: "Assignment board session",
      at: "2026-07-22T08:00:00.000Z",
      href: "/advisor/team/shared-reviews/board",
    },
  ];
  return [...fromNav, ...defaults].slice(0, 8);
}

export function buildCrossWorkspaceLinks() {
  return [
    { href: "/advisor/team", label: "Team Workspace" },
    { href: "/advisor/team/dashboard", label: "Collaboration Dashboard" },
    { href: "/advisor/team/shared-research", label: "Shared Research" },
    { href: "/advisor/team/shared-portfolios", label: "Shared Portfolios" },
    { href: "/advisor/team/shared-reviews", label: "Shared Reviews" },
    { href: "/advisor/team/shared-reviews/board", label: "Assignments" },
    { href: "/advisor/team/activity", label: "Activity" },
    { href: "/advisor/presentations", label: "Presentation Packs" },
    { href: "/advisor/reviews", label: "Client Review Workspace" },
    { href: "/advisor/team/validation", label: "Production Validation" },
  ] as const;
}

export function buildAdvisorPlatformHealth() {
  return ADVISOR_SECTIONS.map((s) => ({
    id: s.id,
    label: s.label,
    href: s.href,
    status: "healthy" as const,
    detail: "Demo surface available when Advisor Demo is enabled",
  }));
}

export function buildProductionValidation(): ValidationItem[] {
  return [
    {
      id: "ws-consistency",
      label: "Workspace consistency",
      status: "pass",
      note: "Team shell + shared research/portfolio/review routes share CollaborationLayout",
    },
    {
      id: "nav-consistency",
      label: "Navigation consistency",
      status: "pass",
      note: "COLLAB_NAV + cross-workspace quick links + breadcrumbs",
    },
    {
      id: "design-system",
      label: "Design system compliance",
      status: "pass",
      note: "Uses shared Card/Button/Badge/Skeleton tokens",
    },
    {
      id: "error-states",
      label: "Error states",
      status: "pass",
      note: "Advisor SectionErrorBoundary + demo gate empty path",
    },
    {
      id: "empty-states",
      label: "Empty states",
      status: "pass",
      note: "EmptyState used across library/compare/activity surfaces",
    },
    {
      id: "loading-states",
      label: "Loading / skeleton screens",
      status: "pass",
      note: "dynamic(..., { ssr: false }) + Skeleton on all team routes",
    },
    {
      id: "responsive",
      label: "Responsive behaviour",
      status: "pass",
      note: "Collapsible sidebar · stacked panels · scrollable boards",
    },
    {
      id: "session-recovery",
      label: "Session recovery",
      status: "watch",
      note: "In-memory only — refresh clears session (by design, no persistence)",
    },
  ];
}

export function buildPerformanceValidation(): ValidationItem[] {
  return [
    {
      id: "lazy-routes",
      label: "Lazy routes",
      status: "pass",
      note: "Team collaboration routes use next/dynamic with ssr:false",
    },
    {
      id: "memoization",
      label: "Memoization",
      status: "pass",
      note: "Dashboard widgets and workspace cards use memo + useMemo",
    },
    {
      id: "windowed",
      label: "Windowed lists",
      status: "pass",
      note: "WindowedList on research/portfolio/review activity feeds",
    },
    {
      id: "bundle",
      label: "Bundle splitting",
      status: "pass",
      note: "Per-route dynamic imports for collaboration modules",
    },
    {
      id: "render",
      label: "Rendering performance",
      status: "pass",
      note: "Presentation-only aggregators; no engine recomputation",
    },
    {
      id: "nav-perf",
      label: "Navigation performance",
      status: "pass",
      note: "Client-side Next.js navigation preserves in-memory session stores",
    },
    {
      id: "dash-render",
      label: "Dashboard rendering",
      status: "pass",
      note: "Lazy-loaded CollaborationDashboard with memoized widgets",
    },
  ];
}

export function buildAccessibilityValidation(): ValidationItem[] {
  return [
    {
      id: "wcag",
      label: "WCAG AA target",
      status: "pass",
      note: "Focus rings, min tap targets, contrast via design tokens",
    },
    {
      id: "keyboard",
      label: "Keyboard navigation",
      status: "pass",
      note: "Board column selects · resize slider keys · focusable controls",
    },
    {
      id: "aria",
      label: "ARIA labels",
      status: "pass",
      note: "Regions, nav landmarks, progressbars, table captions",
    },
    {
      id: "focus",
      label: "Focus management",
      status: "pass",
      note: "Sticky headers preserve context; controls use focus-visible rings",
    },
    {
      id: "sr",
      label: "Screen reader support",
      status: "pass",
      note: "sr-only captions · role=note trust banners · labeled filters",
    },
    {
      id: "contrast",
      label: "High contrast readiness",
      status: "pass",
      note: "Token-based borders/surfaces; avoid low-contrast chrome",
    },
    {
      id: "a11y-dash",
      label: "Accessible dashboards & metrics",
      status: "pass",
      note: "Metric cards use text labels; validation lists are semantic",
    },
  ];
}

export function buildOverallTeamStatus() {
  const health = buildWorkspaceHealth();
  const metrics = buildTeamMetrics();
  const healthy = health.filter((h) => h.status === "healthy").length;
  return {
    label:
      healthy === health.length
        ? "Healthy"
        : healthy >= health.length - 1
          ? "Healthy with watches"
          : "Needs attention",
    detail: `${healthy}/${health.length} workspaces healthy · overall completion ${metrics.overallCompletionPct}%`,
    completionPct: metrics.overallCompletionPct,
  };
}
