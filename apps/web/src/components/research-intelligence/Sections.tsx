"use client";

import { lazy, Suspense } from "react";

import { Badge, ErrorState } from "@/components/ds";
import {
  DATA_UNAVAILABLE,
  displayMetric,
  displayText,
  type RiWindowMonths,
} from "@/lib/research-intelligence";

import {
  FieldRow,
  MetricTile,
  SectionCard,
  WorkspaceEmpty,
  WorkspaceSkeleton,
} from "./Primitives";

const LazyTrendChart = lazy(() =>
  import("./TrendChart").then((m) => ({ default: m.TrendChart })),
);

function ChartFallback() {
  return <WorkspaceSkeleton />;
}

export function PerformanceSection({
  dashboard,
  status,
  windowMonths,
  onRetry,
}: {
  dashboard: Record<string, unknown> | null;
  status: "loading" | "error" | "empty" | "ready";
  windowMonths: RiWindowMonths;
  onRetry: () => void;
}) {
  if (status === "loading") return <WorkspaceSkeleton />;
  if (status === "error") {
    return (
      <ErrorState
        title="Unable to load performance"
        description="Research Intelligence API did not return a dashboard. No metrics were fabricated."
        action={
          <button
            type="button"
            className="text-sm underline"
            onClick={onRetry}
          >
            Retry
          </button>
        }
      />
    );
  }
  if (status === "empty" || !dashboard) {
    return (
      <WorkspaceEmpty
        title={DATA_UNAVAILABLE}
        description="Capture research snapshots after analysis to populate the performance workspace. Horizon market data is required for outcome metrics."
      />
    );
  }

  const coverage = (dashboard.coverage as Record<string, unknown>) || {};
  const trends = (dashboard.trends as Record<string, unknown>[]) || [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="font-[family-name:var(--font-display)] text-xl text-[var(--fg)]">
          Institutional Research Performance
        </h2>
        <Badge variant="outline">{windowMonths}m horizon</Badge>
        {dashboard.message ? (
          <Badge variant="default">{displayText(dashboard.message)}</Badge>
        ) : null}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile
          label="Overall Accuracy"
          value={displayMetric(dashboard.overall_accuracy)}
        />
        <MetricTile
          label="Recommendation Accuracy"
          value={displayMetric(dashboard.recommendation_accuracy)}
        />
        <MetricTile label="IV Error" value={displayMetric(dashboard.iv_error)} />
        <MetricTile label="Avg MoS" value={displayMetric(dashboard.avg_mos)} />
        <MetricTile
          label="Bull Success"
          value={displayMetric(dashboard.bull_success)}
        />
        <MetricTile
          label="Bear Success"
          value={displayMetric(dashboard.bear_success)}
        />
        <MetricTile
          label="False Positives"
          value={displayMetric(dashboard.false_positives)}
        />
        <MetricTile
          label="False Negatives"
          value={displayMetric(dashboard.false_negatives)}
        />
      </div>
      <SectionCard
        title="Coverage"
        description="Registry coverage for the selected holding horizon"
      >
        <dl>
          <FieldRow label="Snapshots" value={displayMetric(coverage.snapshot_count)} />
          <FieldRow label="Measured" value={displayMetric(coverage.measured_count)} />
          <FieldRow
            label="Unavailable outcomes"
            value={displayMetric(coverage.unavailable_outcome_count)}
          />
          <FieldRow
            label="Holding horizon"
            value={`${dashboard.holding_horizon_months ?? windowMonths} months`}
          />
        </dl>
      </SectionCard>
      <SectionCard title="Accuracy Trends" description="Measured periods only">
        <Suspense fallback={<ChartFallback />}>
          <LazyTrendChart trends={trends} />
        </Suspense>
      </SectionCard>
    </div>
  );
}

export function TimelineSection({
  timeline,
  status,
  symbolFilter,
  onSymbolChange,
  onRetry,
}: {
  timeline: Record<string, unknown>[];
  status: "loading" | "error" | "empty" | "ready";
  symbolFilter: string;
  onSymbolChange: (value: string) => void;
  onRetry: () => void;
}) {
  if (status === "loading") return <WorkspaceSkeleton />;
  if (status === "error") {
    return (
      <ErrorState
        title="Unable to load timeline"
        description="Historical snapshots could not be retrieved."
        action={
          <button type="button" className="text-sm underline" onClick={onRetry}>
            Retry
          </button>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-xl text-[var(--fg)]">
            Research Timeline
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Immutable snapshots — recommendation and confidence evolution
          </p>
        </div>
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Filter symbol</span>
          <input
            value={symbolFilter}
            onChange={(e) => onSymbolChange(e.target.value.toUpperCase())}
            className="mt-1 block w-full min-w-[10rem] rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2"
            placeholder="e.g. AAPL"
            aria-label="Filter timeline by symbol"
          />
        </label>
      </div>
      {status === "empty" || timeline.length === 0 ? (
        <WorkspaceEmpty
          title={DATA_UNAVAILABLE}
          description="No research snapshots are registered yet. Snapshots are captured after completed analysis or via the capture API."
        />
      ) : (
        <ol className="space-y-3" aria-label="Research snapshot timeline">
          {timeline.map((row) => (
            <li
              key={String(row.research_id)}
              className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium text-[var(--fg)]">
                  {displayText(row.research_id)}
                </p>
                <time className="text-xs text-[var(--muted)]">
                  {displayText(row.timestamp)}
                </time>
              </div>
              <dl className="mt-2 grid gap-1 sm:grid-cols-2">
                <FieldRow
                  label="Recommendation"
                  value={displayText(row.recommendation)}
                />
                <FieldRow
                  label="Confidence"
                  value={displayMetric(row.confidence)}
                />
                <FieldRow label="Price" value={displayMetric(row.price)} />
                <FieldRow
                  label="MoS"
                  value={displayMetric(row.margin_of_safety)}
                />
                <FieldRow
                  label="Research version"
                  value={displayText(row.research_version)}
                />
                <FieldRow
                  label="Model version"
                  value={displayText(row.model_version)}
                />
              </dl>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function CalibrationSection({
  calibration,
  status,
  windowMonths,
  onRetry,
}: {
  calibration: Record<string, unknown> | null;
  status: "loading" | "error" | "empty" | "ready";
  windowMonths: RiWindowMonths;
  onRetry: () => void;
}) {
  if (status === "loading") return <WorkspaceSkeleton />;
  if (status === "error") {
    return (
      <ErrorState
        title="Unable to load calibration"
        description="Calibration report unavailable from API."
        action={
          <button type="button" className="text-sm underline" onClick={onRetry}>
            Retry
          </button>
        }
      />
    );
  }
  if (status === "empty" || !calibration) {
    return (
      <WorkspaceEmpty
        title={DATA_UNAVAILABLE}
        description="Calibration requires measured outcomes with horizon prices."
      />
    );
  }

  const buckets =
    (calibration.bucket_accuracy as Record<string, Record<string, unknown>>) ||
    {};
  const curve =
    (calibration.calibration_curve as Record<string, unknown>[]) || [];
  const drift = (calibration.drift as Record<string, unknown>) || {};
  const reliability =
    (calibration.reliability as Record<string, unknown>) || {};

  return (
    <div className="space-y-4">
      <h2 className="font-[family-name:var(--font-display)] text-xl text-[var(--fg)]">
        Confidence Calibration ({windowMonths}m)
      </h2>
      <div className="grid gap-3 sm:grid-cols-3">
        {(["high", "medium", "low"] as const).map((bucket) => (
          <MetricTile
            key={bucket}
            label={`${bucket} accuracy`}
            value={displayMetric(buckets[bucket]?.accuracy)}
          />
        ))}
      </div>
      <SectionCard title="Calibration curve" description="Expected vs observed">
        <ul className="space-y-2 text-sm">
          {curve.map((point) => (
            <li
              key={String(point.bucket)}
              className="flex flex-wrap justify-between gap-2 border-b border-[var(--border)] py-2 last:border-0"
            >
              <span className="capitalize text-[var(--muted)]">
                {displayText(point.bucket)}
              </span>
              <span>
                expected {displayMetric(point.expected_confidence)} · observed{" "}
                {displayMetric(point.observed_accuracy)} · gap{" "}
                {displayMetric(point.gap)}
              </span>
            </li>
          ))}
        </ul>
      </SectionCard>
      <SectionCard title="Drift & reliability">
        <dl>
          <FieldRow label="Drift status" value={displayText(drift.status)} />
          <FieldRow
            label="Mean absolute gap"
            value={displayMetric(drift.mean_absolute_gap)}
          />
          <FieldRow
            label="Overall accuracy"
            value={displayMetric(reliability.overall_accuracy)}
          />
          <FieldRow
            label="Brier proxy"
            value={displayMetric(reliability.brier_proxy)}
          />
        </dl>
      </SectionCard>
    </div>
  );
}

export function InsightsSection({
  insights,
  status,
  windowMonths,
  onRetry,
}: {
  insights: Record<string, unknown> | null;
  status: "loading" | "error" | "empty" | "ready";
  windowMonths: RiWindowMonths;
  onRetry: () => void;
}) {
  if (status === "loading") return <WorkspaceSkeleton />;
  if (status === "error") {
    return (
      <ErrorState
        title="Unable to load insights"
        description="Research Intelligence insights unavailable."
        action={
          <button type="button" className="text-sm underline" onClick={onRetry}>
            Retry
          </button>
        }
      />
    );
  }
  if (status === "empty" || !insights) {
    return (
      <WorkspaceEmpty
        title={DATA_UNAVAILABLE}
        description="Insights require measured outcomes. Missing horizon prices stay unavailable."
      />
    );
  }

  const best = (insights.best_performers as Record<string, unknown>[]) || [];
  const worst = (insights.worst_performers as Record<string, unknown>[]) || [];
  const gaps = (insights.coverage_gaps as Record<string, unknown>[]) || [];
  const sectors =
    (insights.sector_performance as Record<string, unknown>[]) || [];

  return (
    <div className="space-y-4">
      <h2 className="font-[family-name:var(--font-display)] text-xl text-[var(--fg)]">
        Research Intelligence ({windowMonths}m)
      </h2>
      <SectionCard title="Best performers">
        {best.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">{DATA_UNAVAILABLE}</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {best.map((row) => (
              <li key={String(row.research_id)}>
                {displayText(row.symbol)} ·{" "}
                {displayMetric(row.price_change_pct)} ·{" "}
                {displayText(row.recommendation_accuracy)}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Worst performers">
        {worst.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">{DATA_UNAVAILABLE}</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {worst.map((row) => (
              <li key={String(row.research_id)}>
                {displayText(row.symbol)} ·{" "}
                {displayMetric(row.price_change_pct)} ·{" "}
                {displayText(row.recommendation_accuracy)}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Coverage gaps">
        {gaps.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No coverage gaps reported.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {gaps.slice(0, 20).map((row) => (
              <li key={String(row.research_id)}>
                {displayText(row.symbol)} — {displayText(row.reason)}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Sector performance">
        {sectors.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">{DATA_UNAVAILABLE}</p>
        ) : (
          <dl>
            {sectors.map((row) => (
              <FieldRow
                key={String(row.sector)}
                label={displayText(row.sector)}
                value={displayMetric(row.accuracy)}
              />
            ))}
          </dl>
        )}
      </SectionCard>
    </div>
  );
}
