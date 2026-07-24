import { AgreementBadge } from "@/components/analysis/AgreementBadge";
import { FieldRow } from "@/components/analysis/FieldRow";
import { SmartHeader } from "@/components/analysis/MarketIntelligenceSection";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { StreetComparisonRow } from "@/lib/analysis/types";

export function StreetComparisonCard({ row }: { row: StreetComparisonRow }) {
  return (
    <Card>
      <CardHeader
        title={row.dimension}
        action={<AgreementBadge level={row.agreement} />}
      />
      <CardBody className="space-y-4 text-sm">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-md border border-[var(--accent)]/30 bg-[var(--accent-soft)]/30 p-3">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--accent)]">
              DSP Research
            </p>
            <div className="mt-2">
              <FieldRow label="DSP" field={row.dspResearch} />
            </div>
          </div>
          <div className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] p-3">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Market Consensus
            </p>
            <div className="mt-2">
              <FieldRow label="Street" field={row.marketConsensus} />
            </div>
          </div>
        </div>
        <p>
          <span className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Reason for difference
          </span>
          <br />
          {row.reasonForDifference}
        </p>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Supporting evidence
          </p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {row.supportingEvidence.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </div>
        <p>
          <span className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Investor interpretation
          </span>
          <br />
          {row.investorInterpretation}
        </p>
      </CardBody>
    </Card>
  );
}

export function DspVsStreetSection({ rows }: { rows: StreetComparisonRow[] }) {
  return (
    <div className="space-y-4">
      <SmartHeader
        title="DSP vs Street"
        changed="Signature comparison is ready: DSP Research is shown; Street remains Unavailable until providers connect."
        monitor="Do not infer agreement from missing Street data. Revisit when External Consensus appears."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        {rows.map((row) => (
          <StreetComparisonCard key={row.id} row={row} />
        ))}
      </div>
    </div>
  );
}
