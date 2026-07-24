import { Badge } from "@/components/ui/Badge";
import type { CoverageBucket, CoverageStatus } from "@/lib/analysis/types";

const TONE: Record<CoverageStatus, "success" | "warning" | "neutral"> = {
  available: "success",
  pending: "warning",
  unavailable: "neutral",
};

export function CoverageProgressBar({
  percent,
  label = "Research coverage",
}: {
  percent: number;
  label?: string;
}) {
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <div className="space-y-2" aria-label={`${label}: ${clamped} percent`}>
      <div className="flex justify-between text-xs text-[var(--muted)]">
        <span>{label}</span>
        <span className="font-medium text-[var(--fg)]">{clamped}%</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-[var(--surface-2)]"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-[var(--accent)] transition-[width] duration-300 motion-reduce:transition-none"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

export function CoverageBucketRow({ bucket }: { bucket: CoverageBucket }) {
  return (
    <div className="flex items-center justify-between gap-2 text-sm">
      <span>{bucket.label}</span>
      <div className="flex items-center gap-2">
        <span className="text-xs text-[var(--muted)]">
          {bucket.availableCount}/{bucket.totalCount}
        </span>
        <Badge tone={TONE[bucket.status]}>{bucket.status}</Badge>
      </div>
    </div>
  );
}
