import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import type { ScenarioView } from "@/lib/institutional-dashboard/types";

export function ScenarioPanel({ view }: { view: ScenarioView }) {
  const cases = [view.bull, view.base, view.bear];

  return (
    <SectionShell
      id="rs-008-scenarios"
      title="Scenario Analysis"
      description="RS-008 — bull / base / bear"
    >
      <div className="grid gap-4 lg:grid-cols-3">
        {cases.map((c) => (
          <div
            key={c.id}
            className="rounded-md border border-[var(--border)] p-3 space-y-3"
          >
            <h3 className="font-[family-name:var(--font-display)] text-base">
              {c.title}
            </h3>
            <MetricCell label="Narrative" field={c.narrative} />
            <MetricCell label="Expected CAGR" field={c.cagr} />
            <MetricCell label="Probability" field={c.probability} />
          </div>
        ))}
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCell label="Expected CAGR (overall)" field={view.expectedCagr} />
        <MetricCell label="Sensitivity" field={view.sensitivity} />
        <MetricCell label="Key drivers" field={view.keyDrivers} />
      </div>
    </SectionShell>
  );
}
