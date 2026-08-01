/**
 * EPIC-F003 — Navigation registry & route metadata.
 * Shell navigation only — no feature page content.
 */

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

/** Institutional primary shell (F003 checklist). */
export const SHELL_NAV: readonly ShellNavItem[] = [
  {
    id: "dashboard",
    href: "/dashboard",
    label: "Dashboard",
    description: "Institutional overview",
    section: "overview",
    icon: "dashboard",
  },
  {
    id: "analysis",
    href: "/analysis",
    label: "Company Analysis",
    description: "Company analysis via the backend API",
    section: "research",
    icon: "analysis",
    access: { anyOfPermissions: ["read_research"] },
  },
  {
    id: "portfolio",
    href: "/portfolio",
    label: "Portfolio",
    description: "Portfolio intelligence",
    section: "research",
    icon: "portfolio",
    access: {
      anyOfPermissions: ["read_research"],
      anyOfRoles: ["portfolio_manager", "administrator"],
    },
  },
  {
    id: "research",
    href: "/research",
    label: "Research Workspace",
    description: "Research Mode workspace",
    section: "research",
    icon: "research",
    access: { anyOfPermissions: ["read_research"] },
    children: [
      {
        id: "research-institutional",
        href: "/research/institutional",
        label: "Institutional",
        description: "Institutional research reports & explainability",
        section: "research",
        icon: "research",
        access: { anyOfPermissions: ["read_research"] },
      },
    ],
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
      ],
      anyOfRoles: ["administrator"],
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

/** Extra searchable / breadcrumb routes (legacy surfaces — not primary shell). */
export const AUX_ROUTES: readonly RouteMeta[] = [
  {
    id: "intelligence",
    path: "/intelligence",
    title: "Intelligence",
    searchable: true,
    group: "Workspace",
    keywords: "composition pipeline",
  },
  {
    id: "companies",
    path: "/companies",
    title: "Companies",
    searchable: true,
    group: "Workspace",
  },
  {
    id: "screening",
    path: "/screening",
    title: "Screening",
    searchable: true,
    group: "Workspace",
  },
  {
    id: "copilot",
    path: "/copilot",
    title: "Copilot",
    searchable: true,
    group: "Workspace",
    keywords: "ai assistant",
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
    searchable: true,
    group: "Ops",
  },
  {
    id: "diagnostics",
    path: "/diagnostics",
    title: "Diagnostics",
    searchable: true,
    group: "Ops",
  },
  {
    id: "platform",
    path: "/platform",
    title: "Platform",
    searchable: true,
    group: "Ops",
  },
  {
    id: "advisor",
    path: "/advisor",
    title: "Advisor",
    searchable: true,
    group: "Workspace",
  },
  {
    id: "reports",
    path: "/reports",
    title: "Reports",
    searchable: true,
    group: "Workspace",
  },
  {
    id: "beta",
    path: "/beta",
    title: "Private Beta",
    searchable: true,
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
    searchable: true,
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
    const children = item.children?.filter((c) =>
      canAccessNavItem(c, permissions, roles),
    );
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
    if (pathname.startsWith("/research/") && !pathname.startsWith("/research/institutional")) {
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
    !pathname.startsWith("/research/institutional")
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

export function searchableRoutes(): RouteMeta[] {
  return ROUTE_REGISTRY.filter((r) => r.searchable !== false && r.path !== "/dashboard");
}

export function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
