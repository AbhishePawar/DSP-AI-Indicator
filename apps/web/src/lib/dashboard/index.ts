/** EPIC-F004 — Institutional dashboard public exports. */

export {
  DASHBOARD_WIDGETS,
  DEFAULT_HIDDEN_WIDGETS,
  DEFAULT_WIDGET_ORDER,
  widgetMeta,
} from "./widgetRegistry";

export type { DashboardWidgetId, DashboardWidgetMeta } from "./widgetRegistry";

export { useDashboardPrefsStore } from "./dashboardPrefsStore";

export type { PinnedCompany, SearchEntry } from "./dashboardPrefsStore";
