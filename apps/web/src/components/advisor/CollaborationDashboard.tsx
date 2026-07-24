"use client";

import { memo, useMemo, useSyncExternalStore, type ReactNode } from "react";
import Link from "next/link";

import { CollaborationLayout } from "@/components/advisor/TeamCollaboration";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { WindowedList } from "@/lib/perf/WindowedList";
import {
  COLLAB_DASHBOARD_TRUST,
  buildAccessibilityValidation,
  buildActivityOverview,
  buildAdvisorPlatformHealth,
  buildCrossWorkspaceLinks,
  buildOverallTeamStatus,
  buildPerformanceValidation,
  buildProductionValidation,
  buildRecentSessions,
  buildTeamMetrics,
  buildWorkspaceHealth,
  type ValidationItem,
  type WorkspaceHealthItem,
} from "@/lib/advisor/collaborationDashboardModels";
import {
  getCollaborationSnapshot,
  subscribeCollaboration,
} from "@/lib/advisor/collaborationSession";

function useCollabSession() {
  return useSyncExternalStore(
    subscribeCollaboration,
    getCollaborationSnapshot,
    getCollaborationSnapshot,
  );
}

function statusTone(status: WorkspaceHealthItem["status"] | ValidationItem["status"]) {
  if (status === "healthy" || status === "pass") return "success" as const;
  if (status === "watch") return "warning" as const;
  return "neutral" as const;
}

function DashboardShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <CollaborationLayout title={title} description={description}>
      <p
        role="note"
        className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm"
      >
        {COLLAB_DASHBOARD_TRUST}
      </p>
      {children}
    </CollaborationLayout>
  );
}

/* ── Widgets ────────────────────────────────────────────────────── */

export const WorkspaceHealthCard = memo(function WorkspaceHealthCard({
  item,
}: {
  item: WorkspaceHealthItem;
}) {
  return (
    <Link
      href={item.href}
      className="block rounded-md border border-[var(--border)] bg-[var(--surface-2)]/40 p-3 transition hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      aria-label={`${item.label}: ${item.status}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium">{item.label}</p>
        <Badge tone={statusTone(item.status)}>{item.status}</Badge>
      </div>
      <p className="mt-2 text-xs text-[var(--muted)]">{item.detail}</p>
    </Link>
  );
});

export const TeamHealthDashboard = memo(function TeamHealthDashboard() {
  useCollabSession(); // re-render when collaboration session changes
  const health = buildWorkspaceHealth();
  const overall = buildOverallTeamStatus();

  return (
    <Card>
      <CardHeader
        title="Workspace Health"
        description={`${overall.label} — ${overall.detail}`}
      />
      <CardBody className="space-y-4">
        <div
          className="h-2 overflow-hidden rounded-full bg-[var(--surface-2)]"
          role="progressbar"
          aria-valuenow={overall.completionPct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Overall team completion"
        >
          <div
            className="h-full bg-[var(--accent)]"
            style={{ width: `${overall.completionPct}%` }}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {health.map((item) => (
            <WorkspaceHealthCard key={item.id} item={item} />
          ))}
        </div>
      </CardBody>
    </Card>
  );
});

export const TeamMetricsPanel = memo(function TeamMetricsPanel() {
  useCollabSession();
  const metrics = buildTeamMetrics();
  const cells = [
    ["Research coverage", metrics.researchCoverage],
    ["Portfolio coverage", metrics.portfolioCoverage],
    ["Review completion", metrics.reviewCompletion],
    ["Assignment distribution", metrics.assignmentDistribution],
    ["Presentation readiness", metrics.presentationReadiness],
    ["Meeting readiness", metrics.meetingReadiness],
    ["Outstanding work", metrics.outstandingWork],
    ["Overall completion %", `${metrics.overallCompletionPct}%`],
  ] as const;

  return (
    <Card>
      <CardHeader title="Team Metrics" description="Presentation-only aggregates" />
      <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Team metrics">
        {cells.map(([label, value]) => (
          <div
            key={label}
            className="rounded-md border border-[var(--border)] bg-[var(--surface-2)]/40 p-3"
          >
            <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</p>
            <p className="mt-1 text-sm font-medium">{value}</p>
          </div>
        ))}
      </CardBody>
    </Card>
  );
});

export const ActivityOverviewCard = memo(function ActivityOverviewCard() {
  useCollabSession();
  const activity = buildActivityOverview();

  return (
    <Card>
      <CardHeader
        title="Activity Overview"
        description="Research · Portfolio · Review session feeds"
      />
      <CardBody className="grid gap-4 lg:grid-cols-3">
        {(
          [
            ["Research Activity", activity.researchActivity],
            ["Portfolio Activity", activity.portfolioActivity],
            ["Review Activity", activity.reviewActivity],
          ] as const
        ).map(([title, items]) => (
          <section key={title} aria-label={title}>
            <h3 className="mb-2 text-sm font-medium">{title}</h3>
            <WindowedList
              items={items}
              initial={4}
              step={4}
              className="grid gap-2"
              renderItem={(item) => (
                <Link
                  key={item.id}
                  href={item.href}
                  className="block min-h-11 rounded-md border border-[var(--border)] px-2 py-2 text-xs hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                >
                  <span className="block text-sm">{item.label}</span>
                  <time dateTime={item.at} className="text-[var(--muted)]">
                    {item.at.slice(0, 10)}
                  </time>
                </Link>
              )}
            />
          </section>
        ))}
      </CardBody>
    </Card>
  );
});

export const CollaborationSummaryCard = memo(function CollaborationSummaryCard() {
  const session = useCollabSession();
  const overall = buildOverallTeamStatus();
  const recent = buildRecentSessions();

  return (
    <Card>
      <CardHeader
        title="Collaboration Summary"
        description="Overall team status · recent sessions · assignments snapshot"
      />
      <CardBody className="space-y-4 text-sm">
        <p>
          Overall team status: <Badge tone="success">{overall.label}</Badge>
        </p>
        <p className="text-[var(--muted)]">{overall.detail}</p>
        <p className="text-xs text-[var(--muted)]">
          Session pins: {session.pinnedItemIds.length} · Recent nav:{" "}
          {session.recentNavigation.length}
        </p>
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-[var(--muted)]">
            Recent sessions
          </p>
          <ul className="space-y-1" aria-label="Recent collaboration sessions">
            {recent.map((s) => (
              <li key={s.id}>
                <Link
                  href={s.href}
                  className="text-[var(--accent)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                >
                  {s.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/advisor/team/shared-reviews/board">
            <Button variant="secondary" size="sm">
              Assignments
            </Button>
          </Link>
          <Link href="/advisor/presentations">
            <Button variant="secondary" size="sm">
              Presentations
            </Button>
          </Link>
          <Link href="/advisor/team/validation">
            <Button variant="ghost" size="sm">
              Validation
            </Button>
          </Link>
        </div>
      </CardBody>
    </Card>
  );
});

function ValidationList({
  title,
  description,
  items,
}: {
  title: string;
  description: string;
  items: ValidationItem[];
}) {
  return (
    <Card>
      <CardHeader title={title} description={description} />
      <CardBody>
        <ul className="space-y-2" aria-label={title}>
          {items.map((item) => (
            <li
              key={item.id}
              className="flex min-h-11 flex-col gap-1 rounded-md border border-[var(--border)] px-3 py-2 text-sm sm:flex-row sm:items-start sm:justify-between"
            >
              <div>
                <p className="font-medium">{item.label}</p>
                <p className="text-xs text-[var(--muted)]">{item.note}</p>
              </div>
              <Badge tone={statusTone(item.status)}>{item.status}</Badge>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

export const ProductionValidationCard = memo(function ProductionValidationCard() {
  const items = useMemo(() => buildProductionValidation(), []);
  return (
    <ValidationList
      title="Production Validation"
      description="Workspace · navigation · design · empty/loading · responsive · session"
      items={items}
    />
  );
});

export const PerformanceValidationCard = memo(function PerformanceValidationCard() {
  const items = useMemo(() => buildPerformanceValidation(), []);
  return (
    <ValidationList
      title="Performance Validation"
      description="Lazy routes · memoization · windowed lists · bundle splitting"
      items={items}
    />
  );
});

export const AccessibilityValidationCard = memo(function AccessibilityValidationCard() {
  const items = useMemo(() => buildAccessibilityValidation(), []);
  return (
    <ValidationList
      title="Accessibility Validation"
      description="WCAG AA · keyboard · ARIA · focus · screen reader · contrast"
      items={items}
    />
  );
});

export const WorkspaceValidationPanel = memo(function WorkspaceValidationPanel() {
  const platform = useMemo(() => buildAdvisorPlatformHealth(), []);

  return (
    <Card>
      <CardHeader
        title="Advisor Platform Readiness"
        description="Cross-module health when Advisor Demo is enabled"
      />
      <CardBody>
        <ul
          className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3"
          aria-label="Advisor platform health"
        >
          {platform.map((p) => (
            <li key={p.id}>
              <Link
                href={p.href}
                className="flex min-h-11 items-center justify-between gap-2 rounded-md border border-[var(--border)] px-3 text-sm hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                <span>{p.label}</span>
                <Badge tone="success">{p.status}</Badge>
              </Link>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
});

export const CrossWorkspaceNav = memo(function CrossWorkspaceNav() {
  const links = useMemo(() => buildCrossWorkspaceLinks(), []);
  return (
    <Card>
      <CardHeader
        title="Cross Workspace Navigation"
        description="Seamless links — in-memory session state preserved while navigating"
      />
      <CardBody className="flex flex-wrap gap-2" aria-label="Cross workspace navigation">
        {links.map((l) => (
          <Link key={l.href} href={l.href}>
            <Button variant="secondary" size="md">
              {l.label}
            </Button>
          </Link>
        ))}
      </CardBody>
    </Card>
  );
});

/* ── Pages ──────────────────────────────────────────────────────── */

export const CollaborationDashboard = memo(function CollaborationDashboard() {
  return (
    <DashboardShell
      title="Collaboration Dashboard"
      description="Unified visibility across research, portfolios, reviews, assignments, and presentations"
    >
      <CrossWorkspaceNav />
      <TeamHealthDashboard />
      <TeamMetricsPanel />
      <div className="grid gap-4 lg:grid-cols-2">
        <CollaborationSummaryCard />
        <Card>
          <CardHeader title="Presentations & Assignments" />
          <CardBody className="flex flex-wrap gap-2">
            <Link href="/advisor/presentations">
              <Button variant="secondary">Presentation Packs</Button>
            </Link>
            <Link href="/advisor/team/shared-reviews/board">
              <Button variant="secondary">Assignment Board</Button>
            </Link>
            <Link href="/advisor/reviews">
              <Button variant="ghost">Client Reviews</Button>
            </Link>
            <Link href="/advisor/team/validation">
              <Button variant="ghost">Production Validation</Button>
            </Link>
          </CardBody>
        </Card>
      </div>
      <ActivityOverviewCard />
    </DashboardShell>
  );
});

export const CollaborationValidationPage = memo(function CollaborationValidationPage() {
  return (
    <DashboardShell
      title="Production Validation"
      description="Readiness checks for Team Collaboration EPIC — presentation validation only"
    >
      <WorkspaceValidationPanel />
      <ProductionValidationCard />
      <PerformanceValidationCard />
      <AccessibilityValidationCard />
      <CrossWorkspaceNav />
    </DashboardShell>
  );
});
