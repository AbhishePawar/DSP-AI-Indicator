/**
 * Sprint 7.1 — Team Collaboration Foundation types (session-only).
 */

export type CollaborationWorkspaceKind = "my" | "shared";

export type CollaborationNavId =
  | "overview"
  | "dashboard"
  | "my_work"
  | "shared_research"
  | "shared_reviews"
  | "shared_portfolios"
  | "discussions"
  | "assignments"
  | "activity"
  | "validation";

export type CollaborationPanelId = "sidebar" | "main" | "context";

export type CollaborationSessionState = {
  selectedWorkspace: CollaborationWorkspaceKind;
  sidebarCollapsed: boolean;
  expandedPanels: Record<CollaborationPanelId, boolean>;
  pinnedItemIds: string[];
  recentNavigation: { href: string; label: string; at: string }[];
  workspaceFilter: string;
  mainPanelWidthPct: number;
};

export type CollaborationActivityItem = {
  id: string;
  label: string;
  kind: string;
  at: string;
  href: string;
};

export type CollaborationPinnedItem = {
  id: string;
  label: string;
  href: string;
  kind: string;
};

export const COLLAB_NAV: {
  id: CollaborationNavId;
  href: string;
  label: string;
}[] = [
  { id: "overview", href: "/advisor/team", label: "Workspace Overview" },
  { id: "dashboard", href: "/advisor/team/dashboard", label: "Collaboration Dashboard" },
  { id: "my_work", href: "/advisor/team/my-work", label: "My Work" },
  { id: "shared_research", href: "/advisor/team/shared-research", label: "Shared Research" },
  { id: "shared_reviews", href: "/advisor/team/shared-reviews", label: "Shared Reviews" },
  { id: "shared_portfolios", href: "/advisor/team/shared-portfolios", label: "Shared Portfolios" },
  { id: "discussions", href: "/advisor/team/discussions", label: "Discussions" },
  { id: "assignments", href: "/advisor/team/shared-reviews/board", label: "Assignments" },
  { id: "activity", href: "/advisor/team/activity", label: "Activity" },
  { id: "validation", href: "/advisor/team/validation", label: "Production Validation" },
];

export const DEFAULT_COLLAB_SESSION: CollaborationSessionState = {
  selectedWorkspace: "my",
  sidebarCollapsed: false,
  expandedPanels: { sidebar: true, main: true, context: true },
  pinnedItemIds: ["pin-research", "pin-review", "pin-portfolio"],
  recentNavigation: [],
  workspaceFilter: "",
  mainPanelWidthPct: 70,
};
