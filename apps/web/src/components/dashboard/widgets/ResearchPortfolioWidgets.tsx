"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQueries } from "@tanstack/react-query";

import {
  Button,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ds";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { featureFlags } from "@/lib/featureFlags";
import {
  listRecentReports,
  type RecentReportEntry,
} from "@/lib/recentReports";
import {
  DashboardWidgetShell,
  WidgetUnavailable,
} from "../DashboardWidgetShell";

export function RecentResearchReportsWidget() {
  const { session } = useAuth();
  const [entries, setEntries] = useState<RecentReportEntry[]>([]);

  useEffect(() => {
    setEntries(listRecentReports());
  }, []);

  const queries = useQueries({
    queries: entries.slice(0, 5).map((entry) => ({
      queryKey: ["dashboard", "report", entry.reportId],
      queryFn: () =>
        api.getReport(entry.reportId, { token: session?.accessToken }),
      enabled: Boolean(session?.accessToken) && entries.length > 0,
      retry: false,
    })),
  });

  return (
    <DashboardWidgetShell
      title="Recent Reports"
      description="GET /api/v1/report/{id} for locally remembered ids"
      span={2}
      action={
        <Link
          href="/reports"
          className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          All reports
        </Link>
      }
    >
      {entries.length === 0 ? (
        <WidgetUnavailable
          description="Analyze a company to store a report id locally. The browser never computes valuation."
          href="/analysis"
          actionLabel="Analyze Company"
        />
      ) : (
        <Table aria-label="Recent research reports">
          <TableHeader>
            <TableRow>
              <TableHead>Report ID</TableHead>
              <TableHead>Symbol</TableHead>
              <TableHead>API status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.slice(0, 5).map((entry, i) => {
              const q = queries[i];
              return (
                <TableRow key={entry.reportId}>
                  <TableCell>
                    <Link
                      href={`/reports/${encodeURIComponent(entry.reportId)}`}
                      className="text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                    >
                      {entry.reportId}
                    </Link>
                  </TableCell>
                  <TableCell>{entry.symbol ?? "—"}</TableCell>
                  <TableCell>
                    {q?.isLoading ? (
                      <Skeleton className="h-4 w-16" />
                    ) : q?.isError ? (
                      <span className="text-[var(--danger-fg)]">
                        Data unavailable.
                      </span>
                    ) : q?.data ? (
                      <span className="text-[var(--muted)]">
                        {q.data.format}
                      </span>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </DashboardWidgetShell>
  );
}

export function ArchiveSnapshotsWidget() {
  return (
    <DashboardWidgetShell
      title="Latest Archive Snapshots"
      description="No archive list endpoint in frozen /api/v1 client"
    >
      <WidgetUnavailable
        description="Data unavailable. Open Research Workspace to continue investigation."
        href="/research"
        actionLabel="Open Research"
      />
    </DashboardWidgetShell>
  );
}

export function ResearchDiffWidget() {
  return (
    <DashboardWidgetShell
      title="Recent Research Diff"
      description="No research-diff endpoint in frozen /api/v1 client"
    >
      <WidgetUnavailable
        description="Data unavailable. Compare analyses in Research Workspace when available."
        href="/research"
        actionLabel="Open Research"
      />
    </DashboardWidgetShell>
  );
}

export function ResearchAlertsWidget() {
  const enabled = featureFlags.showResearchAlerts;
  return (
    <DashboardWidgetShell
      title="Research Monitoring Alerts"
      description={
        enabled
          ? "Alert presentation enabled — feed API not exposed in client"
          : "Alert surfaces gated by research alert feature flag"
      }
    >
      <WidgetUnavailable
        description={
          enabled
            ? "Data unavailable. No monitoring-alerts API is wired in the thin client."
            : "Data unavailable. Research alerts remain off until product flags unlock them."
        }
        href="/research"
        actionLabel="Open Research"
      />
    </DashboardWidgetShell>
  );
}

export function PortfolioSummaryWidget() {
  return (
    <DashboardWidgetShell
      title="Portfolio Snapshot"
      description="Portfolio metrics come from Portfolio workspace APIs — not inventing totals here"
    >
      <WidgetUnavailable
        description="Data unavailable. Open Portfolio to load holdings from the backend."
        href="/portfolio"
        actionLabel="Open Portfolio"
      />
    </DashboardWidgetShell>
  );
}

export function WatchlistSummaryWidget() {
  return (
    <DashboardWidgetShell
      title="Watchlist Summary"
      description="Watchlist is managed in Portfolio workspace"
    >
      <WidgetUnavailable
        description="Data unavailable. Open Portfolio to review the watchlist."
        href="/portfolio"
        actionLabel="Open Portfolio"
      />
    </DashboardWidgetShell>
  );
}

export function PortfolioActivityWidget() {
  return (
    <DashboardWidgetShell
      title="Recent Portfolio Activity"
      description="No portfolio activity feed in frozen /api/v1 client"
    >
      <WidgetUnavailable
        description="Data unavailable. Continue in Portfolio for session activity."
        href="/portfolio"
        actionLabel="Open Portfolio"
      />
    </DashboardWidgetShell>
  );
}

export function DocumentationLinksWidget() {
  const links = [
    { href: "/documentation", label: "Platform documentation" },
    { href: "/docs", label: "Docs hub" },
    { href: "/docs/user-guide", label: "User guide" },
    { href: "/health", label: "Health details" },
  ] as const;

  return (
    <DashboardWidgetShell
      title="Documentation"
      description="Guides and operational references"
    >
      <ul className="space-y-2">
        {links.map((link) => (
          <li key={link.href}>
            <Link href={link.href}>
              <Button variant="secondary" size="sm" className="w-full justify-start">
                {link.label}
              </Button>
            </Link>
          </li>
        ))}
      </ul>
    </DashboardWidgetShell>
  );
}
