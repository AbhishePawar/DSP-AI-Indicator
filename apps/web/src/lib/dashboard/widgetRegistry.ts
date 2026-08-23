/**
 * P9.3 / EPIC-004 — Executive Dashboard widget registry (layout only).
 */

export type DashboardWidgetId =
  | "welcome"
  | "attention_brief"
  | "quick_actions"
  | "market_overview"
  | "portfolio_summary"
  | "watchlist_summary"
  | "valuation_summary"
  | "business_quality_summary"
  | "risk_summary"
  | "research_activity"
  | "research_reports"
  | "committee_activity"
  | "notifications"
  | "tasks"
  | "company_search"
  | "recent_companies"
  | "pinned_companies"
  | "recent_research"
  | "archive_snapshots"
  | "research_diff"
  | "research_alerts"
  | "portfolio_activity"
  | "compliance_summary"
  | "workflow_summary"
  | "copilot_activity"
  | "platform_health"
  | "background_jobs"
  | "api_status"
  | "documentation"
  | "global_search"
  | "recent_searches"
  | "saved_searches"
  /** EPIC-014 — Research Command Center */
  | "research_command_center";

export type DashboardWidgetMeta = {
  id: DashboardWidgetId;
  title: string;
  section:
    | "personal"
    | "attention"
    | "company"
    | "portfolio"
    | "research"
    | "insight"
    | "ai"
    | "system"
    | "search";
  /** Grid span hint */
  span: 1 | 2;
  description: string;
  /** Prefer deferred mount for heavier widgets */
  lazy?: boolean;
};

export const DASHBOARD_WIDGETS: readonly DashboardWidgetMeta[] = [
  {
    id: "welcome",
    title: "Welcome",
    section: "personal",
    span: 2,
    description: "Personal greeting and session context",
  },
  {
    id: "attention_brief",
    title: "Needs attention",
    section: "attention",
    span: 2,
    description: "What requires investigation today — honest status only",
  },
  {
    id: "quick_actions",
    title: "Quick Actions",
    section: "personal",
    span: 2,
    description: "Primary workspace shortcuts",
  },
  {
    id: "market_overview",
    title: "Market Overview",
    section: "insight",
    span: 1,
    description: "GET /api/v1/market/health",
    lazy: true,
  },
  {
    id: "portfolio_summary",
    title: "Portfolio Snapshot",
    section: "portfolio",
    span: 1,
    description: "Open Portfolio workspace — no invented metrics",
  },
  {
    id: "watchlist_summary",
    title: "Watchlist Summary",
    section: "portfolio",
    span: 1,
    description: "Open Portfolio workspace",
  },
  {
    id: "valuation_summary",
    title: "Valuation Summary",
    section: "insight",
    span: 1,
    description: "Navigate to analysis — no client valuation",
  },
  {
    id: "business_quality_summary",
    title: "Business Quality Summary",
    section: "insight",
    span: 1,
    description: "Navigate to analysis — no fabricated scores",
  },
  {
    id: "risk_summary",
    title: "Risk Summary",
    section: "insight",
    span: 1,
    description: "Navigate to analysis — no fabricated risk ranks",
  },
  {
    id: "research_activity",
    title: "Research Activity",
    section: "research",
    span: 1,
    description: "Local research history signals",
  },
  {
    id: "research_reports",
    title: "Recent Reports",
    section: "research",
    span: 2,
    description: "GET /api/v1/report/{id}",
    lazy: true,
  },
  {
    id: "committee_activity",
    title: "Recent AI Committee Decisions",
    section: "ai",
    span: 1,
    description: "Committee list API may be unavailable",
    lazy: true,
  },
  {
    id: "notifications",
    title: "Notifications",
    section: "attention",
    span: 1,
    description: "No notifications feed API in v1 — honest empty",
  },
  {
    id: "tasks",
    title: "Tasks",
    section: "attention",
    span: 1,
    description: "No tasks API in v1 — investigation checklist links",
  },
  {
    id: "global_search",
    title: "Search",
    section: "search",
    span: 1,
    description: "Opens command palette",
  },
  {
    id: "company_search",
    title: "Quick Company Search",
    section: "company",
    span: 1,
    description: "Jump to Company Analysis",
  },
  {
    id: "recent_companies",
    title: "Recently Viewed Companies",
    section: "company",
    span: 1,
    description: "From local analysis history",
    lazy: true,
  },
  {
    id: "pinned_companies",
    title: "Pinned Companies",
    section: "company",
    span: 1,
    description: "User pins (local preferences)",
  },
  {
    id: "recent_research",
    title: "Recent Research",
    section: "research",
    span: 1,
    description: "Local research history",
    lazy: true,
  },
  {
    id: "archive_snapshots",
    title: "Latest Archive Snapshots",
    section: "research",
    span: 1,
    description: "Requires archive API — none in v1",
  },
  {
    id: "research_diff",
    title: "Recent Research Diff",
    section: "research",
    span: 1,
    description: "Requires diff API — none in v1",
  },
  {
    id: "research_alerts",
    title: "Research Monitoring Alerts",
    section: "research",
    span: 1,
    description: "Presentation flag + empty until API",
  },
  {
    id: "portfolio_activity",
    title: "Recent Portfolio Activity",
    section: "portfolio",
    span: 1,
    description: "No activity feed API in v1",
  },
  {
    id: "compliance_summary",
    title: "Compliance Summary",
    section: "ai",
    span: 1,
    description: "Feature-flag presentation only",
  },
  {
    id: "workflow_summary",
    title: "Workflow Summary",
    section: "ai",
    span: 1,
    description: "No workflow list API in client",
  },
  {
    id: "copilot_activity",
    title: "Copilot Activity",
    section: "ai",
    span: 1,
    description: "GET /api/v1/copilot/providers",
    lazy: true,
  },
  {
    id: "platform_health",
    title: "Platform Health",
    section: "system",
    span: 1,
    description: "GET /api/v1/health + subsystem health",
    lazy: true,
  },
  {
    id: "api_status",
    title: "API Status",
    section: "system",
    span: 1,
    description: "GET /api/v1/health · /version · /capabilities",
    lazy: true,
  },
  {
    id: "background_jobs",
    title: "Background Jobs",
    section: "system",
    span: 1,
    description: "UI only — no jobs API in v1",
  },
  {
    id: "documentation",
    title: "Documentation",
    section: "system",
    span: 1,
    description: "Docs and guides",
  },
  {
    id: "recent_searches",
    title: "Recent Searches",
    section: "search",
    span: 1,
    description: "Local search history",
  },
  {
    id: "saved_searches",
    title: "Saved Searches",
    section: "search",
    span: 1,
    description: "UI only preferences",
  },
  {
    id: "research_command_center",
    title: "Research Command Center",
    section: "research",
    span: 2,
    description:
      "Open research, portfolio status, coverage, comparisons, RI, committee, notes, watchlist",
    lazy: true,
  },
] as const;

/**
 * RC3-003 — Executive default: meaningful widgets only.
 * Hollow insight stubs and unfinished AUX remain in the registry for customize,
 * but start hidden via DEFAULT_HIDDEN_WIDGETS.
 */
export const DEFAULT_WIDGET_ORDER: DashboardWidgetId[] = [
  "welcome",
  "attention_brief",
  "research_command_center",
  "market_overview",
  "company_search",
  "global_search",
  "recent_companies",
  "pinned_companies",
  "portfolio_summary",
  "watchlist_summary",
  "portfolio_activity",
  "research_activity",
  "research_reports",
  "recent_research",
  "committee_activity",
  "platform_health",
  "api_status",
  "documentation",
  "recent_searches",
  // Remaining registry ids keep customize/order support:
  "valuation_summary",
  "business_quality_summary",
  "risk_summary",
  "notifications",
  "tasks",
  "research_alerts",
  "copilot_activity",
  "saved_searches",
  "archive_snapshots",
  "research_diff",
  "compliance_summary",
  "workflow_summary",
  "background_jobs",
];

/** Default-hidden: empty/placeholder executive cards and unfinished surfaces. */
export const DEFAULT_HIDDEN_WIDGETS: DashboardWidgetId[] = [
  "valuation_summary",
  "business_quality_summary",
  "risk_summary",
  "notifications",
  "tasks",
  "research_alerts",
  "copilot_activity",
  "saved_searches",
  "archive_snapshots",
  "research_diff",
  "compliance_summary",
  "workflow_summary",
  "background_jobs",
];

export function widgetMeta(id: DashboardWidgetId): DashboardWidgetMeta {
  const meta = DASHBOARD_WIDGETS.find((w) => w.id === id);
  if (!meta) {
    throw new Error(`Unknown dashboard widget: ${id}`);
  }
  return meta;
}
