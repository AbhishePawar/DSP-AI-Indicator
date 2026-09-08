"use client";

/**
 * QualitySection — institutional equity-research quality block.
 *
 * Data sources (all existing, no mock data):
 *   - view.dashboard        → businessScore, financialScore, managementScore,
 *                             growthScore, riskScore, researchConfidence
 *   - view.businessQuality  → MetricView[] (business quality metrics)
 *   - view.financialStrength → MetricView[] (financial strength metrics)
 *   - view.management       → ManagementInsightView[] (management quality)
 *   - view.growth           → GrowthInsightView[] (growth quality)
 *   - view.risks            → RiskInsightView[] (risk indicators)
 *
 * Rendering rules:
 *   - Available fields: show value with restrained colour accent
 *   - Unavailable fields: show "—" in muted colour (never invent values)
 */

import type {
  AnalysisWorkspaceView,
  DisplayField,
  MetricView,
  GrowthInsightView,
  ManagementInsightView,
  RiskInsightView,
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
  if (isNaN(n)) return "text-[var(--fg)]";
  if (n >= 7) return "text-emerald-700";
  if (n >= 5) return "text-amber-700";
  return "text-red-700";
}

/* ─── Rating colour ──────────────────────────────────────────────── */

function ratingColour(rating: string): string {
  const r = rating.toLowerCase();
  if (r.includes("strong") || r.includes("excellent") || r.includes("high") || r.includes("good")) return "text-emerald-700";
  if (r.includes("moderate") || r.includes("medium") || r.includes("fair")) return "text-amber-700";
  if (r.includes("weak") || r.includes("poor") || r.includes("low")) return "text-red-700";
  return "text-[var(--fg)]";
}

/* ─── Score row ──────────────────────────────────────────────────── */

interface ScoreRowProps {
  label: string;
  score: string;
  isAvail: boolean;
}

function ScoreRow({ label, score, isAvail }: ScoreRowProps) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] py-2 last:border-0">
      <span className="min-w-0 flex-1 text-xs text-[var(--muted)]">{label}</span>
      <span className={["shrink-0 text-xs font-semibold tabular-nums", isAvail ? scoreColour(score) : "text-[var(--muted)]"].join(" ")}>
        {score}
      </span>
    </div>
  );
}

/* ─── Section label ──────────────────────────────────────────────── */

function SectionLabel({ label }: { label: string }) {
  return (
    <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
      {label}
    </p>
  );
}

/* ─── Metric row (from MetricView[]) ─────────────────────────────── */

function MetricRow({ metric }: { metric: MetricView }) {
  if (!metric.available) return null;
  const displayVal = metric.actualValue !== "" ? metric.actualValue : metric.rating;
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] py-2 last:border-0">
      <span className="min-w-0 flex-1 text-xs text-[var(--muted)]">{metric.title}</span>
      <div className="flex shrink-0 items-center gap-2">
        <span className={["text-xs font-semibold tabular-nums", ratingColour(metric.rating)].join(" ")}>
          {displayVal}
        </span>
        {metric.rating && metric.actualValue !== "" && metric.actualValue !== metric.rating ? (
          <span className={["text-[10px] font-semibold uppercase tracking-wide", ratingColour(metric.rating)].join(" ")}>
            {metric.rating}
          </span>
        ) : null}
      </div>
    </div>
  );
}

/* ─── Growth row ─────────────────────────────────────────────────── */

function GrowthRow({ item }: { item: GrowthInsightView }) {
  if (!item.available) return null;
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] py-2 last:border-0">
      <span className="min-w-0 flex-1 text-xs text-[var(--muted)]">{item.title}</span>
      <span className={["shrink-0 text-xs font-semibold", ratingColour(item.rating)].join(" ")}>
        {item.rating}
      </span>
    </div>
  );
}

/* ─── Management row ─────────────────────────────────────────────── */

function ManagementRow({ item }: { item: ManagementInsightView }) {
  if (!item.available) return null;
  const confidenceColour = (c: string) => {
    const l = c.toLowerCase();
    if (l === "high") return "text-emerald-700";
    if (l === "medium") return "text-amber-700";
    return "text-red-700";
  };
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] py-2 last:border-0">
      <span className="min-w-0 flex-1 text-xs text-[var(--muted)]">{item.title}</span>
      <span className={["shrink-0 text-xs font-semibold uppercase", confidenceColour(item.confidence)].join(" ")}>
        {item.confidence}
      </span>
    </div>
  );
}

/* ─── Risk row ───────────────────────────────────────────────────── */

function RiskRow({ item }: { item: RiskInsightView }) {
  if (!item.available) return null;
  const sevColour = (s: string) => {
    const l = s.toLowerCase();
    if (l === "high" || l === "critical") return "text-red-700";
    if (l === "medium" || l === "moderate") return "text-amber-700";
    return "text-emerald-700";
  };
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] py-2 last:border-0">
      <span className="min-w-0 flex-1 text-xs text-[var(--muted)]">{item.title}</span>
      <span className={["shrink-0 text-xs font-semibold uppercase", sevColour(item.severity)].join(" ")}>
        {item.severity}
      </span>
    </div>
  );
}

/* ─── Empty state ────────────────────────────────────────────────── */

function EmptyRows({ label }: { label: string }) {
  return (
    <p className="py-2 text-xs text-[var(--muted)]">
      No {label} data available in this analysis.
    </p>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

interface QualitySectionProps {
  view: AnalysisWorkspaceView;
}

export function QualitySection({ view }: QualitySectionProps) {
  const { dashboard, businessQuality, financialStrength, management, growth, risks } = view;

  /* ── Score indicators ─────────────────────────────────────── */
  const bizScore = dv(dashboard.businessScore);
  const bizAvail = avail(dashboard.businessScore);
  const finScore = dv(dashboard.financialScore);
  const finAvail = avail(dashboard.financialScore);
  const mgtScore = dv(dashboard.managementScore);
  const mgtAvail = avail(dashboard.managementScore);
  const growScore = dv(dashboard.growthScore);
  const growAvail = avail(dashboard.growthScore);
  const riskScore = dv(dashboard.riskScore);
  const riskAvail = avail(dashboard.riskScore);

  /* ── Supporting metrics ───────────────────────────────────── */
  const availBiz = businessQuality.filter((m) => m.available);
  const availFin = financialStrength.filter((m) => m.available);
  const availMgt = management.filter((m) => m.available);
  const availGrow = growth.filter((g) => g.available);
  const availRisk = risks.filter((r) => r.available);

  /* ── Confidence ───────────────────────────────────────────── */
  const confidence = dv(dashboard.researchConfidence);
  const confidenceAvail = avail(dashboard.researchConfidence);

  const hasAnyScore = bizAvail || finAvail || mgtAvail || growAvail || riskAvail;
  const hasAnyMetrics =
    availBiz.length > 0 ||
    availFin.length > 0 ||
    availMgt.length > 0 ||
    availGrow.length > 0 ||
    availRisk.length > 0;

  return (
    <div className="space-y-8">

      {/* ── Composite scores ──────────────────────────────────── */}
      <div>
        <div className="mb-1 flex items-center justify-between">
          <SectionLabel label="Composite Scores" />
          {confidenceAvail ? (
            <span className="text-[10px] text-[var(--muted)]">
              Research confidence:{" "}
              <span className={["font-semibold uppercase", ratingColour(confidence)].join(" ")}>
                {confidence}
              </span>
            </span>
          ) : null}
        </div>
        {hasAnyScore ? (
          <div className="divide-y divide-[var(--border)] rounded-none border-t border-[var(--border)]">
            <ScoreRow label="Business Quality" score={bizScore} isAvail={bizAvail} />
            <ScoreRow label="Financial Strength" score={finScore} isAvail={finAvail} />
            <ScoreRow label="Management Quality" score={mgtScore} isAvail={mgtAvail} />
            <ScoreRow label="Growth Quality" score={growScore} isAvail={growAvail} />
            <ScoreRow label="Risk Score" score={riskScore} isAvail={riskAvail} />
          </div>
        ) : (
          <p className="mt-2 text-xs text-[var(--muted)]">
            Quality scores are not yet available for this analysis.
          </p>
        )}
      </div>

      {/* ── Supporting quality metrics ─────────────────────────── */}
      {hasAnyMetrics ? (
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">

          {availBiz.length > 0 ? (
            <div>
              <SectionLabel label="Business Quality" />
              <div className="border-t border-[var(--border)]">
                {availBiz.slice(0, 6).map((m) => (
                  <MetricRow key={m.id} metric={m} />
                ))}
              </div>
            </div>
          ) : null}

          {availFin.length > 0 ? (
            <div>
              <SectionLabel label="Financial Strength" />
              <div className="border-t border-[var(--border)]">
                {availFin.slice(0, 6).map((m) => (
                  <MetricRow key={m.id} metric={m} />
                ))}
              </div>
            </div>
          ) : null}

          {availGrow.length > 0 ? (
            <div>
              <SectionLabel label="Growth Indicators" />
              <div className="border-t border-[var(--border)]">
                {availGrow.slice(0, 6).map((g) => (
                  <GrowthRow key={g.id} item={g} />
                ))}
              </div>
            </div>
          ) : null}

          {availMgt.length > 0 ? (
            <div>
              <SectionLabel label="Management Quality" />
              <div className="border-t border-[var(--border)]">
                {availMgt.slice(0, 6).map((m) => (
                  <ManagementRow key={m.id} item={m} />
                ))}
              </div>
            </div>
          ) : null}

          {availRisk.length > 0 ? (
            <div>
              <SectionLabel label="Risk Indicators" />
              <div className="border-t border-[var(--border)]">
                {availRisk.slice(0, 6).map((r) => (
                  <RiskRow key={r.id} item={r} />
                ))}
              </div>
            </div>
          ) : null}

        </div>
      ) : (
        !hasAnyScore ? (
          <EmptyRows label="quality metric" />
        ) : null
      )}
    </div>
  );
}
