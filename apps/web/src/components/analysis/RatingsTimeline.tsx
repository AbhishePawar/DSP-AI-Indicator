"use client";

/**
 * Ratings Timeline — ARCH-002 / P9.4 extension.
 *
 * A "Ratings Timeline" represents HISTORICAL ratings across different
 * dates/analysis runs. The current /api/v1/analyse contract provides only a
 * single analysis snapshot and does NOT supply genuine historical rating
 * observations.
 *
 * Therefore:
 * - This component does NOT present current module-level scorecard ratings
 *   as historical observations.
 * - When no genuine historical data is available, a clear empty state is shown.
 * - The data contract below is defined so real historical observations can be
 *   wired in later without changing the component interface.
 *
 * Data contract for future historical observations:
 *   HistoricalRatingObservation[] — each entry must come from a distinct
 *   analysis run with a real date supplied by the backend.
 */

import { SectionCard } from "@/components/company-analysis/WorkspacePrimitives";
import { cn } from "@/lib/utils";
import type { ResearchView } from "@/lib/research/mapResearchView";

// ─── Data contract (for future wiring) ───────────────────────────────────────

/**
 * A single historical rating observation.
 * Each entry MUST correspond to a distinct analysis run with a real date
 * supplied by the backend. Do NOT fabricate or infer these values.
 */
export type HistoricalRatingObservation = {
  /** ISO date string of the analysis run — must be supplied by the API */
  date: string;
  /** Display label for the period, e.g. "Q2 2025" */
  periodLabel: string;
  /** Overall score out of 10, e.g. 7.2 */
  overallScore: number;
  /** Letter grade, e.g. "B+" */
  overallGrade: string;
  /** Recommendation label, e.g. "Accumulate" */
  recommendation: string;
  /**
   * Direction of change vs. previous observation.
   * Only set when a prior observation exists in the series.
   */
  changeDirection?: "improved" | "declined" | "unchanged";
};

/**
 * Props for RatingsTimeline.
 *
 * @param view          - Current analysis snapshot (used for ticker/context only).
 * @param history       - Genuine historical observations from the backend.
 *                        Pass an empty array or omit when unavailable.
 * @param isLoading     - True while data is being fetched.
 * @param error         - Error message if the fetch failed.
 */
export type RatingsTimelineProps = {
  view: ResearchView;
  /** Genuine historical rating observations. Empty array = no history available. */
  history?: HistoricalRatingObservation[];
  isLoading?: boolean;
  error?: string | null;
};

// ─── Helper ───────────────────────────────────────────────────────────────────

function gradeColor(grade: string): string {
  switch (grade) {
    case "A+": case"A":
      return "text-[var(--success-fg,#16a34a)]";
    case "B+": case"B":
      return "text-[var(--accent)]";
    case "C":
      return "text-[var(--warning-fg,#d97706)]";
    case "D": case"F":
      return "text-[var(--danger-fg)]";
    default:
      return "text-[var(--muted)]";
  }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function HistoryRow({ obs, index }: { obs: HistoricalRatingObservation; index: number }) {
  const pct = Math.min(100, Math.max(0, (obs.overallScore / 10) * 100));
  const changeIcon =
    obs.changeDirection === "improved" ?"↑"
      : obs.changeDirection === "declined" ?"↓"
        : obs.changeDirection === "unchanged" ?"≈"
          : null;

  return (
    <li
      className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
      aria-label={`${obs.periodLabel}: ${obs.overallGrade}, score ${obs.overallScore}/10`}
    >
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--muted)]">{obs.periodLabel}</span>
          {changeIcon && index > 0 ? (
            <span
              className={cn(
                "text-xs font-medium",
                obs.changeDirection === "improved" ?"text-[var(--success-fg,#16a34a)]"
                  : obs.changeDirection === "declined" ?"text-[var(--danger-fg,#dc2626)]" :"text-[var(--muted)]",
              )}
            >
              {changeIcon}
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-[var(--muted)]">{obs.recommendation}</span>
          <span
            className={cn(
              "font-[family-name:var(--font-display)] text-lg font-semibold",
              gradeColor(obs.overallGrade),
            )}
          >
            {obs.overallGrade}
          </span>
          <span className="text-sm font-medium">{obs.overallScore.toFixed(1)}/10</span>
        </div>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-[var(--border)]"
        role="meter"
        aria-valuenow={obs.overallScore}
        aria-valuemin={0}
        aria-valuemax={10}
        aria-label={`Score: ${obs.overallScore}/10`}
      >
        <div
          className="h-full rounded-full bg-[var(--accent)] transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </li>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function HistoryUnavailableNotice({ ticker }: { ticker: string }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-5 py-8 text-center">
      {/* Icon */}
      <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-[var(--border)]">
        <svg
          className="h-5 w-5 text-[var(--muted)]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 6v6l4 2m6-2a10 10 0 11-20 0 10 10 0 0120 0z"
          />
        </svg>
      </div>

      <p className="text-sm font-medium text-[var(--fg)]">
        Historical ratings are not available yet
      </p>
      <p className="mt-1 text-xs text-[var(--muted)]">
        Ratings history for{" "}
        <span className="font-medium">{ticker}</span> will appear after
        historical analysis data is stored across multiple analysis runs.
      </p>

      <div className="mt-4 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-4 py-3 text-left">
        <p className="text-xs font-medium text-[var(--fg)]">
          Why is this section empty?
        </p>
        <p className="mt-1 text-xs text-[var(--muted)]">
          The current analysis contains only the latest snapshot from{" "}
          <code className="rounded bg-[var(--border)] px-1">/api/v1/analyse</code>.
          This endpoint returns a single point-in-time result and does not
          supply historical rating observations across different dates or
          analysis runs. No historical data has been fabricated or inferred.
        </p>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Once the platform stores results from multiple analysis runs over
          time, genuine historical observations will be displayed here as a
          chronological ratings timeline.
        </p>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function RatingsTimeline({
  view,
  history = [],
  isLoading,
  error,
}: RatingsTimelineProps) {
  // Loading state
  if (isLoading) {
    return (
      <SectionCard
        title="Ratings Timeline"
        description="Loading ratings history…"
      >
        <div className="space-y-3" aria-busy="true" aria-label="Loading ratings timeline">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 animate-pulse rounded-[var(--radius-md)] bg-[var(--border)]"
            />
          ))}
        </div>
      </SectionCard>
    );
  }

  // Error state
  if (error) {
    return (
      <SectionCard title="Ratings Timeline">
        <p className="text-sm text-[var(--danger-fg)]" role="alert">
          {error}
        </p>
      </SectionCard>
    );
  }

  const hasHistory = history.length > 0;

  return (
    <SectionCard
      title="Ratings Timeline"
      description={
        hasHistory
          ? `${history.length} historical observation${history.length === 1 ? "" : "s"} · ${view.ticker}`
          : "Historical rating observations across analysis runs"
      }
    >
      {hasHistory ? (
        /* Genuine historical observations — rendered when real data is wired in */
        <ul className="space-y-2" aria-label="Historical rating observations">
          {history.map((obs, i) => (
            <HistoryRow key={obs.date} obs={obs} index={i} />
          ))}
        </ul>
      ) : (
        /* No historical data available — show honest empty state */
        <HistoryUnavailableNotice ticker={view.ticker || "this company"} />
      )}
    </SectionCard>
  );
}
