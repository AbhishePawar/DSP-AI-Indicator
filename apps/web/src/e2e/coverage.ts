/**
 * EPIC-F011 — End-to-end coverage catalogue (frontend journeys only).
 * No backend or business-logic changes.
 */

export type E2EJourneyId =
  | "auth_rbac"
  | "dashboard"
  | "company_analysis"
  | "portfolio"
  | "research"
  | "admin"
  | "settings"
  | "navigation_routing"
  | "api_integration"
  | "error_handling"
  | "loading_empty"
  | "responsive_regression"
  | "accessibility_regression"
  | "cross_browser"
  | "performance_smoke";

export type E2EJourneyMeta = {
  id: E2EJourneyId;
  label: string;
  routes: readonly string[];
  automated: boolean;
  notes: string;
};

export const E2E_JOURNEYS: readonly E2EJourneyMeta[] = [
  {
    id: "auth_rbac",
    label: "Authentication & RBAC",
    routes: ["/login", "/unauthorized", "/forbidden", "/session-expired"],
    automated: true,
    notes: "Route guards, nav permission filters, login form a11y",
  },
  {
    id: "dashboard",
    label: "Dashboard",
    routes: ["/dashboard"],
    automated: true,
    notes: "Layout region + widget prefs store smoke",
  },
  {
    id: "company_analysis",
    label: "Company Analysis",
    routes: ["/analysis"],
    automated: true,
    notes: "Workspace chrome + analyse client contract",
  },
  {
    id: "portfolio",
    label: "Portfolio",
    routes: ["/portfolio"],
    automated: true,
    notes: "Protected route + holdings display contract",
  },
  {
    id: "research",
    label: "Research",
    routes: ["/research", "/research/institutional"],
    automated: true,
    notes: "Library/viewer sections + honest empty diff",
  },
  {
    id: "admin",
    label: "Administration",
    routes: ["/admin"],
    automated: true,
    notes: "A010 admin client surface + RBAC gate",
  },
  {
    id: "settings",
    label: "Settings",
    routes: ["/settings", "/profile"],
    automated: true,
    notes: "Preferences persistence + about versions",
  },
  {
    id: "navigation_routing",
    label: "Navigation & routing",
    routes: ["/dashboard", "/analysis", "/portfolio", "/research", "/admin", "/settings"],
    automated: true,
    notes: "Shell nav registry, breadcrumbs, searchable routes",
  },
  {
    id: "api_integration",
    label: "API integration",
    routes: [],
    automated: true,
    notes: "Frozen /api/v1 client methods present; thin-client rules",
  },
  {
    id: "error_handling",
    label: "Error handling",
    routes: [],
    automated: true,
    notes: "ApiClientError + Data unavailable messaging",
  },
  {
    id: "loading_empty",
    label: "Loading / empty states",
    routes: [],
    automated: true,
    notes: "resolveListState + workspace empty copy",
  },
  {
    id: "responsive_regression",
    label: "Responsive regression",
    routes: [],
    automated: true,
    notes: "F010 viewport catalogue + panel collapse",
  },
  {
    id: "accessibility_regression",
    label: "Accessibility regression",
    routes: [],
    automated: true,
    notes: "Landmarks, skip target, appearance datasets",
  },
  {
    id: "cross_browser",
    label: "Cross-browser validation",
    routes: [],
    automated: true,
    notes: "Baseline web platform features used by the thin client",
  },
  {
    id: "performance_smoke",
    label: "Performance smoke",
    routes: [],
    automated: true,
    notes: "Critical module import budget",
  },
] as const;

export const E2E_CRITICAL_ROUTES = [
  "/login",
  "/dashboard",
  "/analysis",
  "/portfolio",
  "/research",
  "/admin",
  "/settings",
  "/profile",
] as const;

export function journeyById(id: E2EJourneyId): E2EJourneyMeta {
  const found = E2E_JOURNEYS.find((j) => j.id === id);
  if (!found) throw new Error(`Unknown journey: ${id}`);
  return found;
}
