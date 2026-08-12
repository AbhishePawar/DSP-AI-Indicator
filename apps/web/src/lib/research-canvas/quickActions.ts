/**
 * EPIC-014 — Research Command Palette quick actions.
 * RBAC-filtered like shell sidebar navigation.
 */

import { featureFlags } from "@/lib/featureFlags";
import {
  canAccessNavItem,
  SHELL_NAV,
  type ShellNavItem,
} from "@/lib/shell/navigationRegistry";

export type ResearchQuickAction = {
  id: string;
  label: string;
  keywords: string;
  href: string;
  /** Shell nav id used for RBAC, or null for always-allowed research helpers. */
  navId: string | null;
  requiresFlag?: "researchCanvas" | "researchIntelligence" | "companyComparison";
};

export const RESEARCH_QUICK_ACTIONS: readonly ResearchQuickAction[] = [
  {
    id: "qa-open-company",
    label: "Open Company Analysis",
    keywords: "company analysis open ticker research",
    href: "/analysis",
    navId: "analysis",
  },
  {
    id: "qa-canvas",
    label: "Open Research Canvas",
    keywords: "canvas research os workspace notebook",
    href: "/research/canvas",
    navId: "research",
    requiresFlag: "researchCanvas",
  },
  {
    id: "qa-compare",
    label: "Compare Companies",
    keywords: "compare comparison winner matrix",
    href: "/analysis/compare",
    navId: "analysis",
    requiresFlag: "companyComparison",
  },
  {
    id: "qa-notes",
    label: "Open Research Notes",
    keywords: "notes notebook thesis questions",
    href: "/research/canvas?tab=notes",
    navId: "research",
    requiresFlag: "researchCanvas",
  },
  {
    id: "qa-timeline",
    label: "Open Research Timeline",
    keywords: "timeline history evolution",
    href: "/research/canvas?tab=timeline",
    navId: "research",
    requiresFlag: "researchCanvas",
  },
  {
    id: "qa-portfolio",
    label: "Open Portfolio Intelligence",
    keywords: "portfolio holdings allocation",
    href: "/portfolio",
    navId: "portfolio",
  },
  {
    id: "qa-ri",
    label: "Open Research Intelligence",
    keywords: "intelligence calibration performance validation",
    href: "/research/intelligence",
    navId: "research",
    requiresFlag: "researchIntelligence",
  },
  {
    id: "qa-committee",
    label: "Open AI Committee",
    keywords: "committee ai dissent rationale",
    href: "/research/canvas?tab=committee",
    navId: "research",
    requiresFlag: "researchCanvas",
  },
  {
    id: "qa-export",
    label: "Export Research Package",
    keywords: "export download print pdf package",
    href: "/research/canvas?tab=notes",
    navId: "research",
    requiresFlag: "researchCanvas",
  },
] as const;

function findNav(id: string): ShellNavItem | undefined {
  for (const item of SHELL_NAV) {
    if (item.id === id) return item;
    const child = item.children?.find((c) => c.id === id);
    if (child) return child;
  }
  return undefined;
}

export function filterResearchQuickActions(
  permissions: readonly string[],
  roles: readonly string[],
): ResearchQuickAction[] {
  return RESEARCH_QUICK_ACTIONS.filter((action) => {
    if (action.requiresFlag === "researchCanvas" && !featureFlags.researchCanvas) {
      return false;
    }
    if (
      action.requiresFlag === "researchIntelligence" &&
      !featureFlags.researchIntelligence
    ) {
      return false;
    }
    if (
      action.requiresFlag === "companyComparison" &&
      !featureFlags.companyComparison
    ) {
      return false;
    }
    if (!action.navId) return true;
    const nav = findNav(action.navId);
    if (!nav) return true;
    return canAccessNavItem(nav, permissions, roles);
  });
}
