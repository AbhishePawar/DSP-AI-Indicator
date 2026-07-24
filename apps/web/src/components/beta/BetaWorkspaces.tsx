"use client";

import { memo, useMemo, useState } from "react";
import { usePathname } from "next/navigation";

import { useFeedback } from "@/components/beta/FeedbackContext";
import { ReleaseCandidateDashboard } from "@/components/rc/ReleaseCandidateDashboard";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState, SuccessState } from "@/components/ui/EmptyState";
import { WindowedList } from "@/lib/perf/WindowedList";
import {
  FEEDBACK_CATEGORIES,
  ISSUE_STATUSES,
  ensureAnalytics,
  buildBetaDashboard,
  buildReleaseCandidate,
  listFeedback,
  listIssues,
  updateIssueStatus,
  type FeedbackRecord,
  type IssueRecord,
  type IssueStatus,
} from "@/lib/beta/betaModel";
import { recordResolution } from "@/lib/rc/rcStabilizationModel";

function severityTone(s: string): "danger" | "warning" | "neutral" | "accent" {
  if (s === "critical") return "danger";
  if (s === "high") return "warning";
  if (s === "medium") return "accent";
  return "neutral";
}

export function IssueStatusBadge({ status }: { status: IssueStatus }) {
  const tone =
    status === "resolved"
      ? ("success" as const)
      : status === "open" || status === "in_progress"
        ? ("warning" as const)
        : ("neutral" as const);
  return <Badge tone={tone}>{status.replace(/_/g, " ")}</Badge>;
}

export function IssueCard({
  issue,
  onStatus,
}: {
  issue: IssueRecord;
  onStatus: (id: string, status: IssueStatus) => void;
}) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={issue.title}
        action={<IssueStatusBadge status={issue.status} />}
      />
      <CardBody className="space-y-2 text-sm">
        <div className="flex flex-wrap gap-2">
          <Badge tone={severityTone(issue.severity)}>{issue.severity}</Badge>
          <Badge tone="neutral">{issue.priority}</Badge>
          <Badge tone="neutral">{issue.component}</Badge>
        </div>
        <p className="text-xs text-[var(--muted)]">
          Updated {new Date(issue.updatedAt).toLocaleString()}
        </p>
        <label className="block text-xs">
          Status
          <select
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            value={issue.status}
            onChange={(e) => onStatus(issue.id, e.target.value as IssueStatus)}
          >
            {ISSUE_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </label>
      </CardBody>
    </Card>
  );
}

export function FeedbackListCard({ item }: { item: FeedbackRecord }) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={item.title}
        action={<Badge tone={severityTone(item.severity)}>{item.severity}</Badge>}
      />
      <CardBody className="space-y-2 text-sm">
        <p className="text-xs text-[var(--muted)]">
          {FEEDBACK_CATEGORIES.find((c) => c.id === item.category)?.label} · {item.pagePath}
        </p>
        <p>{item.description}</p>
        <p className="text-xs text-[var(--muted)]">{item.trustNote}</p>
        <p className="text-xs text-[var(--muted)]">
          v{item.appVersion} · {new Date(item.createdAt).toLocaleString()}
        </p>
      </CardBody>
    </Card>
  );
}

export const FeedbackWorkspace = memo(function FeedbackWorkspace() {
  const { openFeedback, refreshTick, startTour } = useFeedback();
  const pathname = usePathname();
  const items = useMemo(() => listFeedback(), [refreshTick]);

  return (
    <div className="space-y-4">
      <p className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm">
        Structured Private Beta feedback stays on this device. Never paste research envelopes,
        portfolio holdings, or API secrets.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => openFeedback()}>New feedback</Button>
        <Button
          variant="secondary"
          onClick={() => openFeedback({ sectionId: "page", category: "ux_feedback" })}
        >
          Page feedback
        </Button>
        <Button
          variant="secondary"
          onClick={() =>
            openFeedback({ sectionId: pathname.split("/")[1] || "section", category: "ux_feedback" })
          }
        >
          Section feedback
        </Button>
        <Button variant="ghost" onClick={startTour}>
          Restart tutorial
        </Button>
      </div>
      <WindowedList
        items={items}
        empty={
          <EmptyState
            title="No feedback yet"
            description="Submit a bug, feature request, or UX note — research and portfolio data stay out of this store."
            actionLabel="New feedback"
            onAction={() => openFeedback()}
          />
        }
        renderItem={(f) => <FeedbackListCard key={f.id} item={f} />}
      />
    </div>
  );
});

export function BetaDashboard({ refreshTick }: { refreshTick: number }) {
  const dash = useMemo(() => buildBetaDashboard(), [refreshTick]);
  const tiles = [
    { label: "Active testers", value: String(dash.activeTesters) },
    { label: "Feedback received", value: String(dash.feedbackReceived) },
    { label: "Critical bugs", value: String(dash.criticalBugs) },
    { label: "Open issues", value: String(dash.openIssues) },
    { label: "Resolved issues", value: String(dash.resolvedIssues) },
    {
      label: "Average satisfaction",
      value: dash.averageSatisfaction != null ? String(dash.averageSatisfaction) : "Unavailable",
    },
  ];
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Release readiness" />
        <CardBody className="text-sm font-medium">{dash.releaseReadiness}</CardBody>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {tiles.map((t) => (
          <Card key={t.label}>
            <CardHeader title={t.label} />
            <CardBody className="text-2xl font-medium">{t.value}</CardBody>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader title="Top requested features" />
        <CardBody>
          <ol className="list-decimal space-y-1 pl-5 text-sm">
            {dash.topRequestedFeatures.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ol>
        </CardBody>
      </Card>
    </div>
  );
}

export const BetaDashboardWorkspace = memo(function BetaDashboardWorkspace() {
  const { refreshTick } = useFeedback();
  return <BetaDashboard refreshTick={refreshTick} />;
});

export const IssueTrackerWorkspace = memo(function IssueTrackerWorkspace() {
  const { refreshTick, bumpRefresh } = useFeedback();
  const [filter, setFilter] = useState<IssueStatus | "all">("all");
  const issues = useMemo(() => listIssues(), [refreshTick]);
  const visible =
    filter === "all" ? issues : issues.filter((i) => i.status === filter);

  const onStatus = (id: string, status: IssueStatus) => {
    const prev = issues.find((i) => i.id === id);
    updateIssueStatus(id, status);
    if (prev && status === "resolved") {
      recordResolution({
        id: `tracker-${id}`,
        title: prev.title,
        severity: prev.severity,
        component: prev.component,
        before: `Status was ${prev.status}`,
        after: "Marked resolved in Issue Tracker",
        verification: "Status badge shows resolved; RC score recalculated",
        status: "resolved",
      });
    }
    bumpRefresh();
  };

  return (
    <div className="space-y-4">
      {filter === "resolved" && visible.length > 0 ? (
        <SuccessState
          title={`${visible.length} resolved`}
          description="Stabilization progress tracked with Before → After → Verification on the RC dashboard."
        />
      ) : null}
      <label className="block text-sm">
        Filter status
        <select
          className="mt-1 min-h-11 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          value={filter}
          onChange={(e) => setFilter(e.target.value as IssueStatus | "all")}
        >
          <option value="all">All</option>
          {ISSUE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </label>
      <WindowedList
        items={visible}
        empty={
          <EmptyState
            title="No issues in this filter"
            description="Open feedback for bugs, a11y, or performance to seed the tracker."
          />
        }
        renderItem={(i) => <IssueCard key={i.id} issue={i} onStatus={onStatus} />}
      />
    </div>
  );
});

export function ReleaseCandidateCard({ refreshTick }: { refreshTick: number }) {
  const rc = useMemo(() => buildReleaseCandidate(), [refreshTick]);
  const tone =
    rc.decision === "GO" ? "success" : rc.decision === "NO-GO" ? "danger" : "warning";
  return (
    <Card className="border-[var(--accent)]/40">
      <CardHeader title="Go / No-Go" action={<Badge tone={tone}>{rc.decision}</Badge>} />
      <CardBody className="space-y-2 text-sm">
        <p>{rc.rationale}</p>
        <ul className="list-disc pl-5 text-[var(--muted)]">
          <li>Outstanding bugs: {rc.outstandingBugs}</li>
          <li>Accessibility: {rc.accessibilityStatus}</li>
          <li>Performance: {rc.performanceStatus}</li>
          <li>Security: {rc.securityStatus}</li>
          <li>Regression: {rc.regressionStatus}</li>
        </ul>
      </CardBody>
    </Card>
  );
}

export const ReleaseCandidateWorkspace = memo(function ReleaseCandidateWorkspace() {
  const { refreshTick } = useFeedback();
  return (
    <div className="space-y-6">
      <ReleaseCandidateCard refreshTick={refreshTick} />
      <ReleaseCandidateDashboard refreshTick={refreshTick} />
      <Card>
        <CardHeader title="RC soak notes" />
        <CardBody className="text-sm text-[var(--muted)]">
          Web 1.0.0 is the stable public release promoted from RC 0.9.5. Use `/launch` for live
          quality gates and `/launch/report` for post-launch review. Research outputs and portfolio
          math remain unchanged.
        </CardBody>
      </Card>
    </div>
  );
});

export function AnalyticsPlaceholderCard() {
  const a = useMemo(() => ensureAnalytics(), []);
  return (
    <Card>
      <CardHeader
        title="Analytics layer (placeholder)"
        description="Local counters only — no third-party SDK"
      />
      <CardBody className="grid gap-2 text-sm sm:grid-cols-2">
        <p>Session: {a.sessionId}</p>
        <p>Search frequency: {a.searchFrequency}</p>
        <p>Export frequency: {a.exportFrequency}</p>
        <p>Portfolio usage: {a.portfolioUsage}</p>
        <p>Copilot usage: {a.copilotUsage}</p>
        <p>Nav flow depth: {a.navigationFlow.length}</p>
        <div className="sm:col-span-2">
          <p className="text-xs font-medium uppercase text-[var(--muted)]">Page visits</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {Object.entries(a.pageVisits)
              .slice(0, 8)
              .map(([p, n]) => (
                <li key={p}>
                  {p}: {n}
                </li>
              ))}
          </ul>
        </div>
        <div className="sm:col-span-2">
          <p className="text-xs font-medium uppercase text-[var(--muted)]">Feature usage</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {Object.entries(a.featureUsage).length === 0 ? (
              <li>None yet</li>
            ) : (
              Object.entries(a.featureUsage)
                .slice(0, 8)
                .map(([f, n]) => (
                  <li key={f}>
                    {f}: {n}
                  </li>
                ))
            )}
          </ul>
        </div>
      </CardBody>
    </Card>
  );
}
