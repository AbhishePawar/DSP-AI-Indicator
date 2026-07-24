import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import type { RiskInsightView } from "@/lib/analysis/types";

export function RiskCard({ risk }: { risk: RiskInsightView }) {
  return (
    <Card>
      <CardHeader
        title={risk.title}
        action={<Badge tone="warning">{risk.severity}</Badge>}
      />
      <CardBody className="space-y-3 text-sm">
        <div className="flex flex-wrap gap-2">
          <ValueCategoryBadge category={risk.category} />
          <SourceBadge source={risk.source} />
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Severity" value={risk.severity} />
          <Stat label="Probability" value={risk.probability} />
          <Stat label="Impact" value={risk.impact} />
        </div>
        <Block label="Reason">{risk.reason}</Block>
        <Block label="Mitigation">{risk.mitigation}</Block>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Investor watchpoints
          </p>
          <ul className="mt-1 list-disc pl-5">
            {risk.investorWatchpoints.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
        {risk.supportingEvidence.length ? (
          <ul className="list-disc pl-5 text-[var(--muted)]">
            {risk.supportingEvidence.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        ) : (
          <EmptyState
            title="Supporting evidence unavailable"
            description="Severity/probability/impact stay Unavailable until risk artifacts appear in the API envelope. DSP will not invent risk scores."
          />
        )}
      </CardBody>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-2">
      <p className="text-xs text-[var(--muted)]">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}

function Block({ label, children }: { label: string; children: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      <p className="mt-1">{children}</p>
    </div>
  );
}
