import { ExplainableScore } from "@/components/institutional-dashboard/ExplainableScore";
import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import type { RiskView } from "@/lib/institutional-dashboard/types";

export function RiskPanel({ view }: { view: RiskView }) {
  const cards = [
    view.business,
    view.financial,
    view.industry,
    view.macro,
    view.regulatory,
    view.execution,
  ];

  return (
    <SectionShell
      id="rs-007-risk"
      title="Risk Analysis"
      description="RS-007 — mandatory risk coverage"
    >
      <MetricCell label="Risk rating" field={view.riskRating} emphasize />
      <MetricCell label="Key assumptions" field={view.keyAssumptions} />
      <div className="grid gap-3 lg:grid-cols-2">
        {cards.map((card) => (
          <ExplainableScore key={card.id} score={card} />
        ))}
      </div>
    </SectionShell>
  );
}
