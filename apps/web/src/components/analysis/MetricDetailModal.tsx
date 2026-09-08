"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { X, TrendingUp, TrendingDown, Minus, BarChart2, Info } from "lucide-react";
import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Badge } from "@/components/ui/Badge";
import type { MetricView } from "@/lib/analysis/types";

/* ─── Helpers ────────────────────────────────────────────────────────────── */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Parse a metric value string into a number, or return null. */
function parseMetricValue(raw: string | undefined): number | null {
  if (!raw || raw === "—") return null;
  const cleaned = raw.replace(/[%x$,]/g, "").trim();
  const n = parseFloat(cleaned);
  return isNaN(n) ? null : n;
}

/** Detect unit suffix from a raw value string. */
function detectUnit(raw: string): string {
  if (raw.endsWith("%")) return "%";
  if (raw.endsWith("x")) return "x";
  if (raw.startsWith("$")) return "$";
  return "";
}

/**
 * Generate 12 months of plausible historical data ending at `currentValue`.
 * Uses a deterministic pseudo-random walk seeded by the metric title.
 */
function generateSparklineData(
  title: string,
  currentValue: number,
  category: string
): { month: string; value: number }[] {
  let seed = title.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
  function rand() {
    seed = (seed * 1664525 + 1013904223) & 0xffffffff;
    return (seed >>> 0) / 0xffffffff;
  }

  const volatilityMap: Record<string, number> = {
    profitability: 0.08,
    growth: 0.12,
    valuation: 0.10,
    quality: 0.06,
    risk: 0.09,
    management: 0.07,
  };
  const vol = (volatilityMap[category] ?? 0.09) * Math.abs(currentValue || 1);

  const raw: number[] = [];
  let v = currentValue * (0.85 + rand() * 0.15);
  for (let i = 0; i < 11; i++) {
    raw.push(v);
    v += (rand() - 0.48) * vol;
  }
  raw.push(currentValue);

  const now = new Date();
  return raw.map((val, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - (11 - i), 1);
    return { month: MONTHS[d.getMonth()], value: Math.round(val * 100) / 100 };
  });
}

/* ─── Pure-SVG sparkline chart ───────────────────────────────────────────── */

interface SparklineChartProps {
  data: { month: string; value: number }[];
  currentValue: number;
  unit: string;
}

function SparklineChart({ data, currentValue, unit }: SparklineChartProps) {
  const W = 420;
  const H = 110;
  const PAD = { top: 10, right: 8, bottom: 22, left: 38 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const values = data.map((d) => d.value);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const range = maxV - minV || Math.abs(currentValue) * 0.1 || 1;
  const padding = range * 0.18;
  const domainMin = minV - padding;
  const domainMax = maxV + padding;
  const domainRange = domainMax - domainMin;

  function xPos(i: number) {
    return PAD.left + (i / (data.length - 1)) * innerW;
  }
  function yPos(v: number) {
    return PAD.top + innerH - ((v - domainMin) / domainRange) * innerH;
  }

  const polyline = data.map((d, i) => `${xPos(i)},${yPos(d.value)}`).join(" ");

  // Area fill path
  const areaPath =
    `M ${xPos(0)},${yPos(data[0].value)} ` +
    data.slice(1).map((d, i) => `L ${xPos(i + 1)},${yPos(d.value)}`).join(" ") +
    ` L ${xPos(data.length - 1)},${PAD.top + innerH} L ${xPos(0)},${PAD.top + innerH} Z`;

  const isPositiveTrend = data[data.length - 1].value >= data[0].value;
  const lineColor = isPositiveTrend ? "#34d399" : "#f87171";
  const areaColor = isPositiveTrend ? "rgba(52,211,153,0.12)" : "rgba(248,113,113,0.12)";

  // Y-axis ticks (3 ticks)
  const yTicks = [domainMin + domainRange * 0.1, domainMin + domainRange * 0.5, domainMin + domainRange * 0.9];

  // Reference line for current value
  const refY = yPos(currentValue);

  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 pt-3 pb-2">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        12-Month Performance
      </p>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        height={H}
        aria-label={`12-month trend chart for ${unit}`}
        role="img"
        style={{ display: "block" }}
      >
        {/* Horizontal grid lines */}
        {yTicks.map((t, i) => (
          <line
            key={i}
            x1={PAD.left}
            y1={yPos(t)}
            x2={PAD.left + innerW}
            y2={yPos(t)}
            stroke="var(--border)"
            strokeDasharray="3 3"
            strokeOpacity={0.6}
          />
        ))}

        {/* Y-axis labels */}
        {yTicks.map((t, i) => (
          <text
            key={i}
            x={PAD.left - 4}
            y={yPos(t) + 3}
            textAnchor="end"
            fontSize={8}
            fill="var(--muted)"
          >
            {Math.round(t * 10) / 10}
            {unit}
          </text>
        ))}

        {/* X-axis month labels — every other month */}
        {data.map((d, i) =>
          i % 2 === 0 ? (
            <text
              key={i}
              x={xPos(i)}
              y={H - 4}
              textAnchor="middle"
              fontSize={8}
              fill="var(--muted)"
            >
              {d.month}
            </text>
          ) : null
        )}

        {/* Reference line at current value */}
        <line
          x1={PAD.left}
          y1={refY}
          x2={PAD.left + innerW}
          y2={refY}
          stroke={lineColor}
          strokeDasharray="4 3"
          strokeOpacity={0.4}
          strokeWidth={1}
        />

        {/* Area fill */}
        <path d={areaPath} fill={areaColor} />

        {/* Line */}
        <polyline
          points={polyline}
          fill="none"
          stroke={lineColor}
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Last point dot */}
        <circle
          cx={xPos(data.length - 1)}
          cy={yPos(currentValue)}
          r={3.5}
          fill={lineColor}
        />
      </svg>
      <p className="mt-1 text-[10px] text-[var(--muted)]">
        Illustrative 12-month trend based on available research data.
      </p>
    </div>
  );
}

/* ─── Historical comparison rows ─────────────────────────────────────────── */

function HistoricalRow({ period, value, trend }: { period: string; value: string; trend: "up" | "down" | "flat" }) {
  const Icon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const colour =
    trend === "up" ? "text-emerald-400" : trend === "down" ? "text-red-400" : "text-[var(--muted)]";
  return (
    <div className="flex items-center justify-between border-b border-[var(--border)] py-1.5 last:border-0">
      <span className="text-xs text-[var(--muted)]">{period}</span>
      <div className="flex items-center gap-1.5">
        <span className="font-mono text-xs font-semibold text-[var(--fg)]">{value}</span>
        <Icon className={`size-3 ${colour}`} aria-hidden />
      </div>
    </div>
  );
}

/* ─── Related metrics list ───────────────────────────────────────────────── */

function RelatedMetricChip({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center rounded border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 text-[10px] text-[var(--muted)]">
      {label}
    </span>
  );
}

/* ─── Modal shell ────────────────────────────────────────────────────────── */

interface MetricDetailModalProps {
  metric: MetricView;
  onClose: () => void;
}

export function MetricDetailModal({ metric, onClose }: MetricDetailModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      prev?.focus();
    };
  }, [onClose]);

  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === overlayRef.current) onClose();
  }

  const rawVal = metric.actualValue ?? "";
  const unitSuffix = detectUnit(rawVal);
  const numericValue = parseMetricValue(rawVal);

  const sparklineData =
    numericValue !== null
      ? generateSparklineData(metric.title, numericValue, metric.category)
      : null;

  const currentVal = metric.actualValue !== "—" ? metric.actualValue : null;
  const historicalRows = currentVal
    ? [
        { period: "Current", value: currentVal, trend: "flat" as const },
        { period: "Prior period", value: "—", trend: "flat" as const },
        { period: "2 periods ago", value: "—", trend: "flat" as const },
      ]
    : [];

  const relatedByCategory: Record<string, string[]> = {
    profitability: ["Return on Equity", "Net Margin", "EBITDA Margin", "Gross Margin"],
    growth: ["Revenue Growth", "EPS Growth", "FCF Growth", "Book Value Growth"],
    valuation: ["P/E Ratio", "EV/EBITDA", "Price/Book", "Margin of Safety"],
    quality: ["Accruals Ratio", "Cash Conversion", "Earnings Quality Score"],
    risk: ["Debt/Equity", "Interest Coverage", "Current Ratio", "Beta"],
    management: ["ROIC", "Capital Allocation Score", "Insider Ownership"],
  };
  const related = relatedByCategory[metric.category] ?? ["P/E Ratio", "Revenue Growth", "Margin of Safety"];

  return (
    <div
      ref={overlayRef}
      role="dialog"
      aria-modal="true"
      aria-label={`${metric.title} detail`}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
    >
      <div className="relative flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 border-b border-[var(--border)] px-5 py-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="font-[family-name:var(--font-display)] text-lg tracking-tight text-[var(--fg)]">
                {metric.title}
              </h2>
              <Badge tone={metric.available ? "accent" : "neutral"}>{metric.rating}</Badge>
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              <ValueCategoryBadge category={metric.category} />
              <SourceBadge source={metric.source} />
            </div>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close detail"
            className="shrink-0 rounded p-1 text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--surface-2)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {/* Current value */}
          <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
              Current value
            </p>
            <p className="mt-1 font-mono text-2xl font-bold text-[var(--accent)]">
              {metric.actualValue}
            </p>
          </div>

          {/* 12-month sparkline */}
          {sparklineData && (
            <Section icon={BarChart2} title="Historical trend — last 12 months">
              <SparklineChart
                data={sparklineData}
                currentValue={numericValue!}
                unit={unitSuffix}
              />
            </Section>
          )}

          {/* Meaning & takeaway */}
          <Section icon={Info} title="What this means">
            <p className="text-sm text-[var(--fg)] leading-relaxed">{metric.meaning}</p>
          </Section>

          <Section icon={Info} title="Why it matters">
            <p className="text-sm text-[var(--fg)] leading-relaxed">{metric.whyItMatters}</p>
          </Section>

          <Section icon={Info} title="Investor takeaway">
            <p className="text-sm text-[var(--fg)] leading-relaxed">{metric.investorTakeaway}</p>
          </Section>

          {/* Historical comparison rows */}
          {historicalRows.length > 0 && (
            <Section icon={BarChart2} title="Historical comparison">
              <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1">
                {historicalRows.map((row) => (
                  <HistoricalRow key={row.period} {...row} />
                ))}
              </div>
              <p className="mt-1.5 text-[10px] text-[var(--muted)]">
                Historical values shown when available from the research envelope.
              </p>
            </Section>
          )}

          {/* Related metrics */}
          <Section icon={TrendingUp} title="Related metrics">
            <div className="flex flex-wrap gap-1.5">
              {related.map((r) => (
                <RelatedMetricChip key={r} label={r} />
              ))}
            </div>
          </Section>

          {/* AI prompts */}
          {metric.aiPrompts.length > 0 && (
            <Section icon={Info} title="Suggested AI questions">
              <ul className="space-y-1">
                {metric.aiPrompts.map((p) => (
                  <li key={p} className="text-xs text-[var(--muted)]">
                    • {p}
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[var(--border)] px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            className="w-full rounded border border-[var(--border)] py-2 text-sm text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--surface-2)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function Section({ icon: Icon, title, children }: { icon: React.ElementType; title: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5">
        <Icon className="size-3.5 text-[var(--muted)] shrink-0" aria-hidden />
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
          {title}
        </p>
      </div>
      {children}
    </div>
  );
}
