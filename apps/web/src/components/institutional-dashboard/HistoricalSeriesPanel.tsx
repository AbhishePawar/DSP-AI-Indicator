import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import { Alert } from "@/components/ds";
import type { HistoricalSeriesView } from "@/lib/institutional-dashboard/types";
import { DATA_UNAVAILABLE } from "@/lib/institutional-dashboard/types";

export function HistoricalSeriesPanel({ view }: { view: HistoricalSeriesView }) {
  return (
    <SectionShell
      id="historical-series"
      title="Historical Time Series"
      description="Authenticated history only — no indicators, TA, or adjusted prices"
    >
      {!view.hasAuthenticatedHistoricalSeries ? (
        <Alert variant="warning">
          Authenticated historical-series feed is not attached. Fields show{" "}
          {DATA_UNAVAILABLE} — no fabricated OHLCV or derived indicators.
        </Alert>
      ) : null}
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCell label="Data source" field={view.source} />
        <MetricCell label="Series kind" field={view.seriesKind} />
        <MetricCell label="Frequency" field={view.frequency} />
        <MetricCell label="Date range" field={view.dateRange} />
        <MetricCell label="Point count" field={view.pointCount} />
        <MetricCell label="Snapshot count" field={view.snapshotCount} />
      </div>
      {view.bars.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">
          Recent OHLCV bars: {DATA_UNAVAILABLE}
        </p>
      ) : (
        <ul className="space-y-3">
          {view.bars.map((bar, index) => (
            <li
              key={`${bar.date.display}-${index}`}
              className="grid gap-3 border-t border-[var(--border)] pt-3 sm:grid-cols-3 lg:grid-cols-6"
            >
              <MetricCell label="Date" field={bar.date} />
              <MetricCell label="Open" field={bar.open} />
              <MetricCell label="High" field={bar.high} />
              <MetricCell label="Low" field={bar.low} />
              <MetricCell label="Close" field={bar.close} />
              <MetricCell label="Volume" field={bar.volume} />
            </li>
          ))}
        </ul>
      )}
    </SectionShell>
  );
}
