/** Primary navigation map — L1.1 + optional Advisor (V2.0 demo gate).
 * EPIC-F003: institutional shell uses `@/lib/shell` SHELL_NAV;
 * this module remains for legacy surfaces and breadcrumb fallbacks.
 */

import { isAdvisorDemoEnabled } from "@/lib/advisor/isAdvisorDemoEnabled";
import { breadcrumbsForPath } from "@/lib/shell/navigationRegistry";

export type NavItem = {
  href: string;
  label: string;
  description: string;
};

const CORE_NAV: readonly NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    description: "Platform overview and health",
  },
  {
    href: "/analysis",
    label: "Analyse",
    description: "Company analysis via the backend API",
  },
  {
    href: "/intelligence",
    label: "Intelligence",
    description: "Composition pipeline over /api/v1",
  },
  {
    href: "/companies",
    label: "Companies",
    description: "Company directory",
  },
  {
    href: "/screening",
    label: "Screening",
    description: "Investment screening",
  },
  {
    href: "/portfolio",
    label: "Portfolio",
    description: "Portfolio intelligence",
  },
  {
    href: "/research",
    label: "Research",
    description: "Company research over composition results",
  },
  {
    href: "/research/institutional",
    label: "Institutional",
    description: "Institutional research reports & explainability workspace",
  },
  {
    href: "/copilot",
    label: "Copilot",
    description: "AI research explainability assistant",
  },
  {
    href: "/documentation",
    label: "Documentation",
    description: "Platform documentation and guides",
  },
  {
    href: "/settings",
    label: "Settings",
    description: "Theme and configuration",
  },
] as const;

const ADVISOR_NAV: NavItem = {
  href: "/advisor",
  label: "Advisor",
  description: "Advisor platform foundation (demo)",
};

/** Full static list for type consumers; prefer getPrimaryNav() for UI. */
export const PRIMARY_NAV: readonly NavItem[] = CORE_NAV;

/** Navigation visible in the shell — Advisor only when demo mode enabled. */
export function getPrimaryNav(): NavItem[] {
  if (!isAdvisorDemoEnabled()) return [...CORE_NAV];
  const insertAt = CORE_NAV.findIndex((n) => n.href === "/settings");
  const next = [...CORE_NAV];
  next.splice(insertAt >= 0 ? insertAt : next.length, 0, ADVISOR_NAV);
  return next;
}

/** Breadcrumbs — delegated to F003 route registry. */
export function breadcrumbsFor(pathname: string): { href: string; label: string }[] {
  return breadcrumbsForPath(pathname);
}
