import { EvidencePanel } from "@/components/analysis/EvidencePanel";
import { FieldRow } from "@/components/analysis/FieldRow";
import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
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
    <div className="space-y-6">
      {/* Confidence badge — right-aligned header */}
      {confidenceValue ? (
        <div className="flex justify-end">
          <ConfidenceBadge level={String(confidenceValue) as ConfidenceLevel} />
        </div>
      ) : null}

      {/* Primary conclusion — prominent */}
      <div className="border-b border-[var(--border)] pb-5">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">
          {presentFieldLabel("action")}
        </p>
        <FieldRow
          label={presentFieldLabel("action")}
          field={conclusion.conclusion}
          emphasize
        />
      </div>

      {/* Valuation metrics */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-3">
          Valuation
        </p>
        <div className="grid gap-0 divide-y divide-[var(--border)] border-t border-b border-[var(--border)]">
          <ConclusionRow label={presentFieldLabel("target_price")} field={conclusion.intrinsicValueRange} />
          <ConclusionRow label="Margin of safety" field={conclusion.marginOfSafety} />
          <ConclusionRow label="Overall research health" field={conclusion.researchHealth} />
          <ConclusionRow
            label="Research confidence"
            field={{
              ...conclusion.researchConfidence,
              value:
                conclusion.researchConfidence.value == null
                  ? null
                  : String(conclusion.researchConfidence.value),
            }}
          />
        </div>
      </div>

      {/* Context */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-3">
          Context
        </p>
        <div className="grid gap-0 divide-y divide-[var(--border)] border-t border-b border-[var(--border)]">
          <ConclusionRow label="Investment horizon" field={conclusion.investmentHorizon} />
          <ConclusionRow label="Suitable investor" field={conclusion.suitableInvestor} />
          <ConclusionRow label="Primary opportunity" field={conclusion.primaryOpportunity} />
          <ConclusionRow label="Primary risk" field={conclusion.primaryRisk} />
        </div>
      </div>

      <EvidencePanel evidence={conclusion.evidence} />
    </div>
  );
}

function ConclusionRow({
  label,
  field,
}: {
  label: string;
  field: { presence: string; value: unknown };
}) {
  const isAvail = field.presence === "available" && field.value != null;
  const displayValue = isAvail ? String(field.value) : "—";

  return (
    <div className="flex items-start justify-between gap-4 py-2.5">
      <span className="text-xs text-[var(--muted)] shrink-0">{label}</span>
      <span
        className={[
          "text-right text-sm font-mono font-semibold leading-snug",
          isAvail ? "text-[var(--accent)]" : "text-[var(--muted)]",
        ].join(" ")}
      >
        {displayValue}
      </span>
    </div>
  );
}
