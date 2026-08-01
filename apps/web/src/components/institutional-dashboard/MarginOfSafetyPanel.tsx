import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import type { MarginOfSafetyView } from "@/lib/institutional-dashboard/types";

export function MarginOfSafetyPanel({ view }: { view: MarginOfSafetyView }) {
  return (
    <SectionShell
      id="rs-005-mos"
      title="Margin of Safety"
      description="RS-005 — most prominent valuation component; never hidden"
      prominent
    >
      <ol className="mx-auto flex max-w-xl flex-col items-stretch gap-0">
        {(
          [
            ["Current market price", view.currentPrice],
            ["Intrinsic value", view.intrinsicValue],
            ["Margin of safety", view.marginOfSafety],
            ["Upside potential", view.upsidePotential],
            ["Downside risk", view.downsideRisk],
            ["Risk / reward", view.riskReward],
          ] as const
        ).map(([label, field], index, arr) => (
          <li key={label} className="list-none">
            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-4 text-center">
              <MetricCell label={label} field={field} emphasize />
            </div>
            {index < arr.length - 1 ? (
              <p
                className="py-1 text-center text-lg text-[var(--muted)]"
                aria-hidden
              >
                ↓
              </p>
            ) : null}
          </li>
        ))}
      </ol>
      <div className="mt-4">
        <MetricCell label="Valuation status" field={view.valuationStatus} />
      </div>
    </SectionShell>
  );
}
