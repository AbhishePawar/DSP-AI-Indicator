"use client";

/**
 * FundamentalsSection — compact Indian equity-research terminal fundamentals block.
 *
 * Data sources (all existing, no mock data):
 *   - view.snapshot        → CMP, marketCap, 52W range
 *   - view.conclusion      → intrinsicValueRange, marginOfSafety
 *   - view.valuation       → currentPrice, intrinsicValueRange, marginOfSafety, summary
 *   - view.dashboard       → financialScore, growthScore, businessScore, riskScore
 *   - view.financialStrength → MetricView[] (ROE, ROCE, debt, margins, etc.)
 *   - view.growth          → GrowthInsightView[] (revenue, earnings, EPS growth)
 *
 * Rendering rules:
 *   - Available fields: show value with accent colour
 *   - Unavailable fields: show "—" in muted colour (never invent values)
 *   - Terminal aesthetic: monospace values, compact rows, dense grid
 */

import type {
  AnalysisWorkspaceView,
  DisplayField,
  MetricView,
  GrowthInsightView,
} from "@/lib/analysis/types";

/* ─── Helpers ────────────────────────────────────────────────────── */

function dv(field: DisplayField<string | number | string[]>): string {
  if (!field || field.presence === "unavailable" || field.value == null) return "—";
  if (Array.isArray(field.value)) return field.value.join(" · ");
  return String(field.value);
}

function avail(field: DisplayField<unknown>): boolean {
  return field?.presence === "available" && field.value != null;
}

/* ─── Score colour ───────────────────────────────────────────────── */

function scoreColour(scoreStr: string): string {
  if (scoreStr === "—") return "text-[var(--muted)]";
  const n = parseFloat(scoreStr);
  if (isNaN(n)) return "text-[var(--accent)]";
  if (n >= 7) return "text-emerald-400";
  if (n >= 5) return "text-amber-400";
  return "text-red-400";
}

/* ─── Rating colour ──────────────────────────────────────────────── */

function ratingColour(rating: string): string {
  const r = rating.toLowerCase();
  if (r.includes("strong") || r.includes("excellent") || r.includes("high")) return "text-emerald-400";
  if (r.includes("good") || r.includes("moderate") || r.includes("medium")) return "text-amber-400";
  if (r.includes("weak") || r.includes("poor") || r.includes("low")) return "text-red-400";
  return "text-[var(--accent)]";
}

/* ─── Terminal metric cell ───────────────────────────────────────── */

interface CellProps {
  label: string;
  value: string;
  available: boolean;
  valueClass?: string;
  sub?: string;
}

function Cell({ label, value, available: isAvail, valueClass, sub }: CellProps) {
  return (
    <div className="flex flex-col gap-0.5 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
      <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </span>
      <span
        className={[
          "font-mono text-sm font-semibold leading-tight",
          valueClass ?? (isAvail ? "text-[var(--accent)]" : "text-[var(--muted)]"),
        ].join(" ")}
      >
        {value}
      </span>
      {sub ? <span className="text-[9px] text-[var(--muted)]">{sub}</span> : null}
    </div>
  );
}

/* ─── Group header ───────────────────────────────────────────────── */

function GroupHeader({ label }: { label: string }) {
  return (
    <div className="col-span-full flex items-center gap-2 pb-0.5 pt-2">
      <span className="text-[9px] font-bold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </span>
      <div className="h-px flex-1 bg-[var(--border)]" />
    </div>
  );
}

/* ─── Metric row (from MetricView[]) ─────────────────────────────── */

function MetricRow({ metric }: { metric: MetricView }) {
  if (!metric.available) return null;
  return (
    <div className="flex items-start justify-between gap-3 border-b border-[var(--border)] py-2 last:border-0">
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-[var(--fg)]">{metric.title}</p>
        {metric.meaning ? (
          <p className="mt-0.5 line-clamp-1 text-[10px] text-[var(--muted)]">{metric.meaning}</p>
        ) : null}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-0.5">
        <span className={["font-mono text-xs font-semibold", ratingColour(metric.rating)].join(" ")}>
          {metric.actualValue !== "" ? metric.actualValue : metric.rating}
        </span>
        {metric.rating && metric.actualValue !== metric.rating ? (
          <span className={["text-[9px] font-medium uppercase", ratingColour(metric.rating)].join(" ")}>
            {metric.rating}
          </span>
        ) : null}
      </div>
    </div>
  );
}

/* ─── Growth row (from GrowthInsightView[]) ─────────────────────── */

function GrowthRow({ item }: { item: GrowthInsightView }) {
  if (!item.available) return null;
  return (
    <div className="flex items-start justify-between gap-3 border-b border-[var(--border)] py-2 last:border-0">
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-[var(--fg)]">{item.title}</p>
        {item.meaning ? (
          <p className="mt-0.5 line-clamp-1 text-[10px] text-[var(--muted)]">{item.meaning}</p>
        ) : null}
      </div>
      <span className={["shrink-0 font-mono text-xs font-semibold", ratingColour(item.rating)].join(" ")}>
        {item.rating}
      </span>
    </div>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

interface FundamentalsSectionProps {
  view: AnalysisWorkspaceView;
}

export function FundamentalsSection({ view }: FundamentalsSectionProps) {
  const { snapshot, conclusion, valuation, dashboard, financialStrength, growth } = view;

  /* Key price / value metrics */
  const cmp = dv(snapshot.currentMarketPrice);
  const cmpAvail = avail(snapshot.currentMarketPrice);
  const mktCap = dv(snapshot.marketCap);
  const mktCapAvail = avail(snapshot.marketCap);
  const w52High = dv(snapshot.week52High);
  const w52Low = dv(snapshot.week52Low);
  const w52Avail = avail(snapshot.week52High) || avail(snapshot.week52Low);

  /* Intrinsic value / MoS — prefer valuation, fall back to conclusion */
  const ivRange =
    avail(valuation.intrinsicValueRange)
      ? dv(valuation.intrinsicValueRange)
      : dv(conclusion.intrinsicValueRange);
  const ivAvail =
    avail(valuation.intrinsicValueRange) || avail(conclusion.intrinsicValueRange);

  const mos =
    avail(valuation.marginOfSafety)
      ? dv(valuation.marginOfSafety)
      : dv(conclusion.marginOfSafety);
  const mosAvail =
    avail(valuation.marginOfSafety) || avail(conclusion.marginOfSafety);

  /* Dashboard scores */
  const finScore = dv(dashboard.financialScore);
  const finScoreAvail = avail(dashboard.financialScore);
  const growScore = dv(dashboard.growthScore);
  const growScoreAvail = avail(dashboard.growthScore);
  const bizScore = dv(dashboard.businessScore);
  const bizScoreAvail = avail(dashboard.businessScore);
  const riskScore = dv(dashboard.riskScore);
  const riskScoreAvail = avail(dashboard.riskScore);

  /* Valuation summary */
  const valSummary = avail(valuation.summary) ? dv(valuation.summary) : null;

  /* Filter available metrics */
  const availableFinancial = financialStrength.filter((m) => m.available);
  const availableGrowth = growth.filter((g) => g.available);

  return (
    <div className="space-y-5">
      {/* ── Overview grid ─────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
        <GroupHeader label="Price & Market" />
        <Cell label="CMP" value={cmp} available={cmpAvail} />
        <Cell label="Market Cap" value={mktCap} available={mktCapAvail} />
        <Cell
          label="52W Range"
          value={w52Avail ? `${w52Low} – ${w52High}` : "—"}
          available={w52Avail}
        />

        <GroupHeader label="Valuation" />
        <Cell label="Intrinsic Value" value={ivRange} available={ivAvail} />
        <Cell
          label="Margin of Safety"
          value={mos}
          available={mosAvail}
          valueClass={mosAvail ? mosColourClass(mos) : "text-[var(--muted)]"}
        />

        <GroupHeader label="Quality Scores" />
        <Cell
          label="Financial"
          value={finScore}
          available={finScoreAvail}
          valueClass={finScoreAvail ? scoreColour(finScore) : "text-[var(--muted)]"}
          sub="/10"
        />
        <Cell
          label="Growth"
          value={growScore}
          available={growScoreAvail}
          valueClass={growScoreAvail ? scoreColour(growScore) : "text-[var(--muted)]"}
          sub="/10"
        />
        <Cell
          label="Business"
          value={bizScore}
          available={bizScoreAvail}
          valueClass={bizScoreAvail ? scoreColour(bizScore) : "text-[var(--muted)]"}
          sub="/10"
        />
        <Cell
          label="Risk"
          value={riskScore}
          available={riskScoreAvail}
          valueClass={riskScoreAvail ? scoreColour(riskScore) : "text-[var(--muted)]"}
          sub="/10"
        />
      </div>

      {/* ── Valuation summary ─────────────────────────────────── */}
      {valSummary ? (
        <p className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs text-[var(--fg)]">
          <span className="mr-1.5 text-[9px] font-bold uppercase tracking-widest text-[var(--muted)]">
            Valuation Summary ·
          </span>
          {valSummary}
        </p>
      ) : null}

      {/* ── Financial strength metrics ─────────────────────────── */}
      {availableFinancial.length > 0 ? (
        <div>
          <p className="mb-2 text-[9px] font-bold uppercase tracking-widest text-[var(--muted)]">
            Financial Strength Metrics
          </p>
          <div className="grid gap-x-6 gap-y-0 sm:grid-cols-2 lg:grid-cols-3">
            {availableFinancial.map((m) => (
              <MetricRow key={m.id} metric={m} />
            ))}
          </div>
        </div>
      ) : null}

      {/* ── Growth metrics ────────────────────────────────────── */}
      {availableGrowth.length > 0 ? (
        <div>
          <p className="mb-2 text-[9px] font-bold uppercase tracking-widest text-[var(--muted)]">
            Growth Indicators
          </p>
          <div className="grid gap-x-6 gap-y-0 sm:grid-cols-2 lg:grid-cols-3">
            {availableGrowth.map((g) => (
              <GrowthRow key={g.id} item={g} />
            ))}
          </div>
        </div>
      ) : null}

      {/* ── Empty state ───────────────────────────────────────── */}
      {availableFinancial.length === 0 && availableGrowth.length === 0 ? (
        <p className="text-xs text-[var(--muted)]">
          Detailed fundamental metrics will appear here once the analysis pipeline
          returns financial statement data for this company.
        </p>
      ) : null}
    </div>
  );
}

/* ─── MoS colour (local helper) ─────────────────────────────────── */

function mosColourClass(mosStr: string): string {
  const n = parseFloat(mosStr.replace(/[^0-9.\-]/g, ""));
  if (isNaN(n)) return "text-[var(--accent)]";
  if (n >= 30) return "text-emerald-400";
  if (n >= 10) return "text-amber-400";
  if (n >= 0) return "text-amber-500";
  return "text-red-400";
}
