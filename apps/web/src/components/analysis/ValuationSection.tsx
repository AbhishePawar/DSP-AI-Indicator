import { FieldRow } from "@/components/analysis/FieldRow";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import type { ValuationView } from "@/lib/analysis/types";
import { presentFieldLabel } from "@/lib/terminology";

export function ValuationSection({ valuation }: { valuation: ValuationView }) {
  return (
    <Card>
      <CardHeader
        title="Valuation"
        description={`${presentFieldLabel("target_price")} — never Official Target Price in Research Mode`}
      />
      <CardBody className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <FieldRow label="Current price" field={valuation.currentPrice} />
          <FieldRow
            label={presentFieldLabel("target_price")}
            field={valuation.intrinsicValueRange}
            emphasize
          />
          <FieldRow label="Margin of safety" field={valuation.marginOfSafety} />
        </div>
        <FieldRow label="Valuation summary" field={valuation.summary} />

        <div>
          <h3 className="mb-3 font-[family-name:var(--font-display)] text-lg">
            Scenario cards
          </h3>
          <div className="grid gap-4 md:grid-cols-3">
            <Scenario title="Bull" field={valuation.bull} />
            <Scenario title="Base" field={valuation.base} />
            <Scenario title="Bear" field={valuation.bear} />
          </div>
        </div>

        {valuation.intrinsicValueRange.presence === "unavailable" ? (
          <EmptyState
            title="Intrinsic range not in envelope"
            description="DSP will not invent valuation bands. When the valuation engine projects a range through the API, it appears here as Estimated Intrinsic Value Range."
          />
        ) : null}
      </CardBody>
    </Card>
  );
}

function Scenario({
  title,
  field,
}: {
  title: string;
  field: ValuationView["bull"];
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4">
      <p className="font-medium">{title}</p>
      <div className="mt-2">
        <FieldRow label="Scenario note" field={field} />
      </div>
    </div>
  );
}
