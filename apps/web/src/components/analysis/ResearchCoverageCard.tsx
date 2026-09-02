import {
  CoverageBucketRow,
  CoverageProgressBar,
} from "@/components/analysis/CoverageProgressBar";
import type { ResearchCoverageView } from "@/lib/analysis/types";

/** Measures DSP research completeness — NOT company quality. */
export function ResearchCoverageCard({
  coverage,
}: {
  coverage: ResearchCoverageView;
}) {
  return (
    <section className="space-y-4">
      <div className="border-b border-[var(--border)] pb-3">
        <h3 className="font-[family-name:var(--font-display)] text-base tracking-tight text-[var(--fg)]">
          Research Coverage
        </h3>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          How complete is DSP&apos;s current research package — not a score of the business
        </p>
      </div>
      <div className="space-y-4 text-sm">
        <CoverageProgressBar percent={coverage.coveragePercent} />
        <div className="divide-y divide-[var(--border)]">
          <StatRow label="Evidence strength" value={coverage.evidenceStrength} />
          <StatRow label="Available metrics" value={String(coverage.availableMetrics)} />
          <StatRow label="Unavailable metrics" value={String(coverage.unavailableMetrics)} />
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
            Coverage breakdown
          </p>
          <div className="space-y-2">
            {coverage.breakdown.map((b) => (
              <CoverageBucketRow key={b.id} bucket={b} />
            ))}
          </div>
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
            Future sections
          </p>
          <div className="space-y-2">
            {coverage.futureSections.map((b) => (
              <CoverageBucketRow key={b.id} bucket={b} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2 first:pt-0 last:pb-0">
      <p className="text-xs text-[var(--muted)] shrink-0">{label}</p>
      <p className="text-sm font-medium text-[var(--fg)] tabular-nums">{value}</p>
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
    <section className="space-y-4">
      <div className="border-b border-[var(--border)] pb-3">
        <h3 className="font-[family-name:var(--font-display)] text-base tracking-tight text-[var(--fg)]">
          Research Freshness
        </h3>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          When this analysis was produced and which methodology presentation layer applies
        </p>
      </div>
      <div className="divide-y divide-[var(--border)] text-sm">
        <Row label="Research date" value={freshness.researchDate ?? "Unavailable"} />
        <Row label="Last updated" value={freshness.lastUpdated ?? "Unavailable"} />
        <Row label="Data currency" value={freshness.dataCurrency} />
        <Row label="Analysis version" value={freshness.analysisVersion} />
        <Row label="Methodology version" value={freshness.methodologyVersion} />
        <Row label="Research mode" value={freshness.researchMode} />
      </div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2 first:pt-0 last:pb-0">
      <p className="text-xs text-[var(--muted)] shrink-0">{label}</p>
      <p className="text-sm font-medium text-[var(--fg)] text-right">{value}</p>
    </div>
  );
}
