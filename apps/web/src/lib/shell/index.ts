/** EPIC-F003 — Application shell public exports. */

export {
  AUX_ROUTES,
  ROUTE_REGISTRY,
  SECTION_LABELS,
  SHELL_NAV,
  breadcrumbsForPath,
  canAccessNavItem,
  filterShellNav,
  groupShellNav,
  isActivePath,
  searchableRoutes,
} from "./navigationRegistry";

export type {
  BreadcrumbCrumb,
  NavPermissionRule,
  RouteMeta,
  ShellNavIconId,
  ShellNavItem,
} from "./navigationRegistry";

export { useUiStore } from "./uiStore";
export type { NavHistoryEntry } from "./uiStore";
