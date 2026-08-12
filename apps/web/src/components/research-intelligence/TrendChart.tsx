"use client";

/**
 * Lightweight SVG trend chart — code-split, no heavy chart library.
 * CV-001: empty series → Data unavailable.
 */

import { DATA_UNAVAILABLE, displayMetric } from "@/lib/research-intelligence";

export function TrendChart({
  trends,
}: {
  trends: Record<string, unknown>[];
}) {
  const points = trends
    .map((t) => ({
      period: String(t.period ?? ""),
      accuracy:
        typeof t.accuracy === "number" && Number.isFinite(t.accuracy)
          ? t.accuracy
          : null,
      sample: typeof t.sample_size === "number" ? t.sample_size : 0,
    }))
    .filter((p) => p.period);

  if (points.length === 0 || points.every((p) => p.accuracy === null)) {
    return (
      <p className="text-sm text-[var(--muted)]" role="status">
        {DATA_UNAVAILABLE}
      </p>
    );
  }

  const width = 480;
  const height = 160;
  const pad = 24;
  const usable = points.filter((p) => p.accuracy !== null) as {
    period: string;
    accuracy: number;
    sample: number;
  }[];
  const xs = usable.map((_, i) => pad + (i * (width - pad * 2)) / Math.max(usable.length - 1, 1));
  const ys = usable.map(
    (p) => height - pad - p.accuracy * (height - pad * 2),
  );
  const path = usable
    .map((_, i) => `${i === 0 ? "M" : "L"} ${xs[i]} ${ys[i]}`)
    .join(" ");

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-40 w-full max-w-xl text-[var(--accent)] motion-reduce:transition-none"
        role="img"
        aria-label="Research accuracy trend"
      >
        <line
          x1={pad}
          y1={height - pad}
          x2={width - pad}
          y2={height - pad}
          stroke="var(--border)"
        />
        <path d={path} fill="none" stroke="currentColor" strokeWidth={2} />
        {usable.map((p, i) => (
          <circle key={p.period} cx={xs[i]} cy={ys[i]} r={3} fill="currentColor">
            <title>
              {p.period}: {displayMetric(p.accuracy)} (n={p.sample})
            </title>
          </circle>
        ))}
      </svg>
      <ul className="mt-2 flex flex-wrap gap-3 text-xs text-[var(--muted)]">
        {usable.map((p) => (
          <li key={p.period}>
            {p.period}: {displayMetric(p.accuracy)}
          </li>
        ))}
      </ul>
    </div>
  );
}
