"use client";

/**
 * Figma Make page primitives shared by Dashboard / Portfolio / Research Hub /
 * Institutional Research (TopBar title + subtitle, 24×28 scroll padding,
 * card panels, uppercase mono stat labels, table header style).
 * Pure presentation — no data fetching, no scoring.
 */

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function FigmaPage({
  title,
  subtitle,
  actions,
  children,
  gap = 20,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  gap?: 20 | 24;
}) {
  return (
    <div className="flex min-h-full flex-col">
      <div className="page-header -mx-4 mb-0 sm:-mx-6">
        <div className="min-w-0">
          <h1 className="break-words font-[family-name:var(--font-display)] text-base font-medium tracking-tight text-[var(--fg)] sm:text-lg">
            {title}
          </h1>
          {subtitle ? (
            <p className="mt-0.5 font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">
              {subtitle}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
      <div
        className={cn(
          "flex flex-1 flex-col py-6 sm:px-1",
          gap === 24 ? "gap-6" : "gap-5",
        )}
      >
        {children}
      </div>
    </div>
  );
}

/** Figma card panel with optional bordered header row. */
export function Panel({
  title,
  action,
  children,
  className,
  bodyClassName,
  padded = false,
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  padded?: boolean;
}) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)]",
        className,
      )}
    >
      {title ? (
        <header className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-5 py-3.5">
          <span className="text-[13px] font-medium text-[var(--fg)]">{title}</span>
          {action}
        </header>
      ) : null}
      <div className={cn(padded && "p-4", bodyClassName)}>{children}</div>
    </section>
  );
}

export function StatCard({
  label,
  value,
  note,
  tone = "fg",
  children,
}: {
  label: string;
  value: string;
  note?: string;
  tone?: "fg" | "muted" | "profit" | "risk";
  children?: ReactNode;
}) {
  const color =
    tone === "profit"
      ? "var(--c-profit)"
      : tone === "risk"
        ? "var(--c-risk)"
        : tone === "muted"
          ? "var(--muted)"
          : "var(--fg)";
  const unavailable = value === "Data unavailable.";
  return (
    <div className="rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-4 py-3.5">
      <p className="mb-1.5 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.06em] text-[var(--muted)]">
        {label}
      </p>
      <p
        className={cn(
          "font-[family-name:var(--font-mono)] font-semibold",
          unavailable ? "text-sm text-[var(--muted)]" : "text-[22px] leading-tight",
        )}
        style={unavailable ? undefined : { color }}
      >
        {value}
      </p>
      {note ? <p className="mt-1 text-[11px] text-[var(--muted)]">{note}</p> : null}
      {children}
    </div>
  );
}

export const TH_CLASS =
  "border-b border-[var(--border)] px-4 py-2.5 text-left font-[family-name:var(--font-mono)] text-[10px] font-medium uppercase tracking-[0.06em] text-[var(--muted)]";

export const TD_CLASS = "px-4 py-3 text-[13px] text-[var(--fg)]";

export function DataCell({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <td className={cn(TD_CLASS, "font-[family-name:var(--font-mono)]", className)}>{children}</td>
  );
}

/** Figma DSP rating pill (var(--c-dsp) on 12% tint). */
export function RatingPill({ value }: { value: string }) {
  if (!value || value === "—" || value === "Data unavailable.") {
    return <span className="text-xs text-[var(--muted)]">—</span>;
  }
  return (
    <span className="rounded-md bg-[color-mix(in_srgb,var(--c-dsp)_12%,transparent)] px-2 py-0.5 font-[family-name:var(--font-mono)] text-xs text-[var(--c-dsp)]">
      {value}
    </span>
  );
}

/**
 * Figma market-bar sparkline (recharts `LineChart` · `dot={false}` ·
 * strokeWidth 1.5). Provider close series only — never synthesised.
 */
export function Sparkline({
  values,
  stroke,
  height = 36,
  label,
}: {
  values: readonly number[];
  stroke: string;
  height?: number;
  label?: string;
}) {
  const finite = values.filter((v) => Number.isFinite(v));
  if (finite.length < 2) {
    return (
      <div
        className="rounded border border-dashed border-[var(--border)]"
        style={{ height }}
        aria-hidden="true"
      />
    );
  }
  const width = 100;
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  const span = max - min || 1;
  const points = finite
    .map((v, i) => {
      const x = (i / (finite.length - 1)) * width;
      const y = height - 2 - ((v - min) / span) * (height - 4);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      width="100%"
      height={height}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <polyline
        points={points}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/**
 * Figma multi-line chart (recharts `LineChart` · dashed `CartesianGrid` ·
 * axis labels, `dot={false}`, strokeWidth 2) as static SVG. Data in → geometry
 * out; nothing is interpolated or extrapolated.
 */
export function MiniLineChart({
  categories,
  series,
  height = 160,
  label,
}: {
  categories: readonly string[];
  series: readonly { name: string; values: readonly (number | null)[]; stroke: string }[];
  height?: number;
  label: string;
}) {
  const width = 240;
  const padL = 28;
  const padB = 18;
  const padT = 6;
  const innerW = width - padL - 4;
  const innerH = height - padB - padT;
  const all = series.flatMap((s) => s.values.filter((v): v is number => typeof v === "number"));
  if (categories.length === 0 || all.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed border-[var(--border)] text-sm text-[var(--muted)]"
        style={{ height }}
        role="img"
        aria-label={`${label}: Data unavailable.`}
      >
        Data unavailable.
      </div>
    );
  }
  const max = Math.max(...all, 1);
  const x = (i: number) => padL + (categories.length === 1 ? innerW / 2 : (i / (categories.length - 1)) * innerW);
  const y = (v: number) => padT + innerH - (v / max) * innerH;
  const ticks = [0, 0.5, 1].map((f) => Math.round(max * f));
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img" aria-label={label}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={padL} x2={width - 4} y1={y(t)} y2={y(t)} stroke="var(--border)" strokeDasharray="3 3" />
          <text x={padL - 4} y={y(t) + 3} textAnchor="end" fontSize={9} fill="var(--muted)" fontFamily="var(--font-mono)">
            {t}
          </text>
        </g>
      ))}
      {categories.map((c, i) => (
        <text key={c} x={x(i)} y={height - 4} textAnchor="middle" fontSize={9} fill="var(--muted)" fontFamily="var(--font-mono)">
          {c}
        </text>
      ))}
      {series.map((s) => {
        const pts = s.values
          .map((v, i) => (typeof v === "number" ? `${x(i).toFixed(1)},${y(v).toFixed(1)}` : null))
          .filter((p): p is string => p !== null);
        return pts.length ? (
          <polyline key={s.name} points={pts.join(" ")} fill="none" stroke={s.stroke} strokeWidth={2} strokeLinejoin="round" />
        ) : null;
      })}
    </svg>
  );
}

/** Figma bar chart (recharts `BarChart`, radius 3, opacity 0.8) as static SVG. */
export function MiniBarChart({
  data,
  fill = "var(--c-dsp)",
  height = 130,
  label,
}: {
  data: readonly { label: string; value: number }[];
  fill?: string;
  height?: number;
  label: string;
}) {
  const width = 240;
  const padL = 28;
  const padB = 18;
  const padT = 6;
  const innerW = width - padL - 4;
  const innerH = height - padB - padT;
  const total = data.reduce((a, d) => a + d.value, 0);
  if (data.length === 0 || total === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed border-[var(--border)] text-sm text-[var(--muted)]"
        style={{ height }}
        role="img"
        aria-label={`${label}: Data unavailable.`}
      >
        Data unavailable.
      </div>
    );
  }
  const max = Math.max(...data.map((d) => d.value), 1);
  const slot = innerW / data.length;
  const barW = Math.max(4, slot * 0.6);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img" aria-label={label}>
      {[0, max].map((t) => (
        <text key={t} x={padL - 4} y={padT + innerH - (t / max) * innerH + 3} textAnchor="end" fontSize={9} fill="var(--muted)" fontFamily="var(--font-mono)">
          {t}
        </text>
      ))}
      {data.map((d, i) => {
        const h = (d.value / max) * innerH;
        const bx = padL + i * slot + (slot - barW) / 2;
        return (
          <g key={d.label}>
            <rect x={bx} y={padT + innerH - h} width={barW} height={h} rx={3} fill={fill} opacity={0.8} />
            <text x={bx + barW / 2} y={height - 4} textAnchor="middle" fontSize={9} fill="var(--muted)" fontFamily="var(--font-mono)">
              {d.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function ChangeText({
  text,
  direction,
}: {
  text: string;
  direction: "up" | "down" | "flat" | null;
}) {
  const color =
    direction === "up"
      ? "var(--c-profit)"
      : direction === "down"
        ? "var(--c-risk)"
        : "var(--muted)";
  return (
    <span className="font-[family-name:var(--font-mono)] text-[13px]" style={{ color }}>
      {text}
    </span>
  );
}

/** Honest empty / unavailable state inside a panel. */
export function PanelEmpty({
  title = "Data unavailable.",
  description,
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-2 px-5 py-6" role="status">
      <p className="text-sm font-medium text-[var(--fg)]">{title}</p>
      {description ? (
        <p className="max-w-prose text-xs leading-relaxed text-[var(--muted)]">{description}</p>
      ) : null}
      {action}
    </div>
  );
}

/** Figma pill filter / sort button. */
export function PillButton({
  active,
  children,
  onClick,
  disabled,
  ariaLabel,
}: {
  active?: boolean;
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  ariaLabel?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      aria-label={ariaLabel}
      className={cn(
        "min-h-8 rounded-md border border-[var(--border)] px-2.5 font-[family-name:var(--font-mono)] text-[11px] capitalize transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
        active
          ? "bg-[var(--surface-2)] text-[var(--fg)]"
          : "bg-transparent text-[var(--muted)] hover:text-[var(--fg)]",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      {children}
    </button>
  );
}
