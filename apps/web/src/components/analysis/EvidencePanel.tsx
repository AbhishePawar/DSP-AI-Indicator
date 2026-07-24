import type { ReactNode } from "react";

import { TraceLink } from "@/components/analysis/TraceLink";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { EvidenceView } from "@/lib/analysis/types";

export function EvidencePanel({
  evidence,
  compact = false,
}: {
  evidence: EvidenceView;
  compact?: boolean;
}) {
  const supporting =
    evidence.supportingEvidence?.length > 0
      ? evidence.supportingEvidence
      : evidence.supportingMetrics;

  return (
    <Card className={compact ? "mt-2 border-dashed" : "mt-4 border-dashed"}>
      <CardHeader
        title="Evidence"
        description={
          compact
            ? "Traceability"
            : "Traceability — supporting and contradicting evidence kept separate"
        }
      />
      <CardBody className={`space-y-3 text-sm ${compact ? "py-3" : ""}`}>
        <Block label="Primary evidence">
          <ListOrEmpty items={evidence.primaryEvidence} empty="None listed" />
        </Block>
        <Block label="Supporting evidence">
          <ListOrEmpty items={supporting} empty="None listed" />
        </Block>
        <Block label="Contradicting evidence">
          <ListOrEmpty
            items={evidence.contradictingEvidence ?? []}
            empty="None listed"
          />
        </Block>
        <Block label="Supporting metrics">
          <ListOrEmpty items={evidence.supportingMetrics} empty="None listed" />
        </Block>
        <Block label="Source">{evidence.source}</Block>
        <Block label="Methodology">{evidence.methodology}</Block>
        <Block label="Confidence">
          {evidence.confidence ?? "Unavailable"}
        </Block>
        <Block label="AI reasoning">
          {evidence.aiReasoning ?? (
            <span className="text-[var(--muted)]">Unavailable</span>
          )}
        </Block>
        <Block label="AI explanation">
          {evidence.aiExplanation ?? (
            <span className="text-[var(--muted)]">Unavailable</span>
          )}
        </Block>
        <Block label="Limitations">
          <ListOrEmpty
            items={evidence.limitations}
            empty="No limitations listed"
          />
        </Block>
        <Block label="Last updated">
          {evidence.lastUpdated ?? "Unavailable"}
        </Block>
        <p className="text-xs text-[var(--muted)]">
          Explore: <TraceLink href="#evidence_explorer">Evidence Explorer</TraceLink>
          {" · "}
          <TraceLink href="#decision_trace">Decision Trace</TraceLink>
          {" · "}
          <TraceLink href="#methodology_panel">Methodology</TraceLink>
        </p>
      </CardBody>
    </Card>
  );
}

function ListOrEmpty({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) {
    return <span className="text-[var(--muted)]">{empty}</span>;
  }
  return (
    <ul className="list-disc pl-5">
      {items.map((m) => (
        <li key={m}>{m}</li>
      ))}
    </ul>
  );
}

function Block({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      <div className="mt-1">{children}</div>
    </div>
  );
}
