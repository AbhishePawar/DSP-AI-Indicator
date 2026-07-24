import { FieldRow } from "@/components/analysis/FieldRow";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { DecisionDashboardView } from "@/lib/analysis/types";
import { presentFieldLabel } from "@/lib/terminology";

export function DecisionDashboard({
  dashboard,
}: {
  dashboard: DecisionDashboardView;
}) {
  return (
    <Card className="border-[var(--accent)]/40">
      <CardHeader
        title="Decision Dashboard"
        description="Summary anchor — what to believe, what is missing, what to investigate next"
      />
      <CardBody className="space-y-5">
        <FieldRow
          label={presentFieldLabel("recommendation")}
          field={dashboard.researchConclusion}
          emphasize
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <FieldRow label="Business score" field={dashboard.businessScore} />
          <FieldRow label="Financial score" field={dashboard.financialScore} />
          <FieldRow label="Valuation score" field={dashboard.valuationScore} />
          <FieldRow label="Risk score" field={dashboard.riskScore} />
          <FieldRow label="Management score" field={dashboard.managementScore} />
          <FieldRow label="Growth score" field={dashboard.growthScore} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <FieldRow label="Research confidence" field={dashboard.researchConfidence} />
          <FieldRow label="Top opportunity" field={dashboard.topOpportunity} />
          <FieldRow label="Biggest risk" field={dashboard.biggestRisk} />
          <FieldRow label="Next investigation" field={dashboard.nextInvestigation} emphasize />
        </div>
      </CardBody>
    </Card>
  );
}
