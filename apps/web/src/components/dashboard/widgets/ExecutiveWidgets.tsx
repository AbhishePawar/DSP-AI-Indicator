"use client";

/**
 * P9.3 Executive Dashboard widgets — existing APIs only; never invent metrics.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Badge, Button } from "@/components/ds";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { listRecentReports } from "@/lib/recentReports";
import { useUiStore } from "@/lib/shell";
import {
  DashboardWidgetShell,
  WidgetError,
  WidgetLoading,
  WidgetUnavailable,
} from "../DashboardWidgetShell";

export function AttentionBriefWidget() {
  const { session } = useAuth();
  const token = session?.accessToken;
  const [reportCount, setReportCount] = useState(0);

  useEffect(() => {
    setReportCount(listRecentReports().length);
  }, []);

  const health = useQuery({
    queryKey: ["dashboard", "exec-health"],
    queryFn: () => api.health({ token }),
    retry: 1,
    staleTime: 30_000,
  });

  const items: { label: string; href: string; tone: "info" | "warning" }[] = [];

  if (health.isError) {
    items.push({
      label: "Platform readiness check failed — continue via Company Analysis when online",
      href: "/analysis",
      tone: "warning",
    });
  } else if (health.data && !health.data.ready) {
    items.push({
      label: "Platform reports not ready — open Research Reports when coverage returns",
      href: "/research/institutional",
      tone: "warning",
    });
  }

  if (reportCount === 0) {
    items.push({
      label: "No recent reports on this device — start or reopen research",
      href: "/analysis",
      tone: "info",
    });
  } else {
    items.push({
      label: `${reportCount} local report id${reportCount === 1 ? "" : "s"} remembered — verify freshness in Research Reports`,
      href: "/research/institutional",
      tone: "info",
    });
  }

  items.push({
    label: "Review portfolio workspace for position context (no invented P&L)",
    href: "/portfolio",
    tone: "info",
  });

  return (
    <DashboardWidgetShell
      title="Needs attention"
      description="What requires investigation today — status from health probes and local history only."
      span={2}
    >
      {health.isLoading ? <WidgetLoading label="Checking attention signals" /> : null}
      <ul className="space-y-3">
        {items.map((item) => (
          <li
            key={item.label}
            className="flex flex-wrap items-start justify-between gap-2 border-l-2 border-[var(--accent)] pl-3"
          >
            <div>
              <Badge
                variant={item.tone === "warning" ? "warning" : "outline"}
                className="mb-1 text-[10px]"
              >
                {item.tone === "warning" ? "Caution" : "Investigate"}
              </Badge>
              <p className="text-sm text-[var(--fg)]">{item.label}</p>
            </div>
            <Link href={item.href}>
              <Button size="sm" variant="secondary">
                Open
              </Button>
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs text-[var(--muted)]">
        Research Mode: rankings are investigation cues, not buy/sell instructions.
      </p>
    </DashboardWidgetShell>
  );
}

export function MarketOverviewWidget() {
  const { session } = useAuth();
  const token = session?.accessToken;

  const market = useQuery({
    queryKey: ["dashboard", "market-overview"],
    queryFn: () => api.marketHealth({ token }),
    enabled: Boolean(token),
    retry: 1,
    staleTime: 30_000,
  });

  return (
    <DashboardWidgetShell
      title="Market Overview"
      description="GET /api/v1/market/health — provider readiness only"
      action={
        <Link
          href="/analysis"
          className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Company Analysis
        </Link>
      }
    >
      {!token ? (
        <WidgetUnavailable
          description="Sign in to probe market health. Quotes are never invented in the browser."
          href="/login?next=%2Fdashboard"
          actionLabel="Sign in"
        />
      ) : null}
      {token && market.isLoading ? (
        <WidgetLoading label="Loading market health" />
      ) : null}
      {token && market.isError ? (
        <WidgetError
          description={
            (market.error as Error).message || "Data unavailable."
          }
          onRetry={() => void market.refetch()}
        />
      ) : null}
      {token && market.data ? (
        <div className="space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={market.data.ok ? "accent" : "warning"}>
              {market.data.ok ? "Provider OK" : "Unavailable"}
            </Badge>
          </div>
          <p className="text-[var(--muted)]">
            Market overview shows connectivity status, not fabricated indices or
            tips. Open Analysis for company-specific research.
          </p>
          <Link href="/analysis">
            <Button size="sm" variant="secondary">
              Analyze a company
            </Button>
          </Link>
        </div>
      ) : null}
    </DashboardWidgetShell>
  );
}

function InsightNavWidget({
  title,
  description,
  body,
  href,
  actionLabel,
}: {
  title: string;
  description: string;
  body: string;
  href: string;
  actionLabel: string;
}) {
  return (
    <DashboardWidgetShell title={title} description={description}>
      <WidgetUnavailable
        title="Data unavailable."
        description={body}
        href={href}
        actionLabel={actionLabel}
      />
    </DashboardWidgetShell>
  );
}

export function ValuationSummaryWidget() {
  return (
    <InsightNavWidget
      title="Valuation Summary"
      description="Valuation runs on the backend — never in this widget"
      body="No aggregated valuation feed is available on the dashboard. Open Analysis or a research report to inspect intrinsic value ranges, assumptions, and confidence."
      href="/analysis"
      actionLabel="Open Analysis"
    />
  );
}

export function BusinessQualitySummaryWidget() {
  return (
    <InsightNavWidget
      title="Business Quality Summary"
      description="Quality meanings come from research analysis"
      body="No portfolio-wide business quality rollup API is exposed here. Investigate quality, moat, and management on a company analysis."
      href="/research"
      actionLabel="Open Research"
    />
  );
}

export function RiskSummaryWidget() {
  return (
    <InsightNavWidget
      title="Risk Summary"
      description="Risk is categorical and evidence-linked"
      body="No fabricated risk heat map. Review company risk sections in Analysis. High financial risk is never styled as a sell tip."
      href="/analysis"
      actionLabel="Review risks"
    />
  );
}

export function ResearchActivityWidget() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    setCount(listRecentReports().length);
  }, []);

  return (
    <DashboardWidgetShell
      title="Research Activity"
      description="Local research activity signals on this device"
      action={
        <Link
          href="/research"
          className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Workspace
        </Link>
      }
    >
      {count === 0 ? (
        <WidgetUnavailable
          description="No local report activity yet. What changed will appear after you run analyses — the browser does not invent activity."
          href="/analysis"
          actionLabel="Start analysis"
        />
      ) : (
        <div className="space-y-2 text-sm">
          <p>
            <span className="font-medium">{count}</span>{" "}
            <span className="text-[var(--muted)]">
              remembered report id{count === 1 ? "" : "s"} on this device
            </span>
          </p>
          <Link href="/research/institutional">
            <Button size="sm" variant="secondary">
              Open Research Reports
            </Button>
          </Link>
        </div>
      )}
    </DashboardWidgetShell>
  );
}

export function NotificationsWidget() {
  return (
    <DashboardWidgetShell
      title="Notifications"
      description="No notifications feed in frozen /api/v1 client"
    >
      <WidgetUnavailable
        title="Inbox empty / unavailable"
        description="Data unavailable for push or in-app notifications. Use Research Monitoring when APIs are provisioned; until then check Company Analysis and Research Reports."
        href="/research/institutional"
        actionLabel="Open Research Reports"
      />
    </DashboardWidgetShell>
  );
}

export function TasksWidget() {
  const setCommandOpen = useUiStore((s) => s.setCommandPaletteOpen);

  return (
    <DashboardWidgetShell
      title="Tasks"
      description="Investigation checklist — no tasks API in v1"
    >
      <ul className="space-y-2 text-sm">
        <li>
          <Link className="text-[var(--accent)] hover:underline" href="/analysis">
            Analyze a company
          </Link>
        </li>
        <li>
          <Link
            className="text-[var(--accent)] hover:underline"
            href="/portfolio"
          >
            Review portfolio workspace
          </Link>
        </li>
        <li>
          <Link
            className="text-[var(--accent)] hover:underline"
            href="/research/institutional"
          >
            Revisit Research Reports
          </Link>
        </li>
        <li>
          <button
            type="button"
            className="text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            onClick={() => setCommandOpen(true)}
          >
            Open command palette (search)
          </button>
        </li>
      </ul>
      <p className="mt-3 text-xs text-[var(--muted)]">
        Tasks are navigation aids, not assigned workflow items from a server.
      </p>
    </DashboardWidgetShell>
  );
}
