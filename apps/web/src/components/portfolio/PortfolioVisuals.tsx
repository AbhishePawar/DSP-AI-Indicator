"use client";

import { memo } from "react";

import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type {
  AllocationSlice,
  TrustedMetric,
} from "@/lib/portfolio/portfolioWorkspace";

export function TrustedMetricBlock({ metric }: { metric: TrustedMetric }) {
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          {metric.label}
        </p>
        <ConfidenceBadge level={metric.confidence} />
      </div>
      <p className="mt-1 text-lg font-medium">
        {metric.presence === "available" ? metric.value : "Unavailable"}
      </p>
      <p className="mt-2 text-xs text-[var(--muted)]">
        Evidence: {metric.evidence}
        <br />
        Methodology: {metric.methodology}
        <br />
        Timestamp: {metric.timestamp ?? "Unavailable"}
      </p>
    </div>
  );
}

export const PortfolioEmptyState = memo(function PortfolioEmptyState() {
  return (
    <Card>
      <CardHeader title="No portfolio data" />
      <CardBody className="text-sm text-[var(--muted)]">
        Portfolio Intelligence is presentation-only. Load the demo session or connect
        portfolio APIs later (broker sync is out of scope).
      </CardBody>
    </Card>
  );
});

export function AllocationDonut({
  slices,
  title,
}: {
  slices: AllocationSlice[];
  title: string;
}) {
  const total = slices.reduce((s, x) => s + x.weight, 0) || 1;
  let acc = 0;
  const stops = slices.map((sl, i) => {
    const start = acc;
    acc += (sl.weight / total) * 100;
    const hue = (i * 47) % 360;
    return `${`hsl(${hue} 35% 45%)`} ${start}% ${acc}%`;
  });

  return (
    <Card>
      <CardHeader title={title} description="CSS conic chart — no external chart library" />
      <CardBody className="flex flex-col items-center gap-4 sm:flex-row">
        <div
          className="h-36 w-36 shrink-0 rounded-full"
          style={{
            background:
              slices.length > 0
                ? `conic-gradient(${stops.join(", ")})`
                : "var(--surface-2)",
          }}
          role="img"
          aria-label={`${title} allocation donut`}
        />
        <ul className="w-full space-y-1 text-sm">
          {slices.slice(0, 8).map((s) => (
            <li key={s.id} className="flex justify-between gap-2">
              <span>{s.label}</span>
              <span className="text-[var(--muted)]">{s.weight.toFixed(1)}%</span>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

export function SectorBarChart({
  slices,
  title,
}: {
  slices: AllocationSlice[];
  title: string;
}) {
  const max = Math.max(...slices.map((s) => s.weight), 1);
  return (
    <Card>
      <CardHeader title={title} />
      <CardBody className="space-y-2">
        <ul className="space-y-2" aria-label={title}>
          {slices.slice(0, 10).map((s) => (
            <li key={s.id}>
              <div className="mb-1 flex justify-between text-xs">
                <span>{s.label}</span>
                <span>{s.weight.toFixed(1)}%</span>
              </div>
              <div className="h-2 rounded bg-[var(--surface-2)]">
                <div
                  className="h-2 rounded bg-[var(--accent)]"
                  style={{ width: `${(s.weight / max) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

export function QualityHistogram({
  slices,
  title,
}: {
  slices: AllocationSlice[];
  title: string;
}) {
  return <SectorBarChart slices={slices} title={title} />;
}

export function PortfolioRiskHeatmap({
  symbols,
  scores,
}: {
  symbols: string[];
  scores: number[];
}) {
  return (
    <Card>
      <CardHeader
        title="Risk heatmap"
        description="Relative presentation intensity by holding weight proxy"
      />
      <CardBody>
        <div
          className="grid grid-cols-2 gap-2 sm:grid-cols-4"
          role="list"
          aria-label="Risk heatmap"
        >
          {symbols.map((sym, i) => {
            const score = scores[i] ?? 0;
            const opacity = Math.min(0.15 + score / 100, 0.85);
            return (
              <div
                key={sym}
                role="listitem"
                className="flex min-h-16 flex-col justify-center rounded-md border border-[var(--border)] p-2 text-center text-sm"
                style={{ backgroundColor: `color-mix(in srgb, var(--accent) ${opacity * 100}%, transparent)` }}
              >
                <span className="font-medium">{sym}</span>
                <span className="text-xs text-[var(--muted)]">{score.toFixed(0)}</span>
              </div>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
}

export function WeightTreemap({ slices }: { slices: AllocationSlice[] }) {
  return (
    <Card>
      <CardHeader title="Weight treemap" description="Flex-weighted blocks" />
      <CardBody>
        <div className="flex min-h-32 flex-wrap gap-1" role="img" aria-label="Weight treemap">
          {slices.slice(0, 12).map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-center rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/50 p-2 text-xs"
              style={{ flexGrow: Math.max(s.weight, 1), flexBasis: `${Math.max(s.weight, 8)}%` }}
              title={`${s.label} ${s.weight.toFixed(1)}%`}
            >
              {s.label}
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

export function ExpectedReturnChart({
  cagr,
  total,
}: {
  cagr: TrustedMetric;
  total: TrustedMetric;
}) {
  const bars = [
    { label: "Expected CAGR", m: cagr },
    { label: "Expected Total Return", m: total },
  ];
  return (
    <Card>
      <CardHeader title="Expected return chart" />
      <CardBody className="space-y-3">
        {bars.map((b) => (
          <div key={b.label}>
            <div className="mb-1 flex justify-between text-xs">
              <span>{b.label}</span>
              <span>{b.m.value ?? "Unavailable"}</span>
            </div>
            <div className="h-3 rounded bg-[var(--surface-2)]">
              <div
                className="h-3 rounded bg-[var(--accent)]"
                style={{
                  width:
                    b.m.numeric != null
                      ? `${Math.min(Math.abs(b.m.numeric) * 4, 100)}%`
                      : "0%",
                }}
              />
            </div>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}
