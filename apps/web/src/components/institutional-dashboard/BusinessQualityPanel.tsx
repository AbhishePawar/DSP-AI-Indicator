import { ExplainableScore } from "@/components/institutional-dashboard/ExplainableScore";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import type { BusinessQualityView } from "@/lib/institutional-dashboard/types";

export function BusinessQualityPanel({ view }: { view: BusinessQualityView }) {
  const cards = [
    view.overall,
    view.moat,
    view.management,
    view.governance,
    view.capitalAllocation,
    view.financialStrength,
    view.predictability,
    view.competitivePosition,
    view.longTermOutlook,
  ];

  return (
    <SectionShell
      id="rs-006-quality"
      title="Business Quality"
      description="RS-006 — each score expandable for explainability"
    >
      <div className="grid gap-3 lg:grid-cols-2">
        {cards.map((card) => (
          <ExplainableScore key={card.id} score={card} />
        ))}
      </div>
    </SectionShell>
  );
}
