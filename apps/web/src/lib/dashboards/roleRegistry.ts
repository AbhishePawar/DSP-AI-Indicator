/** RC1 Milestone 6 — role dashboard registry (presentation only). */

export type EnterpriseDashboardRole =
  | "research"
  | "portfolio-manager"
  | "wealth-advisor"
  | "family-office"
  | "executive";

export type RoleDashboardMeta = {
  role: EnterpriseDashboardRole;
  title: string;
  description: string;
  href: string;
  widgetKeys: readonly string[];
};

export const ENTERPRISE_DASHBOARD_ROLES: readonly RoleDashboardMeta[] = [
  {
    role: "research",
    title: "Research Analyst Dashboard",
    description:
      "Research coverage, pending work, committee agents, and watchlist — Research Engine only.",
    href: "/dashboards/research",
    widgetKeys: [
      "research_coverage",
      "companies_under_review",
      "pending_research",
      "recent_reports",
      "research_score",
      "ai_committee_summary",
      "watchlist",
      "recent_news",
    ],
  },
  {
    role: "portfolio-manager",
    title: "Portfolio Manager Dashboard",
    description:
      "Health, allocation, risk, and MoS heatmap from Portfolio Intelligence.",
    href: "/dashboards/portfolio-manager",
    widgetKeys: [
      "portfolio_health_score",
      "asset_allocation",
      "risk_summary",
      "diversification",
      "top_opportunities",
      "valuation_heatmap",
      "alerts",
      "portfolio_performance",
    ],
  },
  {
    role: "wealth-advisor",
    title: "Wealth Advisor Dashboard",
    description:
      "Client portfolios, risk warnings, and workflow notifications.",
    href: "/dashboards/wealth-advisor",
    widgetKeys: [
      "client_portfolios",
      "portfolio_health",
      "risk_warnings",
      "recommended_actions",
      "upcoming_reviews",
      "workflow_notifications",
    ],
  },
  {
    role: "family-office",
    title: "Family Office Dashboard",
    description:
      "Holdings, allocation, risk, and cash from Portfolio Store + Intelligence.",
    href: "/dashboards/family-office",
    widgetKeys: [
      "net_worth_summary",
      "asset_allocation",
      "portfolio_intelligence",
      "holdings_overview",
      "risk",
      "opportunities",
      "cash_position",
    ],
  },
  {
    role: "executive",
    title: "Executive Dashboard",
    description:
      "Platform KPIs, coverage, workflow status, and system health.",
    href: "/dashboards/executive",
    widgetKeys: [
      "platform_kpis",
      "research_coverage",
      "portfolio_coverage",
      "workflow_status",
      "alert_statistics",
      "user_activity",
      "system_health",
    ],
  },
] as const;

export function metaForRole(
  role: string,
): RoleDashboardMeta | undefined {
  return ENTERPRISE_DASHBOARD_ROLES.find((r) => r.role === role);
}

export function isEnterpriseDashboardRole(
  role: string,
): role is EnterpriseDashboardRole {
  return ENTERPRISE_DASHBOARD_ROLES.some((r) => r.role === role);
}
