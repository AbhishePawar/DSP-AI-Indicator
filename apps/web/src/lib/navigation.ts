/** Primary navigation map — L1.1 + optional Advisor (V2.0 demo gate). */

import { isAdvisorDemoEnabled } from "@/lib/advisor/isAdvisorDemoEnabled";

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

export function breadcrumbsFor(pathname: string): { href: string; label: string }[] {
  const crumbs: { href: string; label: string }[] = [
    { href: "/dashboard", label: "Home" },
  ];
  if (pathname === "/dashboard" || pathname === "/") {
    return crumbs;
  }
  const nav = getPrimaryNav();
  const match = nav.find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
  );
  if (match) {
    crumbs.push({ href: match.href, label: match.label });
    if (pathname.startsWith("/advisor/clients/") && pathname !== "/advisor/clients") {
      crumbs.push({ href: pathname, label: "Client" });
    }
    if (match.href === "/research" && pathname.startsWith("/research/")) {
      const ticker = pathname.split("/")[2];
      if (ticker) {
        crumbs.push({
          href: pathname,
          label: decodeURIComponent(ticker).toUpperCase(),
        });
      }
    }
  } else if (pathname === "/health") {
    crumbs.push({ href: "/health", label: "Health" });
  } else if (pathname === "/diagnostics") {
    crumbs.push({ href: "/diagnostics", label: "Diagnostics" });
  } else if (pathname === "/profile") {
    crumbs.push({ href: "/profile", label: "Profile" });
  } else if (pathname === "/intelligence") {
    crumbs.push({ href: "/intelligence", label: "Intelligence" });
  } else if (pathname === "/companies") {
    crumbs.push({ href: "/companies", label: "Companies" });
  } else if (pathname === "/screening") {
    crumbs.push({ href: "/screening", label: "Screening" });
  } else if (pathname === "/documentation") {
    crumbs.push({ href: "/documentation", label: "Documentation" });
  } else if (pathname === "/platform") {
    crumbs.push({ href: "/platform", label: "Platform" });
  } else if (pathname.startsWith("/reports/")) {
    crumbs.push({ href: "/reports", label: "Reports" });
    crumbs.push({ href: pathname, label: "Report" });
  } else if (pathname.startsWith("/launch")) {
    crumbs.push({ href: "/launch", label: "Launch" });
  } else if (pathname.startsWith("/docs")) {
    crumbs.push({ href: "/docs", label: "Docs" });
  } else if (pathname.startsWith("/beta")) {
    crumbs.push({ href: "/beta", label: "Private Beta" });
  } else if (pathname.startsWith("/advisor")) {
    crumbs.push({ href: "/advisor", label: "Advisor" });
  }
  return crumbs;
}
