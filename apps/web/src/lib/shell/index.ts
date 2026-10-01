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
  zipSidebarModel,
  type BreadcrumbCrumb,
  type NavPermissionRule,
  type RouteMeta,
  type ShellNavIconId,
  type ShellNavItem,
  type ZipSidebarModel,
} from "./navigationRegistry";

export { useUiStore, type NavHistoryEntry } from "./uiStore";
