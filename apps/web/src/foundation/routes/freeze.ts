/**
 * EPIC-F000 — Route freeze map.
 * Routes below are DEFINED for F-series implementation — DO NOT build in F000.
 * Existing `src/app/**` production routes remain untouched.
 */

export type FrozenRouteStatus = "frozen" | "existing_legacy" | "deferred";

export type FrozenRoute = {
  path: string;
  group: "(app)" | "(auth)" | "(marketing)" | "(admin)";
  title: string;
  status: FrozenRouteStatus;
  epic: string;
  notes: string;
};

/**
 * F-series target IA (PR1.1 aligned). Implementation starts F001+.
 * Status `frozen` = specified only; no new page work in F000.
 */
export const FROZEN_FEATURE_ROUTES: readonly FrozenRoute[] = [
  {
    path: "/dashboard",
    group: "(app)",
    title: "Dashboard",
    status: "frozen",
    epic: "F002+",
    notes: "Institutional overview — define only in F000",
  },
  {
    path: "/analysis",
    group: "(app)",
    title: "Company Analysis",
    status: "frozen",
    epic: "F003+",
    notes: "Thin client over /api/v1 analyse — no engine calls in browser",
  },
  {
    path: "/portfolio",
    group: "(app)",
    title: "Portfolio",
    status: "frozen",
    epic: "F004+",
    notes: "Portfolio intelligence surfaces only",
  },
  {
    path: "/research",
    group: "(app)",
    title: "Research Workspace",
    status: "frozen",
    epic: "F005+",
    notes: "Research Mode first; immutable artifacts",
  },
  {
    path: "/admin",
    group: "(admin)",
    title: "Administration",
    status: "frozen",
    epic: "F008",
    notes: "Consumes A010 /admin/* — EPIC-F008 Administration Console",
  },
  {
    path: "/settings",
    group: "(app)",
    title: "Settings",
    status: "frozen",
    epic: "F009",
    notes: "UI preferences + account display — EPIC-F009",
  },
  {
    path: "/profile",
    group: "(app)",
    title: "Profile",
    status: "frozen",
    epic: "F009",
    notes: "Identity from A009 /auth/rbac/me",
  },
  {
    path: "/login",
    group: "(auth)",
    title: "Login",
    status: "existing_legacy",
    epic: "F000",
    notes: "JWT via existing backend /auth APIs — keep current flow",
  },
] as const;

/** Planned App Router groups — structural target for F001+. */
export const ROUTE_GROUPS = {
  auth: {
    id: "(auth)",
    purpose: "Unauthenticated shell — login / recovery",
    layout: "minimal (no sidebar)",
  },
  app: {
    id: "(app)",
    purpose: "Authenticated research application shell",
    layout: "sidebar + header + main + footer",
  },
  admin: {
    id: "(admin)",
    purpose: "Enterprise admin console (A010)",
    layout: "admin sidebar + header",
  },
  marketing: {
    id: "(marketing)",
    purpose: "Public marketing / docs entry (optional)",
    layout: "marketing header only",
  },
} as const;
