import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import type { ValuationView } from "@/lib/institutional-dashboard/types";

export function ValuationPanel({ view }: { view: ValuationView }) {
  return (
    <SectionShell
      id="rs-004-valuation"
      title="Valuation"
      description="RS-004 — no valuation without authenticated / submitted inputs"
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCell
          label="Intrinsic value"
          field={view.intrinsicValue}
          emphasize
        />
        <MetricCell label="Fair value" field={view.fairValue} />
        <MetricCell label="Fair value range" field={view.fairValueRange} />
        <MetricCell
          label="Method contributions"
          field={view.methodContributions}
        />
        <MetricCell label="Sensitivity" field={view.sensitivity} />
        <MetricCell label="Assumptions" field={view.assumptions} />
        <MetricCell label="Engine version" field={view.engineVersion} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {view.methods.map((method) => (
          <div
            key={method.id}
            className="rounded-md border border-[var(--border)] p-3"
          >
            <MetricCell label={method.title} field={method.value} />
          </div>
        ))}
      </div>
    </SectionShell>
  );
}
