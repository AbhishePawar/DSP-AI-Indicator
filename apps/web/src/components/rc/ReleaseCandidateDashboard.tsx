"use client";

import { memo, useMemo } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import {
  buildRcDashboard,
  type ResolutionRecord,
  type ValidationRow,
  type VersionManifest,
  type RcDashboardView,
} from "@/lib/rc/rcStabilizationModel";

function toneForStatus(status: ValidationRow["status"]): "success" | "warning" | "danger" | "neutral" {
  if (status === "pass") return "success";
  if (status === "warn") return "warning";
  if (status === "fail") return "danger";
  return "neutral";
}

function recTone(
  rec: RcDashboardView["recommendation"],
): "success" | "warning" | "danger" {
  if (rec === "APPROVE RC") return "success";
  if (rec === "HOLD") return "danger";
  return "warning";
}

export function IssueResolutionCard({ item }: { item: ResolutionRecord }) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={item.title}
        action={<Badge tone={item.status === "resolved" ? "success" : "warning"}>{item.status}</Badge>}
      />
      <CardBody className="space-y-2 text-sm">
        <div className="flex flex-wrap gap-2">
          <Badge tone="neutral">{item.severity}</Badge>
          <Badge tone="neutral">{item.component}</Badge>
        </div>
        <p>
          <span className="font-medium">Before — </span>
          {item.before}
        </p>
        <p>
          <span className="font-medium">After — </span>
          {item.after}
        </p>
        <p className="text-[var(--muted)]">
          <span className="font-medium text-[var(--fg)]">Verification — </span>
          {item.verification}
        </p>
      </CardBody>
    </Card>
  );
}

export function QualityTrendCard({
  points,
}: {
  points: RcDashboardView["qualityTrend"];
}) {
  const max = Math.max(...points.map((p) => p.score), 100);
  return (
    <Card>
      <CardHeader title="Quality trend" description="Launch → Beta → RC scores" />
      <CardBody className="space-y-3">
        {points.map((p) => (
          <div key={p.label}>
            <div className="mb-1 flex items-baseline justify-between text-sm">
              <span className="font-medium">{p.label}</span>
              <span className="tabular-nums text-[var(--muted)]">{p.score}</span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-[var(--surface-2)]"
              role="img"
              aria-label={`${p.label} score ${p.score}`}
            >
              <div
                className="h-full rounded-full bg-[var(--accent)] transition-[width] duration-300"
                style={{ width: `${(p.score / max) * 100}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-[var(--muted)]">{p.note}</p>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}

export function VersionManifestCard({ manifest }: { manifest: VersionManifest }) {
  return (
    <Card>
      <CardHeader
        title="Version manifest"
        description="Frozen RC metadata — no engine changes"
        action={<Badge tone="accent">v{manifest.appVersion}</Badge>}
      />
      <CardBody className="space-y-3 text-sm">
        <p>
          <span className="font-medium">{manifest.codename}</span>
          <span className="text-[var(--muted)]"> · frozen {manifest.frozenAt}</span>
        </p>
        <p>Backend: {manifest.backendRc}</p>
        <div className="grid gap-1 sm:grid-cols-2">
          <p>Channel: {manifest.buildMetadata.channel}</p>
          <p>Node: {manifest.buildMetadata.nodeTarget}</p>
          <p>Next: {manifest.buildMetadata.nextMajor}</p>
          <p>React: {manifest.buildMetadata.reactMajor}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Dependency snapshot
          </p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {manifest.dependencySnapshot.map((d) => (
              <li key={d.name}>
                {d.name}@{d.version}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Environment summary
          </p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {manifest.environmentSummary.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-[var(--muted)]">
          Release notes: {manifest.releaseNotesRef}
        </p>
        <p className="text-xs text-[var(--muted)]">{manifest.trustNote}</p>
      </CardBody>
    </Card>
  );
}

export function ReleaseSummaryCard({ view }: { view: RcDashboardView }) {
  return (
    <Card className="border-[var(--accent)]/40">
      <CardHeader
        title="Release summary"
        action={<Badge tone={recTone(view.recommendation)}>{view.recommendation}</Badge>}
      />
      <CardBody className="space-y-3 text-sm">
        <p className="font-[family-name:var(--font-display)] text-4xl tabular-nums tracking-tight">
          {view.overallScore}
          <span className="ml-2 text-base text-[var(--muted)]">RC score</span>
        </p>
        <p>{view.rationale}</p>
        <ul className="grid gap-1 sm:grid-cols-2">
          <li>Resolved: {view.resolvedIssues}</li>
          <li>Remaining: {view.remainingIssues}</li>
          <li>Critical open: {view.remainingCritical}</li>
          <li>High open: {view.remainingHigh}</li>
        </ul>
        <div className="flex flex-wrap gap-2 pt-1">
          <Link className="text-[var(--accent)] underline" href="/beta/issues">
            Issue tracker
          </Link>
          <Link className="text-[var(--accent)] underline" href="/launch">
            Launch readiness
          </Link>
          <Link className="text-[var(--accent)] underline" href="/beta">
            Beta dashboard
          </Link>
        </div>
      </CardBody>
    </Card>
  );
}

function ValidationMatrix({
  title,
  description,
  rows,
}: {
  title: string;
  description: string;
  rows: ValidationRow[];
}) {
  return (
    <Card>
      <CardHeader title={title} description={description} />
      <CardBody className="space-y-2">
        {rows.map((row) => (
          <div
            key={row.id}
            className="flex flex-col gap-1 rounded-md border border-[var(--border)] px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
          >
            <div>
              <p className="text-sm font-medium">{row.label}</p>
              <p className="text-xs text-[var(--muted)]">{row.notes}</p>
            </div>
            <Badge tone={toneForStatus(row.status)}>{row.status}</Badge>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}

export function ReleaseCandidateDashboard({ refreshTick }: { refreshTick: number }) {
  const view = useMemo(() => buildRcDashboard(), [refreshTick]);
  const tiles = [
    { label: "Resolved issues", value: String(view.resolvedIssues) },
    { label: "Remaining issues", value: String(view.remainingIssues) },
    { label: "Regression", value: view.regressionStatus },
    { label: "Performance", value: view.performanceStatus },
    { label: "Accessibility", value: view.accessibilityStatus },
    { label: "Security", value: view.securityStatus },
  ];

  return (
    <div className="space-y-5">
      <ReleaseSummaryCard view={view} />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {tiles.map((t) => (
          <Card key={t.label} className="dsp-interactive">
            <CardHeader title={t.label} />
            <CardBody className="text-sm font-medium leading-snug">{t.value}</CardBody>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <QualityTrendCard points={view.qualityTrend} />
        <VersionManifestCard manifest={view.manifest} />
      </div>
      <section className="space-y-3" aria-labelledby="rc-resolutions">
        <h2 id="rc-resolutions" className="font-[family-name:var(--font-display)] text-xl">
          Issue resolutions (Before → After)
        </h2>
        <div className="grid gap-3 md:grid-cols-2">
          {view.resolutions.map((r) => (
            <IssueResolutionCard key={r.id} item={r} />
          ))}
        </div>
      </section>
      <div className="grid gap-4 lg:grid-cols-2">
        <ValidationMatrix
          title="Accessibility verification"
          description="Keyboard, SR, focus, ARIA, contrast, reduced motion"
          rows={view.a11yWalkthrough}
        />
        <ValidationMatrix
          title="Cross-browser validation"
          description="Chrome · Edge · Firefox · Safari · Desktop/Tablet/Mobile"
          rows={view.crossBrowser}
        />
      </div>
    </div>
  );
}

export const ReleaseCandidateDashboardWorkspace = memo(
  function ReleaseCandidateDashboardWorkspace({ refreshTick }: { refreshTick: number }) {
    return <ReleaseCandidateDashboard refreshTick={refreshTick} />;
  },
);
