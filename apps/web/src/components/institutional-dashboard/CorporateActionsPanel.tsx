import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import { Alert } from "@/components/ds";
import type { CorporateActionsView } from "@/lib/institutional-dashboard/types";
import { DATA_UNAVAILABLE } from "@/lib/institutional-dashboard/types";

export function CorporateActionsPanel({ view }: { view: CorporateActionsView }) {
  return (
    <SectionShell
      id="corporate-actions"
      title="Corporate Actions"
      description="Authenticated corporate actions only — retrieval, no adjusted prices"
    >
      {!view.hasAuthenticatedCorporateActions ? (
        <Alert variant="warning">
          Authenticated corporate-actions feed is not attached. Events show{" "}
          {DATA_UNAVAILABLE} — no fabricated splits, dividends, or buybacks.
        </Alert>
      ) : null}
      <div className="mb-4">
        <MetricCell label="Data source" field={view.source} />
      </div>
      {view.events.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">{DATA_UNAVAILABLE}</p>
      ) : (
        <ul className="space-y-4">
          {view.events.map((event, index) => (
            <li
              key={`${event.actionType.display}-${index}`}
              className="grid gap-3 border-t border-[var(--border)] pt-4 sm:grid-cols-2 lg:grid-cols-4"
            >
              <MetricCell label="Action type" field={event.actionType} />
              <MetricCell label="Effective date" field={event.effectiveDate} />
              <MetricCell label="Ex-date" field={event.exDate} />
              <MetricCell label="Record date" field={event.recordDate} />
              <MetricCell label="Payment date" field={event.paymentDate} />
              <MetricCell label="Amount" field={event.amount} />
              <MetricCell label="Ratio" field={event.ratio} />
              <MetricCell label="Description" field={event.description} />
            </li>
          ))}
        </ul>
      )}
    </SectionShell>
  );
}
