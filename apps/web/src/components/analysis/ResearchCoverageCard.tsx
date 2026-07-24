import {
  CoverageBucketRow,
  CoverageProgressBar,
} from "@/components/analysis/CoverageProgressBar";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ResearchCoverageView } from "@/lib/analysis/types";

/** Measures DSP research completeness — NOT company quality. */
export function ResearchCoverageCard({
  coverage,
}: {
  coverage: ResearchCoverageView;
}) {
  return (
    <Card>
      <CardHeader
        title="Research Coverage"
        description="How complete is DSP’s current research package — not a score of the business"
      />
      <CardBody className="space-y-4 text-sm">
        <CoverageProgressBar percent={coverage.coveragePercent} />
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Evidence strength" value={coverage.evidenceStrength} />
          <Stat label="Available metrics" value={String(coverage.availableMetrics)} />
          <Stat
            label="Unavailable metrics"
            value={String(coverage.unavailableMetrics)}
          />
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Coverage breakdown
          </p>
          <div className="space-y-2">
            {coverage.breakdown.map((b) => (
              <CoverageBucketRow key={b.id} bucket={b} />
            ))}
          </div>
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Future sections
          </p>
          <div className="space-y-2">
            {coverage.futureSections.map((b) => (
              <CoverageBucketRow key={b.id} bucket={b} />
            ))}
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
      <p className="text-xs text-[var(--muted)]">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}

/** Alias per sprint naming */
export function FreshnessCard(props: {
  freshness: import("@/lib/analysis/types").ResearchFreshnessView;
}) {
  return <ResearchFreshnessCard freshness={props.freshness} />;
}

export function ResearchFreshnessCard({
  freshness,
}: {
  freshness: import("@/lib/analysis/types").ResearchFreshnessView;
}) {
  return (
    <Card>
      <CardHeader
        title="Research Freshness"
        description="When this analysis was produced and which methodology presentation layer applies"
      />
      <CardBody className="grid gap-3 text-sm sm:grid-cols-2">
        <Row label="Research date" value={freshness.researchDate ?? "Unavailable"} />
        <Row label="Last updated" value={freshness.lastUpdated ?? "Unavailable"} />
        <Row label="Data currency" value={freshness.dataCurrency} />
        <Row label="Analysis version" value={freshness.analysisVersion} />
        <Row label="Methodology version" value={freshness.methodologyVersion} />
        <Row label="Research mode" value={freshness.researchMode} />
      </CardBody>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-0.5 font-medium">{value}</p>
    </div>
  );
}
