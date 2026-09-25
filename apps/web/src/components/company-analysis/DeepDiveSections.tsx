"use client";

/**
 * Figma `CompanyAnalysis.tsx` DEEP DIVE sections â€” S07 Earnings Quality,
 * S08 Growth Quality, S10 Margin of Safety, S12 Strengths & Weaknesses,
 * S13 Investment Context.
 *
 * Display-only over ResearchView + the authenticated statements payload.
 * No scoring, no MoS arithmetic, no client-authored narrative.
 */

import type { ReactNode } from "react";

import { Badge } from "@/components/ds";
import {
  mapFinancialTrends,
  type FinancialTrendsView,
} from "@/lib/company-analysis";
import type { FinancialStatementsPayload } from "@/lib/institutional-dashboard/mapInstitutionalDashboard";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { cn } from "@/lib/utils";
import { TrendChart } from "./TrendChart";
import {
  FieldRow,
  firstStageMetric,
  SectionCard,
  StageSectionCard,
} from "./WorkspacePrimitives";

type Tone = "strong" | "adequate" | "weak" | "neutral";

const TONE_VAR: Record<Tone, string> = {
  strong: "var(--c-profit)",
  adequate: "var(--c-valuation)",
  weak: "var(--c-risk)",
  neutral: "var(--muted)",
};

function toneForStatus(status: string): Tone {
  if (status === "succeeded") return "strong";
  if (status === "degraded") return "adequate";
  if (status === "failed") return "weak";
  return "neutral";
}

/** Figma `DEEP DIVE` eyebrow above a section head. */
function DeepDiveEyebrow({ label, tone }: { label: string; tone?: Tone }) {
  return (
    <div className="mb-3 flex items-center gap-2 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.1em] text-[var(--muted)]">
      <span className="rounded bg-[var(--surface-2)] px-2 py-0.5">Deep dive</span>
      <span>{label}</span>
      {tone && tone !== "neutral" ? (
        <span
          className="ml-1 inline-block h-1.5 w-1.5 rounded-full"
          style={{ background: TONE_VAR[tone] }}
          aria-hidden="true"
        />
      ) : null}
    </div>
  );
}

/** Figma `Card` with coloured top border + big figure (S10 pair, S02 composite). */
function FigureCard({
  eyebrow,
  figure,
  badge,
  tone,
  children,
  className,
}: {
  eyebrow: string;
  figure: string;
  badge?: string;
  tone: Tone;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--card)] p-4",
        className,
      )}
      style={{ borderTop: `2px solid ${TONE_VAR[tone]}` }}
    >
      <p
        className="mb-2 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.07em]"
        style={{ color: TONE_VAR[tone] }}
      >
        {eyebrow}
      </p>
      <p
        className="mb-1.5 font-[family-name:var(--font-display)] text-[32px] font-bold leading-none"
        style={{ color: TONE_VAR[tone] }}
      >
        {figure}
      </p>
      {badge ? <Badge variant="outline">{badge}</Badge> : null}
      {children ? (
        <div className="mt-2.5 text-xs leading-relaxed text-[var(--muted)]">{children}</div>
      ) : null}
    </div>
  );
}

function StatusTile({ label, value, tone }: { label: string; value: string; tone: Tone }) {
  return (
    <div className="rounded-[var(--radius-md)] bg-[var(--surface-2)] px-3.5 py-3">
      <p className="mb-1.5 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.06em] text-[var(--muted)]">
        {label}
      </p>
      <p className="flex items-center gap-2 text-sm font-semibold text-[var(--fg)]">
        <span
          className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
          style={{ background: TONE_VAR[tone] }}
          aria-hidden="true"
        />
        {value === "Unavailable" ? "Data unavailable." : value}
      </p>
    </div>
  );
}

function trendsFor(
  financialStatements: FinancialStatementsPayload | null | undefined,
): FinancialTrendsView {
  return mapFinancialTrends(financialStatements);
}

/* ------------------------------------------------------------------ S07 */

export function EarningsQualitySection({
  view,
  financialStatements,
}: {
  view: ResearchView;
  financialStatements?: FinancialStatementsPayload | null;
}) {
  const eq = view.earnings;
  const trends = trendsFor(financialStatements);
  const tone = toneForStatus(eq.status);
  return (
    <div className="space-y-4">
      <DeepDiveEyebrow label="Earnings Quality" tone={tone} />
      <SectionCard
        title="Earnings Quality"
        description="Are reported earnings durable and supported by the underlying business? Values from the earnings_quality stage; margin trend is the provider-reported net margin from authenticated statements."
      >
        <div className="grid gap-3.5 md:grid-cols-2">
          <TrendChart
            series={trends.series.net_margin}
            eyebrow={`NET MARGIN TREND Â· % Â· ${
              trends.series.net_margin.available
                ? `${trends.series.net_margin.points[0]?.label}â€“${
                    trends.series.net_margin.points[trends.series.net_margin.points.length - 1]?.label
                  }`
                : "provider ratio"
            }`}
            footnote={trends.series.net_margin.source}
          />
          <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--card)] p-4">
            <p className="mb-2.5 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.07em] text-[var(--muted)]">
              Indicators
            </p>
            <dl>
              <FieldRow label="Earnings quality" value={eq.label} />
              <FieldRow
                label="Cash conversion"
                value={firstStageMetric(eq, ["Cash Conversion"])}
              />
              <FieldRow
                label="Earnings consistency"
                value={firstStageMetric(eq, ["Consistency", "Earnings Consistency"])}
              />
              <FieldRow
                label="Accounting quality"
                value={firstStageMetric(eq, ["Accounting Quality"])}
              />
              <FieldRow label="Score" value={eq.score} />
              <FieldRow label="Confidence" value={eq.confidence} />
            </dl>
          </div>
        </div>
      </SectionCard>
      <StageSectionCard title="Earnings quality stage detail" section={eq} />
    </div>
  );
}

/* ------------------------------------------------------------------ S08 */

export function GrowthQualitySection({
  view,
  financialStatements,
}: {
  view: ResearchView;
  financialStatements?: FinancialStatementsPayload | null;
}) {
  const growth = view.growth;
  const trends = trendsFor(financialStatements);
  const tone = toneForStatus(growth.status);
  return (
    <div className="space-y-4">
      <DeepDiveEyebrow label="Growth Quality" tone={tone} />
      <SectionCard
        title="Growth Quality"
        description="Is growth durable and self-funded? Values from the growth_quality stage. Revenue history is the authenticated statements line item â€” growth rates are not computed in the browser."
      >
        <div className="grid gap-3.5 md:grid-cols-2">
          <TrendChart
            series={trends.series.revenue}
            footnote={trends.series.revenue.source}
          />
          <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--card)] p-4">
            <p className="mb-2.5 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.07em] text-[var(--muted)]">
              Indicators
            </p>
            <dl>
              <FieldRow label="Growth quality" value={growth.label} />
              <FieldRow
                label="Revenue growth"
                value={firstStageMetric(growth, ["Revenue Growth"])}
              />
              <FieldRow
                label="Profit growth"
                value={firstStageMetric(growth, ["Profit Growth"])}
              />
              <FieldRow
                label="Reinvestment"
                value={firstStageMetric(growth, ["Reinvestment"])}
              />
              <FieldRow label="Score" value={growth.score} />
              <FieldRow label="Confidence" value={growth.confidence} />
            </dl>
          </div>
        </div>
      </SectionCard>
      <StageSectionCard title="Growth quality stage detail" section={growth} />
    </div>
  );
}

/* ------------------------------------------------------------------ S10 */

export function MarginOfSafetySection({ view }: { view: ResearchView }) {
  const mos = view.marginOfSafetyView;
  const bqTone: Tone = toneForStatus(view.businessQuality.status);
  const mosTone: Tone =
    mos.status === "discount" ? "strong" : mos.status === "premium" ? "weak" : "neutral";
  const bqFigure =
    view.businessQualityScore == null
      ? "Data unavailable."
      : `${view.businessQuality.score} / 100`;
  return (
    <div className="space-y-4">
      <DeepDiveEyebrow label="Margin of Safety" tone={mosTone} />
      <SectionCard
        title="Margin of Safety"
        description="Business quality and valuation are separate analytical questions. A high-quality business can still carry an unattractive valuation. Values are backend-authoritative (RS-005); nothing is recalculated here."
      >
        <div className="grid gap-3.5 md:grid-cols-2">
          <FigureCard
            eyebrow="Business quality"
            figure={bqFigure}
            badge={view.businessQualityLabel === "Unavailable" ? undefined : view.businessQualityLabel}
            tone={view.businessQualityScore == null ? "neutral" : bqTone}
          >
            {view.strengthsWeaknesses.strengths.length
              ? view.strengthsWeaknesses.strengths.slice(0, 2).join(" Â· ")
              : "Data unavailable."}
          </FigureCard>
          <FigureCard
            eyebrow="Margin of safety"
            figure={mos.display === "Unavailable" ? "Data unavailable." : mos.display}
            badge={mos.classification === "Unavailable" ? undefined : mos.classification}
            tone={mosTone}
          >
            {mos.reasoning ??
              (mos.status === "unavailable"
                ? "No authenticated intrinsic value â€” margin of safety was not calculated."
                : null)}
          </FigureCard>
        </div>
        <dl className="mt-4">
          <FieldRow label="Current market price" value={mos.currentPrice} />
          <FieldRow label="DSP intrinsic value" value={mos.intrinsicValue} />
          <FieldRow label="Premium / discount to value" value={mos.premiumDiscount} />
          <FieldRow label="Valuation confidence" value={mos.valuationConfidence} />
          <FieldRow label="Valuation status" value={view.valuation.method} />
        </dl>
      </SectionCard>
    </div>
  );
}

/* ------------------------------------------------------------------ S12 */

function FactorList({
  eyebrow,
  items,
  tone,
  sign,
}: {
  eyebrow: string;
  items: string[];
  tone: Tone;
  sign: "+" | "âˆ’";
}) {
  return (
    <div
      className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--card)] p-4"
      style={{ borderTop: `2px solid ${TONE_VAR[tone]}` }}
    >
      <p
        className="mb-3 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.08em]"
        style={{ color: TONE_VAR[tone] }}
      >
        {eyebrow}
      </p>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
      ) : (
        <ul className="space-y-2.5">
          {items.map((item) => (
            <li key={item} className="flex gap-2 text-[13px] leading-[1.55] text-[var(--fg)]">
              <span
                className="mt-px shrink-0 font-[family-name:var(--font-mono)] text-xs"
                style={{ color: TONE_VAR[tone] }}
                aria-hidden="true"
              >
                {sign}
              </span>
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function StrengthsWeaknessesSection({ view }: { view: ResearchView }) {
  const sw = view.strengthsWeaknesses;
  return (
    <div className="space-y-4">
      <DeepDiveEyebrow label="Strengths & Weaknesses" />
      <SectionCard
        title="Strengths & Weaknesses"
        description="Factors published by the recommendation engine (positive / negative factors) and the Business Quality aggregator. Not AI-generated in the browser; nothing is authored client-side."
      >
        <div className="grid gap-3.5 md:grid-cols-2">
          <FactorList eyebrow="Key strengths" items={sw.strengths} tone="strong" sign="+" />
          <FactorList eyebrow="Key weaknesses" items={sw.weaknesses} tone="weak" sign="âˆ’" />
        </div>
        <p className="mt-3 font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">
          Source:{" "}
          {sw.sources.length ? sw.sources.join(" Â· ") : "Data unavailable."}
        </p>
      </SectionCard>
    </div>
  );
}

/* ------------------------------------------------------------------ S13 */

function toneForRisk(level: string): Tone {
  const l = level.toLowerCase();
  if (l === "unavailable" || l === "data unavailable.") return "neutral";
  if (l.includes("low")) return "strong";
  if (l.includes("high") || l.includes("severe")) return "weak";
  return "adequate";
}

export function InvestmentContextSection({ view }: { view: ResearchView }) {
  const ctx = view.investmentContext;
  const mosTone: Tone =
    view.marginOfSafetyView.status === "discount"
      ? "strong"
      : view.marginOfSafetyView.status === "premium"
        ? "weak"
        : "neutral";
  return (
    <div className="space-y-4">
      <DeepDiveEyebrow label="Investment Context" />
      <SectionCard
        title="Investment Context"
        description="Backend-authoritative DSP analytical context. This is not an independent frontend recommendation."
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <StatusTile
            label="Business quality"
            value={ctx.businessQuality}
            tone={view.businessQualityScore == null ? "neutral" : toneForStatus(view.businessQuality.status)}
          />
          <StatusTile label="Valuation" value={ctx.valuation} tone={mosTone} />
          <StatusTile label="Margin of safety" value={ctx.marginOfSafety} tone={mosTone} />
          <StatusTile label="Risk level" value={ctx.riskLevel} tone={toneForRisk(ctx.riskLevel)} />
          <StatusTile
            label="Confidence"
            value={ctx.confidence}
            tone={ctx.confidence === "Unavailable" ? "neutral" : "adequate"}
          />
        </div>
        <dl className="mt-4">
          <FieldRow label="Recommendation" value={view.recommendation} />
          <FieldRow label="Committee decision" value={view.committeeDecision} />
          <FieldRow label="Decision summary" value={ctx.decisionSummary} />
        </dl>
        {ctx.keyDrivers.length ? (
          <div className="mt-3">
            <p className="mb-1.5 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.07em] text-[var(--muted)]">
              Key drivers
            </p>
            <ul className="list-disc space-y-1 pl-4 text-sm">
              {ctx.keyDrivers.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <p className="mt-3 text-[11px] text-[var(--muted)]">
          Research Mode â€” educational investigation, not personalised investment advice.
        </p>
      </SectionCard>
    </div>
  );
}
