"use client";

import { memo, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import {
  BREAKPOINTS,
  SECURITY_FINDINGS,
  buildLaunchChecklists,
  buildLaunchReadiness,
  buildPerformanceMetrics,
  type GateStatus,
  type PerformanceMetric,
  type QualityGate,
} from "@/lib/launch/launchModel";
import { env } from "@/lib/env";

function statusTone(status: GateStatus): "success" | "warning" | "danger" | "neutral" {
  if (status === "pass") return "success";
  if (status === "warn") return "warning";
  if (status === "fail") return "danger";
  return "neutral";
}

export function LaunchReadinessCard({
  score,
  risk,
  recommendation,
}: {
  score: number;
  risk: string;
  recommendation: string;
}) {
  return (
    <Card className="border-[var(--accent)]/40">
      <CardHeader
        title="Overall launch score"
        action={<Badge tone="accent">{score}/100</Badge>}
      />
      <CardBody className="space-y-2 text-sm">
        <p>
          Risk level: <span className="font-medium capitalize">{risk}</span>
        </p>
        <p className="text-[var(--muted)]">{recommendation}</p>
      </CardBody>
    </Card>
  );
}

export function QualityGateCard({ gate }: { gate: QualityGate }) {
  return (
    <Card>
      <CardHeader
        title={gate.label}
        action={<Badge tone={statusTone(gate.status)}>{gate.status}</Badge>}
      />
      <CardBody className="text-sm">
        <p>{gate.detail}</p>
        <p className="mt-2 text-xs text-[var(--muted)]">Score {gate.score}/100</p>
      </CardBody>
    </Card>
  );
}

export function PerformanceMetricCard({ metric }: { metric: PerformanceMetric }) {
  return (
    <Card>
      <CardHeader
        title={metric.label}
        action={<Badge tone={statusTone(metric.status)}>{metric.status}</Badge>}
      />
      <CardBody className="text-sm">
        <p className="text-lg font-medium">{metric.value}</p>
        <p className="mt-1 text-[var(--muted)]">Target: {metric.target}</p>
        <p className="mt-2 text-xs text-[var(--muted)]">{metric.methodology}</p>
      </CardBody>
    </Card>
  );
}

export function HealthStatusCard({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <Card>
      <CardHeader title={title} />
      <CardBody className="text-sm text-[var(--muted)]">{detail}</CardBody>
    </Card>
  );
}

export function BuildInformationCard() {
  return (
    <Card>
      <CardHeader title="Build information" />
      <CardBody className="space-y-1 text-sm">
        <p>App: {env.appName}</p>
        <p>Web version: 1.0.0</p>
        <p>Epic: Phase C — Soak Test & Public Launch</p>
        <p>Node/Next: Next.js 15 · React 19</p>
        <p className="text-xs text-[var(--muted)]">
          Bundle analyzer: set ANALYZE=true when @next/bundle-analyzer is installed in CI.
        </p>
      </CardBody>
    </Card>
  );
}

export function VersionCard() {
  return (
    <Card>
      <CardHeader title="Version" />
      <CardBody className="text-sm">
        <p className="text-2xl font-medium">1.0.0</p>
        <p className="text-[var(--muted)]">Stable public release · promoted from RC 0.9.5</p>
      </CardBody>
    </Card>
  );
}

export function EnvironmentCard() {
  return (
    <Card>
      <CardHeader title="Environment" />
      <CardBody className="space-y-1 text-sm">
        <p>API base: {env.apiBaseUrl}</p>
        <p>Runtime: browser thin client</p>
        <p className="text-xs text-[var(--muted)]">
          No secrets beyond public API URL in NEXT_PUBLIC_* vars.
        </p>
      </CardBody>
    </Card>
  );
}

export function PerformanceStatusCard({ metrics }: { metrics: PerformanceMetric[] }) {
  const pending = metrics.filter((m) => m.status === "pending").length;
  const warn = metrics.filter((m) => m.status === "warn").length;
  return (
    <Card>
      <CardHeader title="Performance status" />
      <CardBody className="text-sm">
        <p>
          {metrics.length - pending - warn} measured pass · {warn} warn · {pending} pending
        </p>
      </CardBody>
    </Card>
  );
}

export function ErrorCounterCard({ count }: { count: number }) {
  return (
    <Card>
      <CardHeader title="Client error counter" description="Session placeholder" />
      <CardBody>
        <p className="text-2xl font-medium">{count}</p>
        <p className="text-xs text-[var(--muted)]">
          MonitoringHookPlaceholder — wire to observability backend later.
        </p>
      </CardBody>
    </Card>
  );
}

export function SecurityAuditCard() {
  return (
    <Card>
      <CardHeader title="Security audit" />
      <CardBody className="space-y-3">
        {SECURITY_FINDINGS.map((f) => (
          <div key={f.id} className="rounded-md border border-[var(--border)] p-2 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{f.title}</span>
              <Badge tone={statusTone(f.status)}>{f.status}</Badge>
            </div>
            <p className="mt-1 text-[var(--muted)]">{f.detail}</p>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}

export function AccessibilityAuditCard() {
  return (
    <Card>
      <CardHeader title="Accessibility audit" description="WCAG AA targets" />
      <CardBody className="text-sm space-y-2">
        <ul className="list-disc pl-5 text-[var(--muted)]">
          <li>Keyboard navigation & skip link</li>
          <li>Focus-visible rings · focus trap on Copilot dialog</li>
          <li>ARIA labels on nav, dialogs, live regions</li>
          <li>Touch targets ≥ 44px (min-h-11)</li>
          <li>Reduced motion + theme contrast tokens</li>
        </ul>
      </CardBody>
    </Card>
  );
}

export function ReleaseNotesCard() {
  return (
    <Card>
      <CardHeader title="Release notes" />
      <CardBody className="text-sm text-[var(--muted)]">
        See <code>docs/RELEASE_NOTES_v0.8.0.md</code> — production readiness, no investment
        logic changes.
      </CardBody>
    </Card>
  );
}

export function DeploymentChecklist() {
  const items = [
    "Set NEXT_PUBLIC_API_BASE_URL for target environment",
    "Enable DSP_ENABLE_SECURITY on API",
    "Run pytest regression GREEN",
    "next build && next start smoke",
    "Verify /health and /launch readiness",
    "Confirm CSP report-only in staging",
  ];
  return (
    <Card>
      <CardHeader title="Deployment checklist" />
      <CardBody>
        <ol className="list-decimal space-y-1 pl-5 text-sm">
          {items.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ol>
      </CardBody>
    </Card>
  );
}

export function MonitoringHookPlaceholder() {
  return (
    <HealthStatusCard
      title="Monitoring hook"
      detail="Placeholder — attach RUM / error reporting SDK in operator environment without changing product logic."
    />
  );
}

export function AnalyticsHookPlaceholder() {
  return (
    <HealthStatusCard
      title="Analytics hook"
      detail="Placeholder — privacy-preserving product analytics deferred; no PII collection in Sprint 9."
    />
  );
}

export const LaunchReadinessWorkspace = memo(function LaunchReadinessWorkspace() {
  const readiness = useMemo(() => buildLaunchReadiness(), []);
  return (
    <div className="space-y-4">
      <LaunchReadinessCard
        score={readiness.overallScore}
        risk={readiness.riskLevel}
        recommendation={readiness.recommendation}
      />
      <p className="text-xs text-[var(--muted)]">
        {readiness.version} · generated {readiness.generatedAt}
      </p>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {readiness.gates.map((g) => (
          <QualityGateCard key={g.id} gate={g} />
        ))}
      </div>
      <Card>
        <CardHeader title="Remaining issues" />
        <CardBody>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {readiness.remainingIssues.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        </CardBody>
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        <ReleaseNotesCard />
        <DeploymentChecklist />
      </div>
    </div>
  );
});

export const PerformanceWorkspace = memo(function PerformanceWorkspace() {
  const [runtime, setRuntime] = useState<{
    fcp?: number | null;
    lcp?: number | null;
    cls?: number | null;
    memoryMb?: number | null;
    tti?: number | null;
    routeMs?: number | null;
  }>({});

  useEffect(() => {
    const nav = performance.getEntriesByType("navigation")[0] as
      | PerformanceNavigationTiming
      | undefined;
    const paints = performance.getEntriesByType("paint");
    const fcp = paints.find((p) => p.name === "first-contentful-paint")?.startTime ?? null;
    const tti = nav ? nav.domInteractive : null;
    const routeMs = nav ? nav.responseEnd - nav.requestStart : null;

    let memoryMb: number | null = null;
    const perf = performance as Performance & {
      memory?: { usedJSHeapSize: number };
    };
    if (perf.memory?.usedJSHeapSize) {
      memoryMb = perf.memory.usedJSHeapSize / (1024 * 1024);
    }

    let cls = 0;
    let lcp: number | null = null;
    try {
      const po = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === "largest-contentful-paint") {
            lcp = entry.startTime;
            setRuntime((r) => ({ ...r, lcp }));
          }
          if (entry.entryType === "layout-shift" && !(entry as PerformanceEntry & { hadRecentInput?: boolean }).hadRecentInput) {
            cls += (entry as PerformanceEntry & { value: number }).value;
            setRuntime((r) => ({ ...r, cls }));
          }
        }
      });
      po.observe({ type: "largest-contentful-paint", buffered: true } as PerformanceObserverInit);
      po.observe({ type: "layout-shift", buffered: true } as PerformanceObserverInit);
    } catch {
      /* unsupported */
    }

    setRuntime({ fcp, lcp, cls: cls || null, memoryMb, tti, routeMs });
  }, []);

  const metrics = useMemo(() => buildPerformanceMetrics(runtime), [runtime]);

  return (
    <div className="space-y-4">
      <PerformanceStatusCard metrics={metrics} />
      <Card>
        <CardHeader
          title="Audits"
          description="Bundle analyzer · route splitting · lazy imports · memoization · fonts · cache"
        />
        <CardBody className="space-y-2 text-sm text-[var(--muted)]">
          <p>Route code splitting: Next.js app router per-page bundles.</p>
          <p>Lazy import: Copilot panel uses React.lazy.</p>
          <p>Memoization: AnalysisWorkspace, PortfolioWorkspace, KG cards memoized.</p>
          <p>Fonts: next/font (Fraunces, Sora) — no FOIT layout thrash from external CSS.</p>
          <p>Images: no unoptimized marketing heroes in app shell.</p>
          <p>Cache: TanStack Query for API health/analyze; sessionStorage for recovery meta.</p>
          <p>
            Bundle analyzer: document <code>ANALYZE=true next build</code> with
            @next/bundle-analyzer in CI.
          </p>
        </CardBody>
      </Card>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {metrics.map((m) => (
          <PerformanceMetricCard key={m.id} metric={m} />
        ))}
      </div>
    </div>
  );
});

export const HealthStatusWorkspace = memo(function HealthStatusWorkspace() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <BuildInformationCard />
        <VersionCard />
        <EnvironmentCard />
        <ErrorCounterCard count={0} />
        <MonitoringHookPlaceholder />
        <AnalyticsHookPlaceholder />
      </div>
      <HealthStatusCard
        title="API health"
        detail="Live API checks remain on /health — this workspace is frontend ops telemetry."
      />
    </div>
  );
});

export const LaunchChecklistWorkspace = memo(function LaunchChecklistWorkspace() {
  const groups = useMemo(() => buildLaunchChecklists(), []);
  return (
    <div className="space-y-6">
      {groups.map((g) => (
        <Card key={g.id}>
          <CardHeader title={g.title} />
          <CardBody>
            <ul className="space-y-2">
              {g.items.map((item) => (
                <li
                  key={item.id}
                  className="flex flex-wrap items-start justify-between gap-2 rounded-md border border-[var(--border)] px-3 py-2 text-sm"
                >
                  <div>
                    <p className="font-medium">{item.label}</p>
                    <p className="text-xs text-[var(--muted)]">{item.notes}</p>
                  </div>
                  <Badge tone={statusTone(item.status)}>{item.status}</Badge>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      ))}
      <Card>
        <CardHeader title="Responsive breakpoints" />
        <CardBody className="flex flex-wrap gap-2 text-sm">
          {BREAKPOINTS.map((bp) => (
            <Badge key={bp} tone="neutral">
              {bp}px
            </Badge>
          ))}
          <Badge tone="neutral">Landscape</Badge>
          <Badge tone="neutral">Portrait</Badge>
        </CardBody>
      </Card>
      <AccessibilityAuditCard />
      <SecurityAuditCard />
    </div>
  );
});
