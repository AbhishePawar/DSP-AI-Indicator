import { ExplainableScore } from "@/components/institutional-dashboard/ExplainableScore";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import type { ScoreCard } from "@/lib/institutional-dashboard/types";

export function ExplainabilityPanel({ scores }: { scores: ScoreCard[] }) {
  return (
    <SectionShell
      id="rs-009-explainability"
      title="Explainability"
      description="RS-009 — every score exposes formula, inputs, weights, engines, reasoning"
    >
      <div className="grid gap-3 lg:grid-cols-2">
        {scores.map((score) => (
          <ExplainableScore key={`explain-${score.id}`} score={score} />
        ))}
      </div>
    </SectionShell>
  );
}
