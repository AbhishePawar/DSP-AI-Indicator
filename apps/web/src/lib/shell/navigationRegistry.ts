/**
 * EPIC-F003 — Navigation registry & route metadata.
 * Shell navigation only — no feature page content.
 */

import { featureFlags } from "@/lib/featureFlags";

export type NavPermissionRule = {
  /** Any of these permissions grants access. Empty = authenticated users. */
  anyOfPermissions?: readonly string[];
  /** Any of these roles grants access (checked if permissions insufficient). */
  anyOfRoles?: readonly string[];
};

export type RouteMeta = {
  id: string;
  path: string;
  title: string;
  description?: string;
  /** Parent path for breadcrumb chain (defaults to /dashboard). */
  parentPath?: string;
  /** Include in Ctrl+K route search. */
  searchable?: boolean;
  group?: string;
  keywords?: string;
};

export type ShellNavItem = {
  id: string;
  href: string;
  label: string;
  description: string;
  section: "overview" | "research" | "ops" | "account";
  icon: ShellNavIconId;
  access?: NavPermissionRule;
  children?: readonly ShellNavItem[];
};

export type ShellNavIconId =
  | "dashboard"
  | "analysis"
  | "portfolio"
  | "research"
  | "admin"
  | "settings"
  | "profile";

/**
 * RC3-003 — Primary shell journey:
 * Dashboard → Company Analysis → Research Workspace → Portfolio → Research Reports
 * IRD is a supporting child under Research Reports, not a competing primary.
 */
export const SHELL_NAV: readonly ShellNavItem[] = [
  {
    id: "dashboard",
    href: "/dashboard",
    label: "Dashboard",
    description: "Executive overview and next investigation steps",
    section: "overview",
    icon: "dashboard",
    children: [
      {
        id: "enterprise-dashboards",
        href: "/dashboards",
        label: "Enterprise Dashboards",
        description:
          "Role-specific research, portfolio, advisor, family office, and executive views",
        section: "overview",
        icon: "dashboard",
      },
    ],
  },
  {
    id: "analysis",
    href: "/analysis",
    label: "Company Analysis",
    description: "Flagship company research workspace over /api/v1/analyse",
    section: "research",
    icon: "analysis",
    access: { anyOfPermissions: ["read_research"] },
    children: [
      {
        id: "analysis-compare",
        href: "/analysis/compare",
        label: "Company Comparison",
        description:
          "Institutional decision workspace — compare 2–5 companies (supporting intelligence)",
        section: "research",
        icon: "analysis",
        access: { anyOfPermissions: ["read_research"] },
      },
    ],
  },
  {
    id: "research",
    href: "/research",
    label: "Research Workspace",
    description: "Research library and session history",
    section: "research",
    icon: "research",
    access: { anyOfPermissions: ["read_research"] },
    children: [
      {
        id: "research-workspace-platform",
        href: "/research/workspace",
        label: "Analyst Workspace",
        description:
          "Institutional notes, folders, bookmarks, templates, versions, and publish workflow",
        section: "research",
        icon: "research",
        access: { anyOfPermissions: ["read_research"] },
      },
      {
        id: "research-canvas",
        href: "/research/canvas",
        label: "Research Canvas",
        description:
          "Institutional Research Operating System — unified navigator, tabs, notebook, and timeline",
        section: "research",
        icon: "research",
        access: { anyOfPermissions: ["read_research"] },
      },
      {
        id: "research-institutional",
        href: "/research/institutional",
        label: "Research Reports",
        description: "Publication and export surface for institutional reports",
        section: "research",
        icon: "research",
        access: { anyOfPermissions: ["read_research"] },
      },
      {
        id: "research-ird",
        href: "/research/institutional/dashboard",
        label: "Research Panels",
        description:
          "Supporting RS panel view — not the primary company research surface",
        section: "research",
        icon: "research",
        access: { anyOfPermissions: ["read_research"] },
      },
      {
        id: "research-intelligence",
        href: "/research/intelligence",
        label: "Research Intelligence",
        description:
          "Research performance, calibration, and outcome validation (measurement only)",
        section: "research",
        icon: "research",
        access: { anyOfPermissions: ["read_research"] },
      },
    ],
  },
  {
    id: "portfolio",
    href: "/portfolio",
    label: "Portfolio",
    description: "Portfolio coverage and intelligence (session + API)",
    section: "research",
    icon: "portfolio",
    access: {
      anyOfPermissions: ["read_research"],
      anyOfRoles: ["portfolio_manager", "administrator"],
    },
  },
  {
    id: "admin",
    href: "/admin",
    label: "Administration",
    description: "Enterprise administration",
    section: "ops",
    icon: "admin",
    access: {
      anyOfPermissions: [
        "manage_users",
        "manage_roles",
        "configure_platform",
        "view_audit",
        "admin.view",
        "admin.manage",
      ],
      anyOfRoles: ["administrator", "owner"],
    },
  },
  {
    id: "saas",
    href: "/saas",
    label: "SaaS Platform",
    description:
      "Commercial multi-tenant orgs, plans, licensing, billing profiles, and usage",
    section: "ops",
    icon: "admin",
    access: {
      anyOfPermissions: [
        "admin.view",
        "admin.manage",
        "org.manage",
        "configure_platform",
      ],
      anyOfRoles: ["owner", "administrator"],
    },
  },
  {
    id: "portal",
    href: "/portal",
    label: "Customer Portal",
    description: "Organization, licenses, members, usage, and API keys",
    section: "ops",
    icon: "settings",
    access: {
      anyOfPermissions: ["org.view", "manage_users", "configure_platform"],
      anyOfRoles: ["owner", "administrator"],
    },
  },
  {
    id: "ops",
    href: "/ops",
    label: "Operations",
    description: "Enterprise health, incidents, and operational dashboard",
    section: "ops",
    icon: "admin",
    access: {
      anyOfPermissions: ["ops.view", "configure_platform", "admin.view"],
      anyOfRoles: ["administrator", "owner"],
    },
  },
  {
    id: "control-center",
    href: "/control-center",
    label: "Control Center",
    description:
      "Super Admin configuration registry, branding, flags, rules, and platform OS",
    section: "ops",
    icon: "admin",
    access: {
      anyOfPermissions: [
        "configure_platform",
        "admin.manage",
        "admin.view",
        "manage_roles",
      ],
      anyOfRoles: ["administrator", "owner"],
    },
  },
  {
    id: "settings",
    href: "/settings",
    label: "Settings",
    description: "Preferences and configuration",
    section: "account",
    icon: "settings",
  },
  {
    id: "profile",
    href: "/profile",
    label: "Profile",
    description: "Identity and sessions",
    section: "account",
    icon: "profile",
  },
] as const;

export const SECTION_LABELS: Record<ShellNavItem["section"], string> = {
  overview: "Overview",
  research: "Research",
  ops: "Operations",
  account: "Account",
};

/**
 * Extra breadcrumb routes (legacy / unfinished).
 * RC3-003 — not searchable in the command palette (hide unfinished surfaces).
 */
export const AUX_ROUTES: readonly RouteMeta[] = [
  {
    id: "intelligence",
    path: "/intelligence",
    title: "Intelligence",
    searchable: false,
    group: "Workspace",
  },
  {
    id: "companies",
    path: "/companies",
    title: "Companies",
    searchable: false,
    group: "Workspace",
  },
  {
    id: "screening",
    path: "/screening",
    title: "Screening",
    searchable: false,
    group: "Workspace",
  },
  {
    id: "copilot",
    path: "/copilot",
    title: "Copilot",
    searchable: false,
    group: "Workspace",
  },
  {
    id: "documentation",
    path: "/documentation",
    title: "Documentation",
    searchable: true,
    group: "Help",
  },
  {
    id: "health",
    path: "/health",
    title: "Health",
    searchable: false,
    group: "Ops",
  },
  {
    id: "diagnostics",
    path: "/diagnostics",
    title: "Diagnostics",
    searchable: false,
    group: "Ops",
  },
  {
    id: "portal-meta",
    path: "/portal",
    title: "Customer Portal",
    searchable: featureFlags.enterprisePortal,
    group: "Ops",
  },
  {
    id: "ops-meta",
    path: "/ops",
    title: "Operations",
    searchable: featureFlags.enterpriseOps,
    group: "Ops",
  },
  {
    id: "platform",
    path: "/platform",
    title: "Platform",
    searchable: false,
    group: "Ops",
  },
  {
    id: "advisor",
    path: "/advisor",
    title: "Advisor",
    searchable: false,
    group: "Workspace",
  },
  {
    id: "reports",
    path: "/reports",
    title: "Legacy Reports",
    searchable: false,
    group: "Workspace",
  },
  {
    id: "beta",
    path: "/beta",
    title: "Private Beta",
    searchable: false,
    group: "Workspace",
  },
  {
    id: "docs",
    path: "/docs",
    title: "Docs",
    searchable: true,
    group: "Help",
  },
  {
    id: "launch",
    path: "/launch",
    title: "Launch",
    searchable: false,
    group: "Ops",
  },
] as const;

function flattenShell(
  items: readonly ShellNavItem[],
  parentPath = "/dashboard",
): RouteMeta[] {
  const out: RouteMeta[] = [];
  for (const item of items) {
    out.push({
      id: item.id,
      path: item.href,
      title: item.label,
      description: item.description,
      parentPath,
      searchable: true,
      group: SECTION_LABELS[item.section],
      keywords: item.description,
    });
    if (item.children?.length) {
      out.push(...flattenShell(item.children, item.href));
    }
  }
  return out;
}

export const ROUTE_REGISTRY: readonly RouteMeta[] = [
  {
    id: "home",
    path: "/dashboard",
    title: "Home",
    searchable: false,
  },
  ...flattenShell(SHELL_NAV),
  ...AUX_ROUTES,
];

function isAdminGated(rule: NavPermissionRule): boolean {
  const adminPerms = new Set([
    "manage_users",
    "manage_roles",
    "configure_platform",
    "view_audit",
  ]);
  return (
    rule.anyOfPermissions?.some((p) => adminPerms.has(p)) === true ||
    rule.anyOfRoles?.includes("administrator") === true
  );
}

export function canAccessNavItem(
  item: ShellNavItem,
  permissions: readonly string[],
  roles: readonly string[],
): boolean {
  const rule = item.access;
  if (!rule) return true;
  const perms = new Set(permissions.map((p) => p.toLowerCase()));
  const roleSet = new Set(roles.map((r) => r.toLowerCase()));
  if (rule.anyOfPermissions?.some((p) => perms.has(p.toLowerCase()))) {
    return true;
  }
  if (rule.anyOfRoles?.some((r) => roleSet.has(r.toLowerCase()))) {
    return true;
  }
  // Legacy sessions without RBAC claims: show research shell, hide admin.
  if (permissions.length === 0 && !isAdminGated(rule)) {
    return true;
  }
  return false;
}

export function filterShellNav(
  permissions: readonly string[],
  roles: readonly string[],
): ShellNavItem[] {
  return SHELL_NAV.map((item) => {
    if (!canAccessNavItem(item, permissions, roles)) return null;
    // EPS-002 — feature-flagged enterprise surfaces
    if (item.id === "portal" && !featureFlags.enterprisePortal) return null;
    if (item.id === "ops" && !featureFlags.enterpriseOps) return null;
    if (item.id === "admin" && !featureFlags.enterpriseAdmin) return null;
    const children = item.children?.filter((c) => {
      if (!canAccessNavItem(c, permissions, roles)) return false;
      // EPIC-011B — hide unfinished / flagged-off Research Intelligence
      if (c.id === "research-intelligence" && !featureFlags.researchIntelligence) {
        return false;
      }
      // EPIC-012/013 — hide flagged-off Company Comparison
      if (c.id === "analysis-compare" && !featureFlags.companyComparison) {
        return false;
      }
      // EPIC-014 — hide flagged-off Research Canvas
      if (c.id === "research-canvas" && !featureFlags.researchCanvas) {
        return false;
      }
      return true;
    });
    return children ? { ...item, children } : item;
  }).filter((item): item is ShellNavItem => item !== null);
}

export function groupShellNav(
  items: readonly ShellNavItem[],
): { section: ShellNavItem["section"]; label: string; items: ShellNavItem[] }[] {
  const order: ShellNavItem["section"][] = [
    "overview",
    "research",
    "ops",
    "account",
  ];
  return order
    .map((section) => ({
      section,
      label: SECTION_LABELS[section],
      items: items.filter((i) => i.section === section),
    }))
    .filter((g) => g.items.length > 0);
}

export type BreadcrumbCrumb = { href: string; label: string };

function findRouteMeta(pathname: string): RouteMeta | undefined {
  const sorted = [...ROUTE_REGISTRY].sort(
    (a, b) => b.path.length - a.path.length,
  );
  return sorted.find(
    (r) => pathname === r.path || pathname.startsWith(`${r.path}/`),
  );
}

export function breadcrumbsForPath(pathname: string): BreadcrumbCrumb[] {
  const crumbs: BreadcrumbCrumb[] = [
    { href: "/dashboard", label: "Home" },
  ];
  if (pathname === "/dashboard" || pathname === "/") {
    return crumbs;
  }

  const match = findRouteMeta(pathname);
  if (!match || match.path === "/dashboard") {
    // Dynamic research ticker
    if (
      pathname.startsWith("/research/") &&
      !pathname.startsWith("/research/institutional") &&
      !pathname.startsWith("/research/intelligence") &&
      !pathname.startsWith("/research/canvas")
    ) {
      crumbs.push({ href: "/research", label: "Research Workspace" });
      const ticker = pathname.split("/")[2];
      if (ticker) {
        crumbs.push({
          href: pathname,
          label: decodeURIComponent(ticker).toUpperCase(),
        });
      }
      return crumbs;
    }
    if (pathname.startsWith("/advisor/clients/")) {
      crumbs.push({ href: "/advisor", label: "Advisor" });
      crumbs.push({ href: pathname, label: "Client" });
      return crumbs;
    }
    if (pathname.startsWith("/reports/")) {
      crumbs.push({ href: "/reports", label: "Reports" });
      crumbs.push({ href: pathname, label: "Report" });
      return crumbs;
    }
    const segment = pathname.split("/").filter(Boolean).pop();
    if (segment) {
      crumbs.push({
        href: pathname,
        label: segment.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      });
    }
    return crumbs;
  }

  if (match.parentPath && match.parentPath !== "/dashboard") {
    const parent = ROUTE_REGISTRY.find((r) => r.path === match.parentPath);
    if (parent && parent.path !== "/dashboard") {
      crumbs.push({ href: parent.path, label: parent.title });
    }
  }

  crumbs.push({ href: match.path, label: match.title });

  if (
    match.path === "/research" &&
    pathname.startsWith("/research/") &&
    !pathname.startsWith("/research/institutional") &&
    !pathname.startsWith("/research/intelligence") &&
    !pathname.startsWith("/research/canvas")
  ) {
    const ticker = pathname.split("/")[2];
    if (ticker) {
      crumbs.push({
        href: pathname,
        label: decodeURIComponent(ticker).toUpperCase(),
      });
    }
  }

  return crumbs;
}

/**
 * RC3-003 — Command palette routes: shell-primary + help only, RBAC-filtered
 * like the sidebar. Unfinished AUX destinations are not searchable.
 */
export function searchableRoutes(
  permissions: readonly string[] = [],
  roles: readonly string[] = [],
): RouteMeta[] {
  const visibleShell = filterShellNav(permissions, roles);
  const allowedPaths = new Set<string>();
  const walk = (items: readonly ShellNavItem[]) => {
    for (const item of items) {
      allowedPaths.add(item.href);
      if (item.children?.length) walk(item.children);
    }
  };
  walk(visibleShell);

  return ROUTE_REGISTRY.filter((r) => {
    if (r.searchable === false) return false;
    if (r.path === "/dashboard") return false;
    if (r.group === "Help") return true;
    return allowedPaths.has(r.path);
  });
}

export function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
