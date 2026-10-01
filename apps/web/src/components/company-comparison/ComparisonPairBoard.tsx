"use client";

/**
 * ZIP Security Compare presentation.
 * Renders the first two comparison slots from the existing workspace model.
 * No scoring, ranking, or valuation math — display only.
 */

import { DATA_UNAVAILABLE } from "@/lib/company-comparison";
import type {
  ComparisonWorkspaceModel,
  ExecutiveScorecardRowId,
} from "@/lib/company-comparison";

const PAIR_ROWS: ExecutiveScorecardRowId[] = [
  "valuation",
  "businessQuality",
  "financial",
  "risk",
  "moat",
  "overall",
];

function cellFor(model: ComparisonWorkspaceModel, rowId: ExecutiveScorecardRowId, symbol: string) {
  const row = model.scorecard.find((item) => item.id === rowId);
  return row?.cells.find((cell) => cell.symbol === symbol)?.display || DATA_UNAVAILABLE;
}

function qualityLabel(model: ComparisonWorkspaceModel, symbol: string): string {
  return (
    model.qualityModules.businessQuality.find((item) => item.symbol === symbol)?.label ||
    DATA_UNAVAILABLE
  );
}

/** ZIP radar axes. Values are not invented — the comparison API does not return these 0–100 axes. */
export const COMPARISON_RADAR_AXES = [
  "Profitability",
  "Growth",
  "Margins",
  "Valuation",
  "Cash Flow",
  "Low Debt",
] as const;

function ComparisonRadar({
  leftLabel,
  rightLabel,
}: {
  leftLabel: string;
  rightLabel: string;
}) {
  const cx = 120;
  const cy = 120;
  const radius = 78;
  const points = COMPARISON_RADAR_AXES.map((_, index) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / COMPARISON_RADAR_AXES.length;
    return {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
      label: COMPARISON_RADAR_AXES[index],
    };
  });
  const outline = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <article className="rounded-[14px] border border-[var(--border)] bg-[var(--card)] px-4 py-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="m-0 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.08em] text-[var(--muted)]">
          QUALITY SHAPE
        </h3>
        <div className="flex gap-3 font-[family-name:var(--font-mono)] text-[10px]">
          <span style={{ color: "var(--c-revenue)" }}>{leftLabel}</span>
          <span style={{ color: "var(--c-profit)" }}>{rightLabel}</span>
        </div>
      </div>
      <div className="grid items-center gap-4 md:grid-cols-[240px_1fr]">
        <svg viewBox="0 0 240 240" role="img" aria-label="Comparison radar. Axis scores are unavailable." className="mx-auto h-56 w-56">
          <polygon points={outline} fill="none" stroke="var(--border)" strokeWidth="1" />
          {points.map((point) => (
            <line key={point.label} x1={cx} y1={cy} x2={point.x} y2={point.y} stroke="var(--border)" strokeWidth="1" />
          ))}
          {points.map((point) => (
            <text
              key={`${point.label}-label`}
              x={point.x}
              y={point.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="var(--muted)"
              fontSize="8"
            >
              {point.label}
            </text>
          ))}
        </svg>
        <ul className="m-0 list-none space-y-1.5 p-0">
          {COMPARISON_RADAR_AXES.map((axis) => (
            <li key={axis} className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="text-[var(--fg)]">{axis}</span>
              <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">{DATA_UNAVAILABLE}</span>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}

export function ComparisonPairBoard({ model }: { model: ComparisonWorkspaceModel }) {
  const pair = model.slots.slice(0, 2);
  if (pair.length < 2) return null;
  const [left, right] = pair;
  const accents = ["var(--c-revenue)", "var(--c-profit)"] as const;

  return (
    <section aria-label="Side-by-side comparison" className="mb-4 space-y-3">
      <div className="grid gap-3 md:grid-cols-2">
        {pair.map((slot, index) => (
          <article
            key={slot.symbol}
            className="rounded-[14px] border border-[var(--border)] bg-[var(--card)] px-4 py-4"
          >
            <p
              className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.08em]"
              style={{ color: accents[index] }}
            >
              SECURITY {index + 1}
            </p>
            <h2 className="m-0 mt-1 font-[family-name:var(--font-display)] text-2xl font-medium text-[var(--fg)]">
              {slot.symbol}
            </h2>
            <p className="m-0 mt-1 text-sm text-[var(--muted)]">
              {slot.company && slot.company !== slot.symbol ? slot.company : DATA_UNAVAILABLE}
            </p>
            <p className="m-0 mt-3 font-[family-name:var(--font-mono)] text-xs text-[var(--fg)]">
              {slot.status === "ready" ? qualityLabel(model, slot.symbol) : slot.status}
            </p>
          </article>
        ))}
      </div>

      <ComparisonRadar leftLabel={left.symbol} rightLabel={right.symbol} />

      <div className="overflow-x-auto rounded-[14px] border border-[var(--border)] bg-[var(--card)]">
        <table className="w-full min-w-[32rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-[var(--border)]">
              <th className="px-4 py-2.5 text-left font-[family-name:var(--font-mono)] text-[10px] font-medium uppercase tracking-[0.06em] text-[var(--muted)]">
                Metric
              </th>
              <th className="px-4 py-2.5 text-left font-[family-name:var(--font-mono)] text-[10px] font-medium uppercase tracking-[0.06em]" style={{ color: accents[0] }}>
                {left.symbol}
              </th>
              <th className="px-4 py-2.5 text-left font-[family-name:var(--font-mono)] text-[10px] font-medium uppercase tracking-[0.06em]" style={{ color: accents[1] }}>
                {right.symbol}
              </th>
            </tr>
          </thead>
          <tbody>
            {PAIR_ROWS.map((rowId) => {
              const row = model.scorecard.find((item) => item.id === rowId);
              return (
                <tr key={rowId} className="border-b border-[var(--border)] last:border-0">
                  <th scope="row" className="px-4 py-3 text-left text-[13px] font-medium text-[var(--fg)]">
                    {row?.label ?? rowId}
                  </th>
                  <td className="px-4 py-3 font-[family-name:var(--font-mono)] text-[13px] text-[var(--fg)]">
                    {cellFor(model, rowId, left.symbol)}
                  </td>
                  <td className="px-4 py-3 font-[family-name:var(--font-mono)] text-[13px] text-[var(--fg)]">
                    {cellFor(model, rowId, right.symbol)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <article className="rounded-[14px] border border-[var(--border)] bg-[var(--card)] px-4 py-4">
          <h3 className="m-0 mb-2 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.08em] text-[var(--muted)]">
            TRADE-OFFS
          </h3>
          {model.tradeOffs.length === 0 ? (
            <p className="m-0 text-sm text-[var(--muted)]">{DATA_UNAVAILABLE}</p>
          ) : (
            <ul className="m-0 list-none space-y-2 p-0">
              {model.tradeOffs.slice(0, 4).map((item) => (
                <li key={`${item.dimension}-${item.stronger}`} className="text-[13px] leading-relaxed text-[var(--fg)]">
                  <span className="font-medium">{item.dimension}.</span> {item.summary}
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="rounded-[14px] border border-[var(--border)] bg-[var(--card)] px-4 py-4">
          <h3 className="m-0 mb-2 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.08em] text-[var(--muted)]">
            EVIDENCE
          </h3>
          <p className="m-0 text-[13px] leading-relaxed text-[var(--fg)]">
            {model.executive.evidenceQuality || DATA_UNAVAILABLE}
          </p>
          <p className="mb-0 mt-2 text-xs text-[var(--muted)]">
            {model.executive.confidence
              ? `Confidence: ${model.executive.confidence}`
              : DATA_UNAVAILABLE}
          </p>
        </article>
      </div>
    </section>
  );
}
