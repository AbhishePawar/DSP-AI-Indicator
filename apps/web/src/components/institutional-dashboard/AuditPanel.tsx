import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import type { AuditView } from "@/lib/institutional-dashboard/types";

export function AuditPanel({ view }: { view: AuditView }) {
  return (
    <SectionShell
      id="rs-010-audit"
      title="Audit & Provenance"
      description="RS-010 — complete reproducibility envelope"
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCell label="Report ID" field={view.reportId} />
        <MetricCell label="Audit reference" field={view.auditReference} />
        <MetricCell
          label="Generation timestamp"
          field={view.generationTimestamp}
        />
        <MetricCell
          label="Market data timestamp"
          field={view.marketDataTimestamp}
        />
        <MetricCell
          label="Financial statement period"
          field={view.financialStatementPeriod}
        />
        <MetricCell label="Engine version" field={view.engineVersion} />
        <MetricCell label="Research version" field={view.researchVersion} />
        <MetricCell label="Rules version" field={view.rulesVersion} />
        <MetricCell label="Data sources" field={view.dataSources} />
        <MetricCell
          label="Calculation metadata"
          field={view.calculationMetadata}
        />
        <MetricCell label="Correlation ID" field={view.correlationId} />
        <MetricCell label="Package versions" field={view.packageVersions} />
      </div>
    </SectionShell>
  );
}
