"use client";

import { memo, useMemo } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import {
  buildLaunchDashboard,
  buildPostLaunchReport,
  buildVersionFreeze,
  type GateResult,
  type KnownIssue,
  type LaunchDashboardView,
  type PostLaunchReportView,
} from "@/lib/launch/publicLaunchModel";

function gateTone(status: GateResult): "success" | "warning" | "danger" {
  if (status === "PASS") return "success";
  if (status === "WARN") return "warning";
  return "danger";
}

function deployTone(
  status: LaunchDashboardView["deploymentStatus"],
): "success" | "warning" | "danger" {
  if (status === "LIVE") return "success";
  if (status === "SOAK") return "warning";
  return "danger";
}

export function ReleaseStatusCard({ view }: { view: LaunchDashboardView }) {
  return (
    <Card className="border-[var(--accent)]/40">
      <CardHeader
        title="Release status"
        action={<Badge tone={deployTone(view.deploymentStatus)}>{view.deploymentStatus}</Badge>}
      />
      <CardBody className="space-y-2 text-sm">
        <p className="font-[family-name:var(--font-display)] text-3xl tracking-tight">
          Web {view.currentVersion}
        </p>
        <p>
          Recommendation:{" "}
          <Badge
            tone={
              view.recommendation === "GO PUBLIC"
                ? "success"
                : view.recommendation === "HOLD"
                  ? "danger"
                  : "warning"
            }
          >
            {view.recommendation}
          </Badge>
        </p>
        <p className="text-[var(--muted)]">{view.rationale}</p>
        <p className="text-xs text-[var(--muted)]">Released {view.releaseTime}</p>
      </CardBody>
    </Card>
  );
}

export function BuildInfoCard({
  view,
}: {
  view: LaunchDashboardView;
}) {
  const freeze = useMemo(() => buildVersionFreeze(), []);
  return (
    <Card>
      <CardHeader title="Build information" description="Version freeze metadata" />
      <CardBody className="space-y-2 text-sm">
        <p>
          Build ID: <span className="font-medium">{view.buildId}</span>
        </p>
        <p>Environment: {view.environment}</p>
        <p>Branch: {freeze.releaseBranch}</p>
        <p>Promoted from: {freeze.promotedFrom}</p>
        <p>Backend: {freeze.backend}</p>
        <p className="text-xs text-[var(--muted)]">{freeze.trustNote}</p>
      </CardBody>
    </Card>
  );
}

export function KnownIssuesCard({ issues }: { issues: KnownIssue[] }) {
  return (
    <Card>
      <CardHeader title="Known issues" description="Documented for operators & users" />
      <CardBody className="space-y-2">
        {issues.map((issue) => (
          <div
            key={issue.id}
            className="rounded-md border border-[var(--border)] px-3 py-2 text-sm"
          >
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                tone={
                  issue.severity === "critical" || issue.severity === "high"
                    ? "warning"
                    : "neutral"
                }
              >
                {issue.severity}
              </Badge>
              <span className="font-medium">{issue.title}</span>
            </div>
            <p className="mt-1 text-xs text-[var(--muted)]">{issue.mitigation}</p>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}

export function ReleaseHealthCard({ view }: { view: LaunchDashboardView }) {
  const gates = [
    { label: "Critical bugs", value: view.qualityGates.criticalBugs },
    { label: "Regression", value: view.qualityGates.regression },
    { label: "Accessibility", value: view.qualityGates.accessibility },
    { label: "Performance", value: view.qualityGates.performance },
    { label: "Security", value: view.qualityGates.security },
  ];
  return (
    <Card>
      <CardHeader title="Release health" description="Phase C quality gates" />
      <CardBody className="space-y-3 text-sm">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {gates.map((g) => (
            <div
              key={g.label}
              className="flex items-center justify-between rounded-md border border-[var(--border)] px-3 py-2"
            >
              <span>{g.label}</span>
              <Badge tone={gateTone(g.value)}>{g.value}</Badge>
            </div>
          ))}
        </div>
        <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Monitoring
        </p>
        <ul className="list-disc space-y-1 pl-5 text-[var(--muted)]">
          <li>App health: {view.monitoring.applicationHealth}</li>
          <li>Performance: {view.monitoring.performanceMetrics}</li>
          <li>Errors: {view.monitoring.errorRates}</li>
          <li>Feedback: {view.monitoring.userFeedbackQueue}</li>
          <li>Release: {view.monitoring.releaseHealth}</li>
        </ul>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Service health
          </p>
          <ul className="mt-1 space-y-1">
            {view.serviceHealth.map((s) => (
              <li key={s.name} className="flex flex-wrap items-center gap-2">
                <Badge tone={gateTone(s.status)}>{s.status}</Badge>
                <span className="font-medium">{s.name}</span>
                <span className="text-xs text-[var(--muted)]">{s.detail}</span>
              </li>
            ))}
          </ul>
        </div>
      </CardBody>
    </Card>
  );
}

export function PostLaunchReport({ report }: { report: PostLaunchReportView }) {
  return (
    <Card>
      <CardHeader title={report.title} description={`Released ${report.releasedAt}`} />
      <CardBody className="space-y-4 text-sm">
        <p>{report.outcome}</p>
        <div>
          <p className="font-medium">Lessons learned</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {report.lessonsLearned.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium">Future roadmap</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {report.futureRoadmap.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-[var(--muted)]">Regression: {report.regressionSummary}</p>
        <KnownIssuesCard issues={report.knownIssues} />
      </CardBody>
    </Card>
  );
}

export function LaunchDashboard({ refreshTick = 0 }: { refreshTick?: number }) {
  const view = useMemo(() => buildLaunchDashboard(), [refreshTick]);
  const freeze = useMemo(() => buildVersionFreeze(), []);

  return (
    <div className="space-y-5">
      <ReleaseStatusCard view={view} />
      <div className="grid gap-4 lg:grid-cols-2">
        <BuildInfoCard view={view} />
        <ReleaseHealthCard view={view} />
      </div>
      <KnownIssuesCard issues={view.knownIssues} />
      <Card>
        <CardHeader
          title="Production deployment verification"
          description="Build · env · HTTPS · compression · caching · maps · errors · health · version"
        />
        <CardBody className="grid gap-2 sm:grid-cols-2">
          {view.productionChecks.map((c) => (
            <div
              key={c.id}
              className="rounded-md border border-[var(--border)] px-3 py-2 text-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{c.label}</span>
                <Badge tone={gateTone(c.status)}>{c.status}</Badge>
              </div>
              <p className="mt-1 text-xs text-[var(--muted)]">{c.detail}</p>
            </div>
          ))}
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Version freeze" />
        <CardBody className="space-y-2 text-sm">
          <p>
            Dependencies frozen at Web {freeze.appVersion} · branch{" "}
            <code className="text-xs">{freeze.releaseBranch}</code>
          </p>
          <ul className="list-disc pl-5 text-[var(--muted)]">
            {freeze.dependencies.map((d) => (
              <li key={d.name}>
                {d.name}@{d.version}
              </li>
            ))}
          </ul>
          <p className="text-xs text-[var(--muted)]">
            Env vars & build config listed in docs/VERSION_FREEZE_v1.0.0.md
          </p>
        </CardBody>
      </Card>
      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="text-[var(--accent)] underline" href="/launch/report">
          Post-launch report
        </Link>
        <Link className="text-[var(--accent)] underline" href="/launch/checklist">
          Smoke / QA checklists
        </Link>
        <Link className="text-[var(--accent)] underline" href="/launch/performance">
          Performance
        </Link>
        <Link className="text-[var(--accent)] underline" href="/beta/rc">
          RC history
        </Link>
        <Link className="text-[var(--accent)] underline" href="/docs">
          Documentation
        </Link>
      </div>
    </div>
  );
}

export const LaunchDashboardWorkspace = memo(function LaunchDashboardWorkspace() {
  return <LaunchDashboard />;
});

export const PostLaunchReportWorkspace = memo(function PostLaunchReportWorkspace() {
  const report = useMemo(() => buildPostLaunchReport(), []);
  return <PostLaunchReport report={report} />;
});
