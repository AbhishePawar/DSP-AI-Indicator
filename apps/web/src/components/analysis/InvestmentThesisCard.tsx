import { FieldRow } from "@/components/analysis/FieldRow";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { DisplayField, InvestmentThesisView } from "@/lib/analysis/types";

export function InvestmentThesisCard({ thesis }: { thesis: InvestmentThesisView }) {
  return (
    <Card>
      <CardHeader
        title="Investment Thesis"
        description="Why this company deserves attention — structured, evidence-aware"
      />
      <CardBody className="space-y-5">
        <FieldRow label="Why this company deserves attention" field={thesis.whyAttention} />
        <ListField label="Key strengths" field={thesis.keyStrengths} />
        <ListField label="Key concerns" field={thesis.keyConcerns} />
        <FieldRow label="Long-term thesis" field={thesis.longTermThesis} />
        <ListField label="Things to monitor" field={thesis.thingsToMonitor} />
      </CardBody>
    </Card>
  );
}

function ListField({
  label,
  field,
}: {
  label: string;
  field: DisplayField<string[]>;
}) {
  const items =
    field.presence === "available" && Array.isArray(field.value) ? field.value : [];
  return (
    <div className="space-y-2">
      <FieldRow
        label={label}
        field={{
          ...field,
          value: items.length ? items.join("; ") : null,
        }}
      />
      {items.length > 1 ? (
        <ul className="list-disc pl-5 text-sm text-[var(--muted)]">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
