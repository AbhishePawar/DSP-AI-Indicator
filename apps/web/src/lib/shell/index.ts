/** EPIC-F003 — Application shell public exports. */

export {
  AUX_ROUTES,
  ORDINARY_SHELL_NAV,
  ROUTE_REGISTRY,
  SECTION_LABELS,
  SHELL_NAV,
  breadcrumbsForPath,
  canAccessNavItem,
  filterShellNav,
  groupShellNav,
  isActivePath,
  resolveShellAudience,
  searchableRoutes,
  type BreadcrumbCrumb,
  type NavPermissionRule,
  type RouteMeta,
  type ShellAudience,
  type ShellNavIconId,
  type ShellNavItem,
} from "./navigationRegistry";

export { useUiStore, type NavHistoryEntry } from "./uiStore";
