import { FieldRow } from "@/components/analysis/FieldRow";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import type { MarketIntelligenceView } from "@/lib/analysis/types";

export function MarketSentimentCard({
  market,
}: {
  market: MarketIntelligenceView;
}) {
  return (
    <Card>
      <CardHeader
        title="Market sentiment snapshot"
        description="External opinion summary — never replaces DSP Research"
      />
      <CardBody className="grid gap-4 sm:grid-cols-2">
        <FieldRow label="Overall market sentiment" field={market.overallSentiment} />
        <FieldRow label="Coverage count" field={market.coverageCount} />
        <FieldRow label="Consensus strength" field={market.consensusStrength} />
        <FieldRow label="Market confidence" field={market.marketConfidence} />
        <FieldRow label="Research coverage note" field={market.researchCoverageNote} />
        <FieldRow label="Last updated" field={market.lastUpdated} />
        <FieldRow label="Data availability" field={market.dataAvailability} />
      </CardBody>
    </Card>
  );
}

export function MarketIntelligenceSection({
  market,
}: {
  market: MarketIntelligenceView;
}) {
  return (
    <div className="space-y-4">
      <SmartHeader
        title="Market Intelligence"
        changed="External market feeds are not connected in this RC — DSP Research remains primary."
        monitor="Watch for provider enablement; until then treat Street fields as Unavailable."
      />
      {market.available ? (
        <MarketSentimentCard market={market} />
      ) : (
        <>
          <EmptyState
            title="Market intelligence unavailable"
            description="Why: consensus providers are not integrated. Expected: future provider adapters via compliance ports. How DSP handles this: show Unavailable labels and keep DSP Research as source of truth — never invent Street opinion."
          />
          <MarketSentimentCard market={market} />
        </>
      )}
    </div>
  );
}

function SmartHeader({
  title,
  changed,
  monitor,
}: {
  title: string;
  changed: string;
  monitor: string;
}) {
  return (
    <div>
      <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-tight">
        {title}
      </h2>
      <p className="mt-2 rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm">
        <span className="font-medium">What changed? — </span>
        {changed}
      </p>
      <p className="mt-2 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm">
        <span className="font-medium">What should investors monitor next? — </span>
        {monitor}
      </p>
    </div>
  );
}

export { SmartHeader };
