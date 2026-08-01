/** EPIC-F004 — Institutional dashboard public exports. */

export {
  DASHBOARD_WIDGETS,
  DEFAULT_WIDGET_ORDER,
  widgetMeta,
  type DashboardWidgetId,
  type DashboardWidgetMeta,
} from "./widgetRegistry";

export {
  useDashboardPrefsStore,
  type PinnedCompany,
  type SearchEntry,
} from "./dashboardPrefsStore";
