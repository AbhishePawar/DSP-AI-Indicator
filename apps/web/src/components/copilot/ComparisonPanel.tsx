"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type {
  CopilotCompanyContext,
  StageFieldSummary,
} from "@/lib/copilot/types";
import { formatPct, formatScore } from "@/lib/intelligence/mapResponse";

function FieldRow({
  label,
  left,
  right,
}: {
  label: string;
  left: string;
  right: string;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,8rem)_1fr_1fr] gap-2 border-b border-[var(--border)] py-2 text-sm last:border-b-0">
      <span className="text-[var(--muted)]">{label}</span>
      <span className="truncate">{left}</span>
      <span className="truncate">{right}</span>
    </div>
  );
}

function stageDisplay(stage: StageFieldSummary): string {
  if (!stage.available) return "—";
  return (
    stage.label ||
    stage.decision ||
    (stage.score != null ? formatScore(stage.score) : null) ||
    stage.status ||
    "—"
  );
}

export function ComparisonPanel({
  primary,
  secondary,
  available,
}: {
  primary: CopilotCompanyContext | null;
  secondary: CopilotCompanyContext | null;
  available: boolean;
}) {
  if (!available || !primary || !secondary) {
    return (
      <Card>
        <CardHeader
          title="Compare Companies"
          description="Requires two analysed companies in this browser session"
        />
        <CardBody>
          <p className="text-sm text-[var(--muted)]">
            Comparison is unavailable until a second company has been analysed
            in this session. Only overlapping present fields are compared —
            missing values are never estimated.
          </p>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Compare Companies"
        description={`${primary.ticker} vs ${secondary.ticker}`}
      />
      <CardBody>
        <div className="grid grid-cols-[minmax(0,8rem)_1fr_1fr] gap-2 text-xs uppercase tracking-wider text-[var(--muted)]">
          <span>Field</span>
          <span>{primary.ticker}</span>
          <span>{secondary.ticker}</span>
        </div>
        <FieldRow
          label="Recommendation"
          left={primary.recommendation || "—"}
          right={secondary.recommendation || "—"}
        />
        <FieldRow
          label="MoS"
          left={formatPct(primary.marginOfSafety)}
          right={formatPct(secondary.marginOfSafety)}
        />
        <FieldRow
          label="Moat"
          left={stageDisplay(primary.economicMoat)}
          right={stageDisplay(secondary.economicMoat)}
        />
        <FieldRow
          label="Management"
          left={stageDisplay(primary.managementQuality)}
          right={stageDisplay(secondary.managementQuality)}
        />
        <FieldRow
          label="Financial"
          left={stageDisplay(primary.financialStrength)}
          right={stageDisplay(secondary.financialStrength)}
        />
        <FieldRow
          label="Earnings"
          left={stageDisplay(primary.earningsQuality)}
          right={stageDisplay(secondary.earningsQuality)}
        />
        <FieldRow
          label="Growth"
          left={stageDisplay(primary.growthQuality)}
          right={stageDisplay(secondary.growthQuality)}
        />
        <FieldRow
          label="Committee"
          left={primary.committeeDecision || "—"}
          right={secondary.committeeDecision || "—"}
        />
      </CardBody>
    </Card>
  );
}
