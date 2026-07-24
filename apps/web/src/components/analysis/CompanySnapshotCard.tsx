import { FieldRow } from "@/components/analysis/FieldRow";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import type { CompanySnapshotView } from "@/lib/analysis/types";
import { presentFieldLabel } from "@/lib/terminology";

export function CompanySnapshotCard({
  snapshot,
  onRefresh,
  onShare,
}: {
  snapshot: CompanySnapshotView;
  onRefresh: () => void;
  onShare: () => void;
}) {
  return (
    <Card>
      <CardHeader
        title="Company Snapshot"
        description="What is this business? Identity and quick facts from the API envelope."
        action={
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" onClick={onRefresh}>
              Refresh
            </Button>
            <Button variant="ghost" size="sm" onClick={onShare}>
              Share
            </Button>
            <Button variant="ghost" size="sm" disabled title="Export arrives later">
              Export
            </Button>
          </div>
        }
      />
      <CardBody className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <FieldRow label="Company name" field={snapshot.companyName} emphasize />
          <FieldRow label="Ticker" field={snapshot.ticker} emphasize />
          <FieldRow label="Industry" field={snapshot.industry} />
          <FieldRow label="Sector" field={snapshot.sector} />
          <FieldRow label="Exchange" field={snapshot.exchange} />
          <FieldRow label="Current market price" field={snapshot.currentMarketPrice} />
          <FieldRow label="Last updated" field={snapshot.lastUpdated} />
        </div>

        <div>
          <h3 className="mb-3 font-[family-name:var(--font-display)] text-lg">
            Quick facts
          </h3>
          <div className="grid gap-4 sm:grid-cols-3">
            <FieldRow label="Market cap" field={snapshot.marketCap} />
            <FieldRow label="52 week high" field={snapshot.week52High} />
            <FieldRow label="52 week low" field={snapshot.week52Low} />
          </div>
          {snapshot.marketCap.presence === "unavailable" ? (
            <div className="mt-3">
              <EmptyState
                title="Market facts not in envelope"
                description="Price and market-cap fields are Unavailable until market data is present in /analyze/company. DSP will not invent quotes."
              />
            </div>
          ) : null}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <FieldRow label="Research status" field={snapshot.researchStatus} />
          <FieldRow label="Research date" field={snapshot.researchDate} />
        </div>

        <p className="text-xs text-[var(--muted)]">
          Research Mode: conclusions use {presentFieldLabel("action")} language —
          never Buy / Sell / Hold tips.
        </p>
      </CardBody>
    </Card>
  );
}
