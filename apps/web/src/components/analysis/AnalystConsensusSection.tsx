import { FieldRow } from "@/components/analysis/FieldRow";
import { SmartHeader } from "@/components/analysis/MarketIntelligenceSection";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import type { AnalystConsensusView } from "@/lib/analysis/types";

export function ConsensusCard({
  consensus,
}: {
  consensus: AnalystConsensusView;
}) {
  return (
    <Card>
      <CardHeader
        title="Consensus summary"
        description="Research Mode language only — never Buy / Sell / Hold tips"
      />
      <CardBody className="grid gap-4 sm:grid-cols-2">
        <FieldRow label="Consensus summary" field={consensus.summary} emphasize />
        <FieldRow label="Agreement level" field={consensus.agreementLevel} />
        <FieldRow label="Coverage" field={consensus.coverage} />
        <FieldRow label="Confidence" field={consensus.confidence} />
        <FieldRow label="Analyst coverage quality" field={consensus.coverageQuality} />
      </CardBody>
    </Card>
  );
}

export function ConsensusTrendCard({
  consensus,
}: {
  consensus: AnalystConsensusView;
}) {
  return (
    <Card>
      <CardHeader title="Consensus trend & scenarios" />
      <CardBody className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <FieldRow label="Consensus trend" field={consensus.trend} />
        <FieldRow label="Historical consensus trend" field={consensus.historicalTrend} />
        <FieldRow label="Consensus changes" field={consensus.consensusChanges} />
        <FieldRow label="Bull case" field={consensus.bullCase} />
        <FieldRow label="Base case" field={consensus.baseCase} />
        <FieldRow label="Bear case" field={consensus.bearCase} />
      </CardBody>
    </Card>
  );
}

export function AnalystConsensusSection({
  consensus,
}: {
  consensus: AnalystConsensusView;
}) {
  return (
    <div className="space-y-4">
      <SmartHeader
        title="Analyst Consensus"
        changed="No Street consensus payload in the current API envelope."
        monitor="When providers connect, compare coverage quality and scenario dispersion — still not tips."
      />
      {!consensus.available ? (
        <EmptyState
          title="Analyst consensus unavailable"
          description="Why: external consensus not in /analyze/company. Expected: future ConsensusProviderPort adapters. DSP will not fabricate analyst opinions or Target Price language."
        />
      ) : null}
      <ConsensusCard consensus={consensus} />
      <ConsensusTrendCard consensus={consensus} />
    </div>
  );
}
