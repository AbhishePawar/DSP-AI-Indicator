"use client";

/**
 * P9.3 / EPIC-004 — Institutional Executive Dashboard.
 * Consumes frozen /api/v1 only. Missing data stays unavailable.
 */

import {
  Suspense,
  lazy,
  useMemo,
  useState,
  type ComponentType,
  type ReactNode,
} from "react";

import { Alert, Button } from "@/components/ds";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  useDashboardPrefsStore,
  widgetMeta,
  type DashboardWidgetId,
} from "@/lib/dashboard";
import { useUiStore } from "@/lib/shell";
import { cn } from "@/lib/utils";
import { DashboardCustomizePanel } from "./DashboardCustomizePanel";
import {
  DashboardWidgetShell,
  WidgetLoading,
} from "./DashboardWidgetShell";
import { QuickActionsWidget } from "./widgets/QuickActionsWidget";
import { WelcomeWidget } from "./widgets/WelcomeWidget";
import {
  AttentionBriefWidget,
  BusinessQualitySummaryWidget,
  MarketOverviewWidget,
  NotificationsWidget,
  ResearchActivityWidget,
  RiskSummaryWidget,
  TasksWidget,
  ValuationSummaryWidget,
} from "./widgets/ExecutiveWidgets";

const LazyRecentlyViewedCompaniesWidget = lazy(() =>
  import("./widgets/CompanyWidgets").then((m) => ({
    default: m.RecentlyViewedCompaniesWidget,
  })),
);
const LazyPinnedCompaniesWidget = lazy(() =>
  import("./widgets/CompanyWidgets").then((m) => ({
    default: m.PinnedCompaniesWidget,
  })),
);
const LazyRecentResearchWidget = lazy(() =>
  import("./widgets/CompanyWidgets").then((m) => ({
    default: m.RecentResearchWidget,
  })),
);
const LazyQuickCompanySearch = lazy(() =>
  import("./widgets/SearchWidgets").then((m) => ({
    default: m.CompanySearchWidget,
  })),
);
const LazyGlobalSearch = lazy(() =>
  import("./widgets/SearchWidgets").then((m) => ({
    default: m.GlobalSearchEntryWidget,
  })),
);
const LazyRecentSearches = lazy(() =>
  import("./widgets/SearchHistoryWidgets").then((m) => ({
    default: m.RecentSearchesWidget,
  })),
);
const LazySavedSearches = lazy(() =>
  import("./widgets/SearchHistoryWidgets").then((m) => ({
    default: m.SavedSearchesWidget,
  })),
);
const LazyPortfolioSummary = lazy(() =>
  import("./widgets/ResearchPortfolioWidgets").then((m) => ({
    default: m.PortfolioSummaryWidget,
  })),
);
const LazyWatchlistSummary = lazy(() =>
  import("./widgets/ResearchPortfolioWidgets").then((m) => ({
    default: m.WatchlistSummaryWidget,
  })),
);
const LazyPortfolioActivity = lazy(() =>
  import("./widgets/ResearchPortfolioWidgets").then((m) => ({
    default: m.PortfolioActivityWidget,
  })),
);
const LazyResearchReports = lazy(() =>
  import("./widgets/ResearchPortfolioWidgets").then((m) => ({
    default: m.RecentResearchReportsWidget,
  })),
);
const LazyArchiveSnapshots = lazy(() =>
  import("./widgets/ResearchPortfolioWidgets").then((m) => ({
    default: m.ArchiveSnapshotsWidget,
  })),
);
const LazyResearchDiff = lazy(() =>
  import("./widgets/ResearchPortfolioWidgets").then((m) => ({
    default: m.ResearchDiffWidget,
  })),
);
const LazyResearchAlerts = lazy(() =>
  import("./widgets/ResearchPortfolioWidgets").then((m) => ({
    default: m.ResearchAlertsWidget,
  })),
);
const LazyDocumentation = lazy(() =>
  import("./widgets/ResearchPortfolioWidgets").then((m) => ({
    default: m.DocumentationLinksWidget,
  })),
);
const LazyCommittee = lazy(() =>
  import("./widgets/SystemAiWidgets").then((m) => ({
    default: m.CommitteeActivityWidget,
  })),
);
const LazyCompliance = lazy(() =>
  import("./widgets/SystemAiWidgets").then((m) => ({
    default: m.ComplianceSummaryWidget,
  })),
);
const LazyWorkflow = lazy(() =>
  import("./widgets/SystemAiWidgets").then((m) => ({
    default: m.WorkflowSummaryWidget,
  })),
);
const LazyCopilot = lazy(() =>
  import("./widgets/SystemAiWidgets").then((m) => ({
    default: m.CopilotActivityWidget,
  })),
);
const LazyPlatformHealth = lazy(() =>
  import("./widgets/SystemAiWidgets").then((m) => ({
    default: m.PlatformHealthWidget,
  })),
);
const LazyBackgroundJobs = lazy(() =>
  import("./widgets/SystemAiWidgets").then((m) => ({
    default: m.BackgroundJobsWidget,
  })),
);
const LazyApiStatus = lazy(() =>
  import("./widgets/SystemAiWidgets").then((m) => ({
    default: m.ApiStatusWidget,
  })),
);
const LazyResearchCommandCenter = lazy(() =>
  import("./widgets/ResearchCommandCenterWidget").then((m) => ({
    default: m.ResearchCommandCenterWidget,
  })),
);

function withSuspense(
  Comp: ComponentType,
  title: string,
): ReactNode {
  return (
    <Suspense
      fallback={
        <DashboardWidgetShell title={title}>
          <WidgetLoading label={`Loading ${title}`} />
        </DashboardWidgetShell>
      }
    >
      <Comp />
    </Suspense>
  );
}

function renderWidget(id: DashboardWidgetId): ReactNode {
  switch (id) {
    case "welcome":
      return <WelcomeWidget />;
    case "attention_brief":
      return <AttentionBriefWidget />;
    case "quick_actions":
      return <QuickActionsWidget />;
    case "research_command_center":
      return withSuspense(
        LazyResearchCommandCenter,
        "Research Command Center",
      );
    case "market_overview":
      return withSuspense(MarketOverviewWidget, "Market Overview");
    case "valuation_summary":
      return <ValuationSummaryWidget />;
    case "business_quality_summary":
      return <BusinessQualitySummaryWidget />;
    case "risk_summary":
      return <RiskSummaryWidget />;
    case "research_activity":
      return <ResearchActivityWidget />;
    case "notifications":
      return <NotificationsWidget />;
    case "tasks":
      return <TasksWidget />;
    case "company_search":
      return withSuspense(LazyQuickCompanySearch, "Quick Company Search");
    case "recent_companies":
      return withSuspense(
        LazyRecentlyViewedCompaniesWidget,
        "Recently Viewed Companies",
      );
    case "pinned_companies":
      return withSuspense(LazyPinnedCompaniesWidget, "Pinned Companies");
    case "recent_research":
      return withSuspense(LazyRecentResearchWidget, "Recent Research");
    case "portfolio_summary":
      return withSuspense(LazyPortfolioSummary, "Portfolio Snapshot");
    case "watchlist_summary":
      return withSuspense(LazyWatchlistSummary, "Watchlist Summary");
    case "portfolio_activity":
      return withSuspense(LazyPortfolioActivity, "Recent Portfolio Activity");
    case "research_reports":
      return withSuspense(LazyResearchReports, "Recent Reports");
    case "archive_snapshots":
      return withSuspense(LazyArchiveSnapshots, "Latest Archive Snapshots");
    case "research_diff":
      return withSuspense(LazyResearchDiff, "Recent Research Diff");
    case "research_alerts":
      return withSuspense(LazyResearchAlerts, "Research Monitoring Alerts");
    case "committee_activity":
      return withSuspense(LazyCommittee, "Recent AI Committee Decisions");
    case "compliance_summary":
      return withSuspense(LazyCompliance, "Compliance Summary");
    case "workflow_summary":
      return withSuspense(LazyWorkflow, "Workflow Summary");
    case "copilot_activity":
      return withSuspense(LazyCopilot, "Copilot Activity");
    case "platform_health":
      return withSuspense(LazyPlatformHealth, "Platform Health");
    case "background_jobs":
      return withSuspense(LazyBackgroundJobs, "Background Jobs");
    case "api_status":
      return withSuspense(LazyApiStatus, "API Status");
    case "documentation":
      return withSuspense(LazyDocumentation, "Documentation");
    case "global_search":
      return withSuspense(LazyGlobalSearch, "Search");
    case "recent_searches":
      return withSuspense(LazyRecentSearches, "Recent Searches");
    case "saved_searches":
      return withSuspense(LazySavedSearches, "Saved Searches");
    default:
      return null;
  }
}

const EXECUTIVE_QUESTIONS = [
  "What requires my attention today?",
  "What changed?",
  "What should I research?",
  "What risks exist?",
  "What opportunities exist?",
  "What is my portfolio doing?",
] as const;

/** P9.3 — Executive Dashboard (authenticated landing). */
export function InstitutionalDashboard() {
  const [customizeOpen, setCustomizeOpen] = useState(false);
  const widgetOrder = useDashboardPrefsStore((s) => s.widgetOrder);
  const hiddenWidgets = useDashboardPrefsStore((s) => s.hiddenWidgets);
  const setCommandOpen = useUiStore((s) => s.setCommandPaletteOpen);

  const visibleIds = useMemo(
    () => widgetOrder.filter((id) => !hiddenWidgets.includes(id)),
    [widgetOrder, hiddenWidgets],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Executive Dashboard"
        description="Authoritative authenticated landing — research orientation from certified /api/v1 probes and local history. Missing data stays unavailable."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setCommandOpen(true)}
            >
              Command palette
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setCustomizeOpen((v) => !v)}
              aria-expanded={customizeOpen}
              aria-controls="dashboard-customize"
            >
              {customizeOpen ? "Hide layout" : "Customize layout"}
            </Button>
          </div>
        }
      />

      <Alert variant="info" title="Research Mode">
        This dashboard helps you decide what to investigate next. It does not
        issue buy/sell instructions. Shell navigation (top bar, sidebar, status
        footer) remains available around this workspace.
      </Alert>

      <section
        aria-label="Executive questions"
        className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5"
      >
        <h2 className="font-[family-name:var(--font-display)] text-lg font-medium tracking-tight">
          Today&apos;s orientation
        </h2>
        <ol className="mt-3 grid gap-2 text-sm text-[var(--muted)] sm:grid-cols-2 lg:grid-cols-3">
          {EXECUTIVE_QUESTIONS.map((q, i) => (
            <li key={q} className="flex gap-2">
              <span className="text-[var(--accent)]" aria-hidden="true">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>{q}</span>
            </li>
          ))}
        </ol>
      </section>

      <div id="dashboard-customize">
        <DashboardCustomizePanel
          open={customizeOpen}
          onClose={() => setCustomizeOpen(false)}
        />
      </div>

      <div
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
        role="region"
        aria-label="Dashboard widgets"
      >
        {visibleIds.map((id) => {
          const meta = widgetMeta(id);
          return (
            <div
              key={id}
              className={cn(
                meta.span === 2 && "sm:col-span-2 xl:col-span-2",
                meta.span === 2 &&
                  (id === "welcome" ||
                    id === "attention_brief" ||
                    id === "quick_actions" ||
                    id === "research_reports") &&
                  "xl:col-span-3",
              )}
              data-widget={id}
            >
              {renderWidget(id)}
            </div>
          );
        })}
      </div>

      <footer className="border-t border-[var(--border)] pt-4 text-xs text-[var(--muted)]">
        Executive Dashboard · Design System tokens · Thin client over{" "}
        <code className="font-[family-name:var(--font-mono)]">/api/v1</code> ·
        Customize layout anytime ·{" "}
        <button
          type="button"
          className="text-[var(--accent)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          onClick={() => setCommandOpen(true)}
        >
          Search / command palette
        </button>
      </footer>
    </div>
  );
}
