import { EvidencePanel } from "@/components/analysis/EvidencePanel";
import { FieldRow } from "@/components/analysis/FieldRow";
import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ResearchConclusionView } from "@/lib/analysis/types";
import { presentFieldLabel } from "@/lib/terminology";
import type { ConfidenceLevel } from "@/lib/trust/labels";

export function ResearchConclusionCard({
  conclusion,
}: {
  conclusion: ResearchConclusionView;
}) {
  const confidenceValue = conclusion.researchConfidence.value;

  return (
    <Card>
      <CardHeader
        title={presentFieldLabel("recommendation")}
        description="DSP View investment assessment — Research Mode terminology"
        action={
          confidenceValue ? (
            <ConfidenceBadge level={String(confidenceValue) as ConfidenceLevel} />
          ) : null
        }
      />
      <CardBody className="space-y-4">
        <FieldRow
          label={presentFieldLabel("action")}
          field={conclusion.conclusion}
          emphasize
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <FieldRow
            label={presentFieldLabel("target_price")}
            field={conclusion.intrinsicValueRange}
          />
          <FieldRow label="Margin of safety" field={conclusion.marginOfSafety} />
          <FieldRow label="Overall research health" field={conclusion.researchHealth} />
          <FieldRow
            label="Research confidence"
            field={{
              ...conclusion.researchConfidence,
              value:
                conclusion.researchConfidence.value == null
                  ? null
                  : String(conclusion.researchConfidence.value),
            }}
          />
          <FieldRow label="Investment horizon" field={conclusion.investmentHorizon} />
          <FieldRow label="Suitable investor" field={conclusion.suitableInvestor} />
          <FieldRow label="Primary opportunity" field={conclusion.primaryOpportunity} />
          <FieldRow label="Primary risk" field={conclusion.primaryRisk} />
        </div>
        <EvidencePanel evidence={conclusion.evidence} />
      </CardBody>
    </Card>
  );
}
