"use client";

/**
 * Figma `CompanyAnalysis` trend card (AreaChart with gradient fill, muted
 * axis labels, tooltip). Pure SVG — no charting dependency — rendering only
 * the provider values handed to it by `mapFinancialTrends`.
 */

import { useId, useState } from "react";

import {
  formatTrendValue,
  type FinancialTrendSeries,
} from "@/lib/company-analysis";
import { cn } from "@/lib/utils";

const W = 320;
const H = 120;
const PAD_X = 12;
const PAD_TOP = 8;
const PAD_BOTTOM = 22;

function scaleY(value: number, min: number, max: number): number {
  const span = max - min || 1;
  return PAD_TOP + (1 - (value - min) / span) * (H - PAD_TOP - PAD_BOTTOM);
}

export function TrendChart({
  series,
  eyebrow,
  footnote,
  className,
}: {
  series: FinancialTrendSeries;
  /** Uppercase eyebrow above the chart (Figma: "REVENUE TREND · ₹ Bn · Source…"). */
  eyebrow?: string;
  footnote?: string;
  className?: string;
}) {
  const gradientId = useId();
  const [active, setActive] = useState<number | null>(null);
  const points = series.points;
  const valued = points
    .map((p, i) => ({ ...p, i }))
    .filter((p): p is typeof p & { value: number } => p.value != null);

  const label =
    eyebrow ??
    `${series.title.toUpperCase()}${
      series.unit === "currency" && series.currency ? ` · ${series.currency}` : series.unit === "ratio" ? " · %" : ""
    }`;

  if (!series.available || valued.length < 2) {
    return (
      <div
        className={cn(
          "rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--card)] p-4",
          className,
        )}
      >
        <p className="mb-3 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.07em] text-[var(--muted)]">
          {label}
        </p>
        <div
          className="flex h-[120px] items-center justify-center rounded-[var(--radius-md)] border border-dashed border-[var(--border)] text-sm text-[var(--muted)]"
          role="img"
          aria-label={`${series.title}: Data unavailable.`}
        >
          Data unavailable.
        </div>
        <p className="mt-2 text-[11px] text-[var(--muted)]">
          {!series.authenticated
            ? "Authenticated statements were not returned for this company."
            : "Fewer than two authenticated periods carry this line item."}
        </p>
      </div>
    );
  }

  const values = valued.map((p) => p.value);
  const min = Math.min(0, ...values);
  const max = Math.max(...values);
  const stepX = (W - PAD_X * 2) / Math.max(1, points.length - 1);
  const coords = valued.map((p) => ({
    x: PAD_X + p.i * stepX,
    y: scaleY(p.value, min, max),
    point: p,
  }));
  const linePath = coords
    .map((c, idx) => `${idx === 0 ? "M" : "L"}${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
    .join(" ");
  const baselineY = scaleY(min, min, max);
  const areaPath = `${linePath} L${coords[coords.length - 1].x.toFixed(1)} ${baselineY} L${coords[0].x.toFixed(1)} ${baselineY} Z`;
  const activeCoord = active != null ? coords.find((c) => c.point.i === active) : undefined;

  return (
    <div
      className={cn(
        "rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--card)] p-4",
        className,
      )}
    >
      <p className="mb-3 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.07em] text-[var(--muted)]">
        {label}
      </p>
      <figure className="m-0">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-[120px] w-full"
          role="img"
          aria-label={`${series.title}: ${valued
            .map((p) => `${p.label} ${formatTrendValue(series, p.value)}`)
            .join(", ")}`}
          onMouseLeave={() => setActive(null)}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={series.colorVar} stopOpacity={0.18} />
              <stop offset="95%" stopColor={series.colorVar} stopOpacity={0} />
            </linearGradient>
          </defs>
          <path d={areaPath} fill={`url(#${gradientId})`} />
          <path
            d={linePath}
            fill="none"
            stroke={series.colorVar}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          {coords.map((c) => (
            <g key={c.point.periodEnd}>
              <rect
                x={c.x - stepX / 2}
                y={0}
                width={stepX}
                height={H}
                fill="transparent"
                onMouseEnter={() => setActive(c.point.i)}
                onFocus={() => setActive(c.point.i)}
                tabIndex={-1}
              />
              <circle
                cx={c.x}
                cy={c.y}
                r={active === c.point.i ? 3.5 : 2}
                fill={series.colorVar}
              />
              <text
                x={c.x}
                y={H - 6}
                textAnchor="middle"
                className="fill-[var(--muted)] font-[family-name:var(--font-mono)] text-[9px]"
              >
                {c.point.label}
              </text>
            </g>
          ))}
          {activeCoord ? (
            <g>
              <line
                x1={activeCoord.x}
                x2={activeCoord.x}
                y1={PAD_TOP}
                y2={H - PAD_BOTTOM}
                stroke="var(--border)"
                strokeDasharray="3 3"
              />
            </g>
          ) : null}
        </svg>
        <figcaption
          className="mt-2 flex items-center justify-between gap-3 font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]"
          aria-live="polite"
        >
          <span>
            {activeCoord
              ? `${activeCoord.point.label} · ${formatTrendValue(series, activeCoord.point.value)}`
              : `${coords[0].point.label} → ${coords[coords.length - 1].point.label}`}
          </span>
          <span>
            Latest {formatTrendValue(series, coords[coords.length - 1].point.value)}
          </span>
        </figcaption>
      </figure>
      {footnote ? (
        <p className="mt-2 text-[11px] text-[var(--muted)]">{footnote}</p>
      ) : null}
    </div>
  );
}
