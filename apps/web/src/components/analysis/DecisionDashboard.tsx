import { FieldRow } from "@/components/analysis/FieldRow";
import type { DecisionDashboardView } from "@/lib/analysis/types";
import { presentFieldLabel } from "@/lib/terminology";

export function DecisionDashboard({
  dashboard,
}: {
  dashboard: DecisionDashboardView;
}) {
  return (
    <div className="space-y-6">
      {/* Section description */}
      <p className="text-sm text-[var(--muted)] leading-relaxed border-l-2 border-[var(--accent)]/40 pl-3">
        Summary anchor — what to believe, what is missing, what to investigate next.
      </p>

      {/* Primary recommendation — prominent */}
      <div className="border-b border-[var(--border)] pb-5">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">
          {presentFieldLabel("recommendation")}
        </p>
        <FieldRow
          label={presentFieldLabel("recommendation")}
          field={dashboard.researchConclusion}
          emphasize
        />
      </div>

      {/* Score grid */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-3">
          Dimension Scores
        </p>
        <div className="grid gap-0 divide-y divide-[var(--border)] border-t border-[var(--border)]">
          <ScoreRow label="Business quality" field={dashboard.businessScore} />
          <ScoreRow label="Financial strength" field={dashboard.financialScore} />
          <ScoreRow label="Valuation" field={dashboard.valuationScore} />
          <ScoreRow label="Risk" field={dashboard.riskScore} />
          <ScoreRow label="Management" field={dashboard.managementScore} />
          <ScoreRow label="Growth quality" field={dashboard.growthScore} />
        </div>
      </div>

      {/* Research signals */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-3">
          Research Signals
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <FieldRow label="Research confidence" field={dashboard.researchConfidence} />
          <FieldRow label="Top opportunity" field={dashboard.topOpportunity} />
          <FieldRow label="Biggest risk" field={dashboard.biggestRisk} />
          <FieldRow label="Next investigation" field={dashboard.nextInvestigation} emphasize />
        </div>
      </div>
    </div>
  );
}

function ScoreRow({
  label,
  field,
}: {
  label: string;
  field: { presence: string; value: unknown };
}) {
  const isAvail = field.presence === "available" && field.value != null;
  const displayValue = isAvail ? String(field.value) : "—";

  return (
    <div className="flex items-center justify-between py-2.5 px-0">
      <span className="text-xs text-[var(--muted)]">{label}</span>
      <span
        className={[
          "font-mono text-sm font-semibold tabular-nums",
          isAvail ? "text-[var(--accent)]" : "text-[var(--muted)]",
        ].join(" ")}
      >
        {displayValue}
      </span>
    </div>
  );
}
