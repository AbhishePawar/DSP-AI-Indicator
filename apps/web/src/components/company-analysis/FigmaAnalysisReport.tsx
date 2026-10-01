"use client";

/**
 * Figma Make `CompanyAnalysis.tsx` presentation.
 *
 * Long-scroll report (company header, TOC, S01–S14, Ask DSP drawer).
 * Every figure comes from the authenticated analyse / quote / statements
 * payloads already loaded by CompanyAnalysisWorkspace. Missing fields render
 * "Data unavailable." — the Figma TCS demo series is not used.
 */

import { lazy, Suspense, useEffect, useRef, useState, type ComponentType } from "react";

import type {
  AnalyseRequest,
  AnalyseResponse,
  RiskCategoryPayload,
} from "@/lib/api/compositionTypes";
import {
  formatTrendValue,
  mapFinancialTrends,
  type FinancialTrendSeries,
} from "@/lib/company-analysis";
import type {
  FinancialStatementsPayload,
  MarketQuotePayload,
} from "@/lib/institutional-dashboard/mapInstitutionalDashboard";
import { money } from "@/lib/research/mapResearchView";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { cn } from "@/lib/utils";
import { TrendChart } from "./TrendChart";
import { AiCopilotSection } from "./sections/AiCopilotSection";
import { DocumentsSection } from "./sections/DocumentsSection";
import { ExportSection } from "./WorkspaceSections";

type Tone = "strong" | "adequate" | "weak" | "unavailable";

const UNAVAILABLE = "Data unavailable.";

const TOC = [
  {
    label: "ANALYSIS",
    items: [
      { id: "s01", label: "Summary" },
      { id: "s03", label: "Buffett Assessment" },
      { id: "s04", label: "Financials" },
      { id: "s09", label: "Valuation" },
      { id: "s02", label: "Business Quality" },
      { id: "s11", label: "Key Risks" },
    ],
  },
  {
    label: "DEEP DIVE",
    items: [
      { id: "s06", label: "Management" },
      { id: "s07", label: "Earnings Quality" },
      { id: "s08", label: "Growth Quality" },
      { id: "s10", label: "Margin of Safety" },
      { id: "s12", label: "Strengths & Weaknesses" },
      { id: "s13", label: "Investment Context" },
      { id: "s14", label: "Evidence" },
    ],
  },
] as const;

const DOMAIN_COLOR: Record<string, string> = {
  economic_moat: "var(--c-dsp)",
  management_quality: "var(--c-revenue)",
  financial_strength: "var(--c-profit)",
  earnings_quality: "var(--c-cashflow)",
  growth_quality: "var(--c-valuation)",
};

const EXTRA_SECTIONS: ReadonlyArray<{
  id: string;
  label: string;
  Section: ComponentType<{ view: ResearchView }>;
}> = [
  {
    id: "ownership",
    label: "Ownership",
    Section: lazy(() =>
      import("./sections/OwnershipSection").then((m) => ({ default: m.OwnershipSection })),
    ),
  },
  {
    id: "peers",
    label: "Peers",
    Section: lazy(() =>
      import("./sections/PeersSection").then((m) => ({ default: m.PeersSection })),
    ),
  },
  {
    id: "news",
    label: "News",
    Section: lazy(() =>
      import("./sections/NewsSection").then((m) => ({ default: m.NewsSection })),
    ),
  },
  {
    id: "research",
    label: "Official research",
    Section: lazy(() =>
      import("./WorkspaceSections").then((m) => ({ default: m.ResearchSection })),
    ),
  },
  {
    id: "compliance",
    label: "Compliance",
    Section: lazy(() =>
      import("./WorkspaceSections").then((m) => ({ default: m.ComplianceSection })),
    ),
  },
  {
    id: "timeline",
    label: "Timeline",
    Section: lazy(() =>
      import("./WorkspaceSections").then((m) => ({ default: m.TimelineSection })),
    ),
  },
  {
    id: "explainability",
    label: "Explainability",
    Section: lazy(() =>
      import("./FlagshipSections").then((m) => ({ default: m.ExplainabilitySection })),
    ),
  },
  {
    id: "advancedCheck",
    label: "Advanced check",
    Section: lazy(() =>
      import("./WorkspaceSections").then((m) => ({ default: m.AdvancedCheckSection })),
    ),
  },
];

const LOADING_STEPS = [
  "Identifying company",
  "Collecting financial evidence",
  "Analysing business quality",
  "Evaluating economic moat",
  "Evaluating management",
  "Analysing earnings & growth",
  "Evaluating valuation",
  "Assessing risks",
  "Validating research",
  "Preparing analysis report",
];

function formatAnalysisDate(value: string | null): string {
  if (!value) return UNAVAILABLE;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return present(value);
  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function present(value: string | null | undefined): string {
  const text = (value ?? "").trim();
  if (!text || text === "—" || text === "-" || text === "Unavailable" || text === "UNKNOWN") {
    return UNAVAILABLE;
  }
  return text;
}

function toneFor(value: string | null | undefined): Tone {
  const t = present(value).toLowerCase();
  if (t === UNAVAILABLE.toLowerCase()) return "unavailable";
  if (/\b(strong|high quality|high|met)\b/.test(t)) return "strong";
  if (/\b(weak|negative|premium|not met|failed|low)\b/.test(t)) return "weak";
  if (/\b(adequate|moderate|medium|watch)\b/.test(t)) return "adequate";
  return "unavailable";
}

function toneColor(tone: Tone): string {
  if (tone === "strong") return "var(--c-profit)";
  if (tone === "adequate") return "var(--c-revenue)";
  if (tone === "weak") return "var(--c-risk)";
  return "var(--muted)";
}

function finite(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function ratioPct(value: number | null): string {
  if (value == null) return UNAVAILABLE;
  return `${(value * 100).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
}

function multiple(value: number | null): string {
  if (value == null) return UNAVAILABLE;
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}×`;
}

function compactMoney(value: number | null, currency: string | null): string {
  if (value == null) return UNAVAILABLE;
  const formatted = Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
  return currency ? `${currency} ${formatted}` : formatted;
}

function latestRatio(
  statements: FinancialStatementsPayload | null | undefined,
  keys: string[],
): number | null {
  if (!statements?.available || !statements.authenticated) return null;
  const periods = [...(statements.periods ?? [])].sort((a, b) =>
    b.period_end.localeCompare(a.period_end),
  );
  for (const period of periods) {
    for (const key of keys) {
      const value = finite(period.ratios?.[key]);
      if (value != null) return value;
    }
  }
  return null;
}

function quoteCurrency(quote: MarketQuotePayload | null | undefined): string | null {
  const code = quote?.currency?.trim().toUpperCase();
  return code && /^[A-Z]{3}$/.test(code) ? code : null;
}

function quoteFields(quote: MarketQuotePayload | null | undefined) {
  if (!quote?.available || !quote.authenticated) return null;
  return quote.fields ?? null;
}

function dailyChangeLabel(
  current: number | null,
  previous: number | null,
  change: number | null,
  changePercent: number | null,
): { text: string; down: boolean } | null {
  if (change != null && changePercent != null) {
    const sign = change > 0 ? "+" : "";
    return {
      text: `${sign}${change.toLocaleString(undefined, { maximumFractionDigits: 2 })} (${sign}${changePercent.toLocaleString(undefined, { maximumFractionDigits: 2 })}%)`,
      down: change < 0,
    };
  }
  if (current == null || previous == null || previous === 0) return null;
  const delta = current - previous;
  const pct = (delta / previous) * 100;
  const sign = delta > 0 ? "+" : "";
  return {
    text: `${sign}${delta.toLocaleString(undefined, { maximumFractionDigits: 2 })} (${sign}${pct.toLocaleString(undefined, { maximumFractionDigits: 2 })}%)`,
    down: delta < 0,
  };
}

function lastValued(series: FinancialTrendSeries): string {
  const point = [...series.points].reverse().find((p) => p.value != null);
  return point ? formatTrendValue(series, point.value) : UNAVAILABLE;
}

function StatusBadge({ text }: { text: string }) {
  const tone = toneFor(text);
  const color = toneColor(tone);
  return (
    <span
      className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 font-[family-name:var(--font-mono)] text-[11px] tracking-wide"
      style={{
        color,
        background: `color-mix(in srgb, ${color} 12%, transparent)`,
        border: `1px solid color-mix(in srgb, ${color} 28%, transparent)`,
      }}
    >
      <span className="size-1.5 rounded-full" style={{ background: color }} aria-hidden />
      {present(text)}
    </span>
  );
}

function SectionHead({
  id,
  num,
  title,
  status,
  subtitle,
}: {
  id: string;
  num: string;
  title: string;
  status?: string;
  subtitle?: string;
}) {
  return (
    <div id={id} className="mb-5 scroll-mt-4">
      <div className="mb-1 flex flex-wrap items-center gap-2.5">
        {num ? (
          <span className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.1em] text-[var(--muted)]">
            {num}
          </span>
        ) : null}
        <h2 className="m-0 font-[family-name:var(--font-display)] text-xl font-medium tracking-tight text-[var(--fg)]">
          {title}
        </h2>
        {status ? <StatusBadge text={status} /> : null}
      </div>
      {subtitle ? (
        <p className="m-0 text-[13px] leading-relaxed text-[var(--muted)]">{subtitle}</p>
      ) : null}
    </div>
  );
}

function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-[var(--border)] bg-[var(--card)] px-[22px] py-5",
        className,
      )}
    >
      {children}
    </div>
  );
}

function AskButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="whitespace-nowrap rounded-full border border-[var(--border)] bg-transparent px-3 py-1 text-xs text-[var(--muted)] hover:border-[color-mix(in_srgb,var(--c-dsp)_50%,transparent)] hover:text-[var(--fg)]"
    >
      {label}
    </button>
  );
}

function DeepDiveLabel({ title, status }: { title: string; status?: string }) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.1em] text-[var(--muted)]">
      <span className="rounded bg-[var(--surface-2)] px-2 py-0.5">DEEP DIVE</span>
      <span>{title}</span>
      {status ? <StatusBadge text={status} /> : null}
    </div>
  );
}

function BulletList({
  title,
  items,
  tone,
  marker,
}: {
  title: string;
  items: string[];
  tone: "strong" | "weak";
  marker: string;
}) {
  const color = tone === "strong" ? "var(--c-profit)" : "var(--c-risk)";
  return (
    <div
      className="rounded-[10px] p-4"
      style={{
        background: `color-mix(in srgb, ${color} 6%, transparent)`,
        border: `1px solid color-mix(in srgb, ${color} 18%, transparent)`,
      }}
    >
      <div
        className="mb-2.5 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.08em]"
        style={{ color }}
      >
        {title}
      </div>
      {items.length === 0 ? (
        <p className="m-0 text-xs text-[var(--muted)]">{UNAVAILABLE}</p>
      ) : (
        items.slice(0, 3).map((item) => (
          <div key={item} className="mb-2 flex gap-2 text-xs leading-snug text-[var(--fg)]">
            <span style={{ color }}>{marker}</span>
            <span>{item}</span>
          </div>
        ))
      )}
    </div>
  );
}

export function AnalysisPending() {
  return (
    <div className="relative min-h-[28rem] flex-1">
      <div className="pointer-events-none absolute inset-0 opacity-35" aria-hidden>
        <div className="space-y-4 p-7">
          <div className="h-3 w-32 animate-pulse rounded bg-[var(--surface-2)]" />
          <div className="h-7 w-72 animate-pulse rounded bg-[var(--surface-2)]" />
          <div className="h-24 animate-pulse rounded-xl bg-[var(--surface-2)]" />
          <div className="h-40 animate-pulse rounded-xl bg-[var(--surface-2)]" />
        </div>
      </div>
      <div className="absolute inset-0 z-10 flex items-center justify-center bg-[color-mix(in_srgb,var(--bg)_72%,transparent)] backdrop-blur-sm">
        <ol className="w-[min(100%,22rem)] space-y-2 rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
          {LOADING_STEPS.map((step, index) => (
            <li
              key={step}
              className="flex items-center gap-2 text-[13px] text-[var(--muted)]"
              aria-current={index === 0 ? "step" : undefined}
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  index === 0 ? "animate-pulse bg-[var(--c-dsp)]" : "bg-[var(--border)]",
                )}
              />
              {step}
            </li>
          ))}
          <p className="pt-2 text-[11px] text-[var(--muted)]">
            Waiting for the DSP analysis response. Steps stay incomplete until that response arrives.
          </p>
        </ol>
      </div>
    </div>
  );
}

export function AnalysisModeChooser({
  companyLabel,
  onSimple,
  onBuffett,
  blockedReason,
}: {
  companyLabel: string;
  onSimple: () => void;
  onBuffett: () => void;
  blockedReason?: string | null;
}) {
  const blocked = Boolean(blockedReason);
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-10">
      <p className="mb-2.5 font-[family-name:var(--font-mono)] text-xs tracking-[0.08em] text-[var(--muted)]">
        COMPANY ANALYSIS
      </p>
      <h1 className="m-0 text-center font-[family-name:var(--font-display)] text-[clamp(24px,4vw,36px)] font-medium tracking-tight text-[var(--fg)]">
        {companyLabel || "Select a company"}
      </h1>
      <p className="mb-12 mt-2 text-center text-sm text-[var(--muted)]">
        Choose your research depth
      </p>
      {blockedReason ? (
        <p className="mb-6 max-w-md text-center text-sm text-[var(--muted)]">{blockedReason}</p>
      ) : null}
      <div className="grid w-full max-w-[660px] gap-4 sm:grid-cols-2">
        <button
          type="button"
          disabled={blocked}
          onClick={onSimple}
          className="rounded-[14px] border border-[var(--border)] bg-[var(--card)] px-7 py-7 text-left transition hover:border-[color-mix(in_srgb,var(--c-revenue)_50%,transparent)] hover:shadow-[0_8px_24px_rgba(0,0,0,0.2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          <div className="mb-3 text-[22px] text-[var(--c-revenue)]" aria-hidden>
            ◈
          </div>
          <div className="mb-2 font-[family-name:var(--font-display)] text-[17px] font-medium text-[var(--fg)]">
            Simple Research
          </div>
          <p className="mb-5 text-[13px] leading-relaxed text-[var(--muted)]">
            A concise investigation — key metrics, financial summary, strengths, risks, and valuation context from the same DSP analysis.
          </p>
          <span className="inline-block rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-2 text-[13px] text-[var(--c-revenue)]">
            Research →
          </span>
        </button>
        <button
          type="button"
          disabled={blocked}
          onClick={onBuffett}
          className="rounded-[14px] border border-[color-mix(in_srgb,var(--c-dsp)_35%,transparent)] bg-[var(--card)] px-7 py-7 text-left shadow-[0_0_0_1px_rgba(124,106,247,0.08)] transition hover:border-[color-mix(in_srgb,var(--c-dsp)_70%,transparent)] hover:shadow-[0_8px_32px_rgba(124,106,247,0.18)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          <div className="mb-3 flex items-center gap-2">
            <span
              aria-hidden
              className="flex size-[22px] items-center justify-center rounded-md bg-[linear-gradient(135deg,#7c6af7,#2dd4bf)] text-[10px] font-bold text-white"
            >
              D
            </span>
            <span className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.08em] text-[var(--c-dsp)]">
              FLAGSHIP
            </span>
          </div>
          <div className="mb-2 font-[family-name:var(--font-display)] text-[17px] font-medium text-[var(--fg)]">
            DSP Buffett Indicator Analysis
          </div>
          <p className="mb-5 text-[13px] leading-relaxed text-[var(--muted)]">
            The full evidence-driven report — business quality, economic moat, management, earnings, growth, valuation, and margin of safety.
          </p>
          <span className="inline-block rounded-lg bg-[var(--c-dsp)] px-4 py-2 text-[13px] text-white">
            Analyse →
          </span>
        </button>
      </div>
    </div>
  );
}

export function SimpleResearchSummary({
  view,
  marketQuote,
  financialStatements,
  onUpgrade,
}: {
  view: ResearchView;
  marketQuote: MarketQuotePayload | null;
  financialStatements: FinancialStatementsPayload | null;
  onUpgrade: () => void;
}) {
  const fields = quoteFields(marketQuote);
  const currency = view.currency || quoteCurrency(marketQuote);
  const price = finite(fields?.current_price);
  const change = dailyChangeLabel(
    price,
    finite(fields?.previous_close),
    finite(fields?.change),
    finite(fields?.change_percent),
  );
  const roe = latestRatio(financialStatements, ["roe", "return_on_equity"]);
  const roce = latestRatio(financialStatements, ["roce", "return_on_capital_employed"]);
  const debtEquity = latestRatio(financialStatements, ["debt_to_equity", "debt_equity"]);
  const pe = latestRatio(financialStatements, ["pe", "pe_ratio", "price_to_earnings"]);
  const trends = mapFinancialTrends(financialStatements);
  const strengths =
    view.strengthsWeaknesses.strengths.length > 0
      ? view.strengthsWeaknesses.strengths
      : view.strengths;
  const risks = riskRows(view);
  const metrics = [
    { label: "ROE", value: ratioPct(roe), color: "var(--c-profit)" },
    { label: "ROCE", value: ratioPct(roce), color: "var(--c-profit)" },
    { label: "Revenue", value: lastValued(trends.series.revenue), color: "var(--c-revenue)" },
    { label: "Net Profit", value: lastValued(trends.series.net_income), color: "var(--c-cashflow)" },
    { label: "D/E", value: multiple(debtEquity), color: "var(--muted)" },
    { label: "PE Ratio", value: multiple(pe), color: "var(--c-valuation)" },
  ];
  const valuation = [
    { label: "Market Price", value: price == null ? UNAVAILABLE : money(price, currency), color: "var(--fg)" },
    { label: "Intrinsic Value", value: present(view.marginOfSafetyView.intrinsicValue), color: "var(--c-cashflow)" },
    { label: "Margin of Safety", value: present(view.marginOfSafetyView.display), color: toneColor(toneFor(view.marginOfSafetyView.classification)) },
  ];

  return (
    <div className="px-4 py-7 sm:px-7">
      <p className="mb-1.5 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.1em] text-[var(--muted)]">
        SIMPLE RESEARCH
      </p>
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="m-0 font-[family-name:var(--font-display)] text-[28px] font-medium text-[var(--fg)]">
          {present(view.company)}
        </h1>
        <StatusBadge text={present(view.businessQualityLabel)} />
      </div>
      <div className="mt-2.5 flex flex-wrap gap-4 font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
        <span>
          {present(view.exchange)}: {view.ticker}
        </span>
        <span className="text-[var(--c-revenue)]">
          {price == null ? UNAVAILABLE : money(price, currency)}
        </span>
        {change ? (
          <span style={{ color: change.down ? "var(--c-risk)" : "var(--c-profit)" }}>{change.text}</span>
        ) : null}
      </div>

      <div className="mt-6 grid gap-4">
        <Card>
          <div className="mb-3.5 font-[family-name:var(--font-mono)] text-[11px] tracking-[0.08em] text-[var(--muted)]">
            KEY METRICS
          </div>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(130px,1fr))] gap-3">
            {metrics.map((metric) => (
              <div key={metric.label} className="rounded-lg bg-[var(--surface-2)] px-3.5 py-3">
                <div className="mb-1.5 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
                  {metric.label}
                </div>
                <div
                  className="font-[family-name:var(--font-mono)] text-base font-semibold"
                  style={{ color: metric.value === UNAVAILABLE ? "var(--muted)" : metric.color }}
                >
                  {metric.value}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <div className="grid gap-4 md:grid-cols-2">
          <BulletList title="KEY STRENGTHS" items={strengths.slice(0, 3)} tone="strong" marker="+" />
          <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
            <div className="mb-3 font-[family-name:var(--font-mono)] text-[11px] tracking-[0.08em] text-[var(--c-risk)]">
              KEY RISKS
            </div>
            {risks.length === 0 ? (
              <p className="m-0 text-xs text-[var(--muted)]">{UNAVAILABLE}</p>
            ) : (
              risks.slice(0, 3).map((risk) => (
                <div key={risk.name} className="mb-2.5">
                  <div className="text-[13px] font-medium text-[var(--fg)]">{risk.name}</div>
                  <div className="text-xs leading-relaxed text-[var(--muted)]">{risk.evidence}</div>
                </div>
              ))
            )}
          </div>
        </div>

        <Card>
          <div className="mb-3.5 font-[family-name:var(--font-mono)] text-[11px] tracking-[0.08em] text-[var(--muted)]">
            VALUATION SUMMARY
          </div>
          <div className="mb-3 flex flex-wrap gap-6">
            {valuation.map((item) => (
              <div key={item.label}>
                <div className="mb-1 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
                  {item.label}
                </div>
                <div
                  className="font-[family-name:var(--font-mono)] text-xl font-semibold"
                  style={{ color: item.value === UNAVAILABLE ? "var(--muted)" : item.color }}
                >
                  {item.value}
                </div>
              </div>
            ))}
          </div>
          <p className="m-0 text-[13px] leading-relaxed text-[var(--muted)]">
            {present(view.investmentContext.decisionSummary)}
          </p>
        </Card>

        <div className="rounded-xl border border-[color-mix(in_srgb,var(--c-dsp)_30%,transparent)] bg-[color-mix(in_srgb,var(--c-dsp)_4%,transparent)] px-5 py-5">
          <div className="mb-1.5 font-[family-name:var(--font-display)] text-[15px] text-[var(--fg)]">
            Want the complete analysis?
          </div>
          <p className="mb-3.5 text-[13px] leading-relaxed text-[var(--muted)]">
            Open the full DSP Buffett Indicator Analysis — the same research, with economic moat, earnings quality, management, intrinsic value, evidence, and follow-up questions.
          </p>
          <button
            type="button"
            onClick={onUpgrade}
            className="rounded-lg bg-[var(--c-dsp)] px-5 py-2 text-[13px] text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Run DSP Buffett Indicator Analysis →
          </button>
        </div>
      </div>
    </div>
  );
}

export function AnalysisEmpty({
  symbol,
  description,
  onAnalyze,
}: {
  symbol: string;
  description: string;
  onAnalyze?: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
      <p className="font-[family-name:var(--font-mono)] text-xs tracking-[0.08em] text-[var(--muted)]">
        COMPANY ANALYSIS
      </p>
      <h1 className="m-0 font-[family-name:var(--font-display)] text-3xl font-medium tracking-tight text-[var(--fg)]">
        {symbol || "No company selected"}
      </h1>
      <p className="m-0 max-w-md text-sm text-[var(--muted)]">{description}</p>
      {onAnalyze && symbol ? (
        <button
          type="button"
          onClick={onAnalyze}
          className="rounded-lg bg-[var(--c-dsp)] px-5 py-2 text-[13px] text-white"
        >
          Analyse {symbol}
        </button>
      ) : null}
    </div>
  );
}

export function FigmaAnalysisReport({
  view,
  marketQuote,
  financialStatements,
  analyseRequest,
  analyseResponse,
}: {
  view: ResearchView;
  marketQuote: MarketQuotePayload | null;
  financialStatements: FinancialStatementsPayload | null;
  analyseRequest: AnalyseRequest | null;
  analyseResponse: AnalyseResponse | null;
}) {
  const [activeSection, setActiveSection] = useState("s01");
  const [tocOpen, setTocOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatSeed, setChatSeed] = useState<string | null>(null);
  const [documentsOpen, setDocumentsOpen] = useState(false);
  const [extraSection, setExtraSection] = useState<string | null>(null);
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});

  const trends = mapFinancialTrends(financialStatements);
  const fields = quoteFields(marketQuote);
  const currency = view.currency || quoteCurrency(marketQuote);
  const price = finite(fields?.current_price);
  const change = dailyChangeLabel(
    price,
    finite(fields?.previous_close),
    finite(fields?.change),
    finite(fields?.change_percent),
  );
  const weekHigh = finite(fields?.week_52_high);
  const weekLow = finite(fields?.week_52_low);
  const roe = latestRatio(financialStatements, ["roe", "return_on_equity"]);
  const roce = latestRatio(financialStatements, ["roce", "return_on_capital_employed"]);
  const debtEquity = latestRatio(financialStatements, ["debt_to_equity", "debt_equity"]);
  const ebitda = latestRatio(financialStatements, ["ebitda_margin"]);
  const eps = latestRatio(financialStatements, ["eps", "earnings_per_share"]);
  const pe = latestRatio(financialStatements, ["pe", "pe_ratio", "price_to_earnings"]);

  const qualityLabel = present(view.businessQualityLabel);
  const qualityScore = present(view.businessQuality.score);
  const thesis =
    present(view.investmentContext.decisionSummary) === UNAVAILABLE
      ? present(view.buffett.verdict)
      : present(view.investmentContext.decisionSummary);
  const strengths =
    view.strengthsWeaknesses.strengths.length > 0
      ? view.strengthsWeaknesses.strengths
      : view.strengths;
  const weaknesses =
    view.strengthsWeaknesses.weaknesses.length > 0
      ? view.strengthsWeaknesses.weaknesses
      : view.risks;
  const buffettRows =
    view.buffett.scorecard.length > 0
      ? view.buffett.scorecard.map((row) => ({
          dim: row.dimension,
          result: present(row.grade || row.evidence),
          status: present(row.grade),
        }))
      : view.buffett.decisionMatrix.map((row) => ({
          dim: row.criterion,
          result: present(row.evidence),
          status: row.state === "met" ? "Met" : row.state === "not_met" ? "Not met" : UNAVAILABLE,
        }));

  const headerMetrics = [
    { label: "Market Cap", value: compactMoney(finite(fields?.market_cap), currency) },
    { label: "Sector", value: UNAVAILABLE },
    { label: "ROE", value: ratioPct(roe) },
    { label: "D/E", value: multiple(debtEquity) },
    { label: "PE", value: multiple(pe) },
    {
      label: "52W Range",
      value:
        weekLow != null && weekHigh != null
          ? `${money(weekLow, currency)} – ${money(weekHigh, currency)}`
          : UNAVAILABLE,
    },
    {
      label: "Analysis date",
      value: formatAnalysisDate(view.analysedAt),
    },
  ];

  const financialTiles = [
    { label: "Revenue", value: lastValued(trends.series.revenue), color: "var(--c-revenue)" },
    { label: "Net Profit", value: lastValued(trends.series.net_income), color: "var(--c-profit)" },
    { label: "ROE", value: ratioPct(roe), color: "var(--c-profit)" },
    { label: "ROCE", value: ratioPct(roce), color: "var(--c-profit)" },
    { label: "EBITDA Margin", value: ratioPct(ebitda), color: "var(--c-cashflow)" },
    { label: "D/E Ratio", value: multiple(debtEquity), color: "var(--muted)" },
    { label: "EPS", value: eps == null ? UNAVAILABLE : money(eps, currency), color: "var(--c-valuation)" },
    {
      label: "Free Cash Flow",
      value: lastValued(trends.series.free_cash_flow),
      color: "var(--c-cashflow)",
    },
  ];

  const riskCards = riskRows(view);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActiveSection(entry.target.id);
        }
      },
      { rootMargin: "-30% 0px -60% 0px", threshold: 0 },
    );
    for (const el of Object.values(sectionRefs.current)) {
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [documentsOpen]);

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setTocOpen(false);
  }

  function askAbout(ctx: string) {
    setChatSeed(ctx);
    setChatOpen(true);
  }

  function bind(id: string) {
    return (el: HTMLElement | null) => {
      sectionRefs.current[id] = el;
    };
  }

  return (
    <div className="relative flex min-h-[70vh] flex-col">
      <header className="shrink-0 border-b border-[var(--border)] bg-[var(--card)] px-4 py-4 sm:px-7">
        <div className="mb-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="mb-1 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.1em] text-[var(--muted)]">
              DSP BUFFETT INDICATOR ANALYSIS
            </p>
            <div className="flex flex-wrap items-baseline gap-2.5">
              <h1 className="m-0 font-[family-name:var(--font-display)] text-2xl font-medium tracking-tight text-[var(--fg)] sm:text-[28px]">
                {present(view.company)}
              </h1>
              <span className="font-[family-name:var(--font-mono)] text-[13px] text-[var(--muted)]">
                {view.ticker} · {present(view.exchange)}
              </span>
              <StatusBadge text={qualityLabel} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-[family-name:var(--font-mono)] text-[22px] font-bold text-[var(--fg)]">
              {price == null ? UNAVAILABLE : money(price, currency)}
            </span>
            {change ? (
              <span
                className="rounded px-1.5 py-0.5 font-[family-name:var(--font-mono)] text-xs"
                style={{
                  color: change.down ? "var(--c-risk)" : "var(--c-profit)",
                  background: change.down
                    ? "color-mix(in srgb, var(--c-risk) 12%, transparent)"
                    : "color-mix(in srgb, var(--c-profit) 12%, transparent)",
                }}
              >
                {change.text}
              </span>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap border-t border-[var(--border)] pt-3">
          {headerMetrics.map((metric, index) => (
            <div
              key={metric.label}
              className={cn("mb-1 pr-5", index > 0 && "border-l border-[var(--border)] pl-5")}
            >
              <div className="mb-0.5 font-[family-name:var(--font-mono)] text-[9px] tracking-[0.08em] text-[var(--muted)]">
                {metric.label.toUpperCase()}
              </div>
              <div className="font-[family-name:var(--font-mono)] text-xs font-medium text-[var(--fg)]">
                {metric.value}
              </div>
            </div>
          ))}
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <nav
          className="sticky top-0 hidden h-[calc(100vh-8rem)] w-[200px] shrink-0 flex-col overflow-auto border-r border-[var(--border)] py-4 md:flex"
          aria-label="Analysis sections"
        >
          {TOC.map((group) => (
            <div key={group.label} className="mb-2">
              <div className="px-4 pb-2 font-[family-name:var(--font-mono)] text-[9px] tracking-[0.12em] text-[var(--muted)]">
                {group.label}
              </div>
              {group.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => scrollTo(item.id)}
                  className="w-full border-l-2 px-4 py-1.5 text-left text-xs"
                  style={{
                    borderColor: activeSection === item.id ? "var(--c-dsp)" : "transparent",
                    background: activeSection === item.id ? "var(--surface-2)" : "transparent",
                    color: activeSection === item.id ? "var(--fg)" : "var(--muted)",
                  }}
                >
                  {item.label}
                </button>
              ))}
              <div className="mx-4 my-2 h-px bg-[var(--border)]" />
            </div>
          ))}
          <div className="px-4 pb-2 font-[family-name:var(--font-mono)] text-[9px] tracking-[0.12em] text-[var(--muted)]">
            TOOLS
          </div>
          <button
            type="button"
            onClick={() => setChatOpen(true)}
            className="mx-2.5 mb-1.5 flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs"
            style={{
              background: chatOpen ? "var(--c-dsp)" : "var(--surface-2)",
              borderColor: chatOpen ? "var(--c-dsp)" : "var(--border)",
              color: chatOpen ? "#fff" : "var(--muted)",
            }}
          >
            Ask DSP
          </button>
          <button
            type="button"
            onClick={() => scrollTo("export")}
            className="mx-2.5 mb-1.5 rounded-lg border border-[var(--border)] px-3 py-2 text-left text-xs text-[var(--muted)]"
          >
            Export
          </button>
          <button
            type="button"
            onClick={() => {
              setDocumentsOpen(true);
              scrollTo("documents");
            }}
            className="mx-2.5 rounded-lg border border-[var(--border)] px-3 py-2 text-left text-xs text-[var(--muted)]"
          >
            Documents
          </button>
        </nav>

        <div className="min-w-0 flex-1 px-4 py-7 sm:px-7" style={{ paddingBottom: chatOpen ? 280 : 72 }}>
          <section ref={bind("s01")} className="mb-9">
            <div className="overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--card)]">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--c-dsp)_6%,transparent)] px-5 py-4">
                <span className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.1em] text-[var(--muted)]">
                  01 — ANALYSIS SUMMARY
                </span>
                <div className="flex flex-wrap gap-2">
                  <StatusBadge text={qualityLabel} />
                  <StatusBadge text={present(view.marginOfSafetyView.classification)} />
                </div>
              </div>
              <div className="px-5 py-5">
                <h2 className="sr-only">Summary</h2>
                <p className="mb-4 font-[family-name:var(--font-display)] text-base leading-relaxed text-[var(--fg)]">
                  {thesis}
                </p>
                <p className="mb-4 text-xs text-[var(--muted)]">{view.buffett.disclaimer}</p>
                <div className="mb-5 grid gap-3 sm:grid-cols-3">
                  {[
                    {
                      label: "Business Quality",
                      value: qualityScore,
                      sub: qualityLabel,
                      color: toneColor(toneFor(qualityLabel)),
                    },
                    {
                      label: "Valuation",
                      value: present(view.marginOfSafetyView.display),
                      sub: present(view.marginOfSafetyView.classification),
                      color: toneColor(toneFor(view.marginOfSafetyView.classification)),
                    },
                    {
                      label: "Intrinsic Value",
                      value: present(view.valuation.intrinsicValue),
                      sub: `vs price ${present(view.valuation.currentPrice)}`,
                      color: "var(--c-cashflow)",
                    },
                  ].map((card) => (
                    <div
                      key={card.label}
                      className="rounded-[10px] bg-[var(--surface-2)] px-4 py-3.5"
                      style={{ borderTop: `2px solid ${card.color}` }}
                    >
                      <div className="mb-1.5 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
                        {card.label.toUpperCase()}
                      </div>
                      <div
                        className="mb-1 font-[family-name:var(--font-display)] text-[22px] font-bold leading-none"
                        style={{ color: card.color }}
                      >
                        {card.value}
                      </div>
                      <div className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">
                        {card.sub}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mb-5 grid gap-3 md:grid-cols-2">
                  <BulletList title="WHAT'S WORKING" items={strengths} tone="strong" marker="+" />
                  <BulletList title="WHAT TO WATCH" items={weaknesses} tone="weak" marker="−" />
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">
                    Ask:
                  </span>
                  <AskButton label="Why is valuation a concern?" onClick={() => askAbout("Explain the valuation and margin of safety from this analysis.")} />
                  <AskButton label="What is the biggest risk?" onClick={() => askAbout("What is the biggest risk in this analysis?")} />
                  <AskButton label="Explain the moat" onClick={() => askAbout("Explain the economic moat assessment.")} />
                  <AskButton label="How good is the quality score?" onClick={() => askAbout("Explain the business quality score.")} />
                </div>
              </div>
            </div>
          </section>

          <section ref={bind("s03")} className="mb-9">
            <SectionHead
              id="s03-head"
              num="02"
              title="Buffett-Style Assessment"
              subtitle="DSP analytical outputs organised through a Buffett-inspired investment framework."
            />
            <Card>
              {buffettRows.length === 0 ? (
                <p className="m-0 text-sm text-[var(--muted)]">{UNAVAILABLE}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-[13px]">
                    <thead>
                      <tr className="border-b border-[var(--border)]">
                        {["DIMENSION", "RESULT", "STATUS"].map((col) => (
                          <th
                            key={col}
                            className="px-3 py-2 text-left font-[family-name:var(--font-mono)] text-[10px] font-normal tracking-[0.08em] text-[var(--muted)]"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {buffettRows.map((row) => (
                        <tr key={row.dim} className="border-b border-[var(--border)] last:border-0">
                          <td className="px-3 py-2.5 text-[var(--fg)]">{row.dim}</td>
                          <td className="px-3 py-2.5 font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
                            {row.result}
                          </td>
                          <td className="px-3 py-2.5">
                            <StatusBadge text={row.status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
            <div className="mt-2.5 flex justify-end">
              <AskButton label="Ask about this assessment" onClick={() => askAbout("Explain the Buffett assessment.")} />
            </div>
          </section>

          <section ref={bind("s04")} className="mb-9">
            <SectionHead id="s04-head" num="03" title="Financial Analysis" />
            <div className="mb-4 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              {financialTiles.map((tile) => (
                <div key={tile.label} className="rounded-lg bg-[var(--surface-2)] px-3.5 py-3">
                  <div className="mb-1 font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">
                    {tile.label}
                  </div>
                  <div
                    className="font-[family-name:var(--font-mono)] text-[15px] font-semibold"
                    style={{ color: tile.value === UNAVAILABLE ? "var(--muted)" : tile.color }}
                  >
                    {tile.value}
                  </div>
                </div>
              ))}
            </div>
            <div className="grid gap-3.5 lg:grid-cols-2">
              <TrendChart series={trends.series.revenue} />
              <TrendChart series={trends.series.net_income} />
            </div>
            {view.financial.metrics.length > 0 ? (
              <Card className="mt-3.5">
                <div className="mb-2 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
                  STAGE METRICS
                </div>
                <dl>
                  {view.financial.metrics.map((metric) => (
                    <div key={metric.label} className="flex justify-between gap-3 border-b border-[var(--border)] py-2 text-sm last:border-0">
                      <dt className="text-[var(--muted)]">{metric.label}</dt>
                      <dd className="m-0 text-right font-[family-name:var(--font-mono)] text-xs">
                        {present(metric.value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </Card>
            ) : null}
            <div className="mt-2.5 flex justify-end">
              <AskButton label="Ask about the financials" onClick={() => askAbout("Explain the financial analysis.")} />
            </div>
          </section>

          <section ref={bind("s09")} className="mb-9">
            <SectionHead
              id="s09-head"
              num="04"
              title="Valuation & Intrinsic Value"
              status={present(view.marginOfSafetyView.classification)}
            />
            <Card>
              <div className="mb-5 grid gap-6 sm:grid-cols-3">
                {[
                  { label: "Current Market Price", value: present(view.valuation.currentPrice), color: "var(--fg)" },
                  { label: "DSP Intrinsic Value", value: present(view.valuation.intrinsicValue), color: "var(--c-cashflow)" },
                  {
                    label: "Margin of Safety",
                    value: present(view.marginOfSafetyView.display),
                    color: toneColor(toneFor(view.marginOfSafetyView.classification)),
                  },
                ].map((item) => (
                  <div key={item.label} className="text-center">
                    <div className="mb-1.5 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
                      {item.label}
                    </div>
                    <div
                      className="font-[family-name:var(--font-display)] text-[32px] font-bold leading-none"
                      style={{ color: item.value === UNAVAILABLE ? "var(--muted)" : item.color }}
                    >
                      {item.value}
                    </div>
                  </div>
                ))}
              </div>
              <div className="mb-1.5 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
                METHODOLOGY
              </div>
              <p className="m-0 text-[13px] leading-relaxed text-[var(--fg)]">
                {present(view.valuation.method)}. Confidence {present(view.valuation.confidence)}.{" "}
                {present(view.marginOfSafetyView.reasoning)}
              </p>
            </Card>
            <div className="mt-2.5 flex justify-end">
              <AskButton
                label="Why is valuation a concern?"
                onClick={() => askAbout("Explain the valuation and intrinsic value.")}
              />
            </div>
          </section>

          <section ref={bind("s02")} className="mb-9">
            <SectionHead id="s02-head" num="05" title="Business Quality" status={qualityLabel} />
            <div className="mb-4 grid gap-4 lg:grid-cols-[220px_1fr]">
              <Card className="flex flex-col items-center justify-center border-t-2 text-center" >
                <div className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.08em] text-[var(--muted)]">
                  COMPOSITE SCORE
                </div>
                <div
                  className="font-[family-name:var(--font-display)] text-6xl font-bold leading-none"
                  style={{ color: toneColor(toneFor(qualityLabel)) }}
                >
                  {qualityScore}
                </div>
                <div className="text-[11px] text-[var(--muted)]">/ 100</div>
                <StatusBadge text={qualityLabel} />
              </Card>
              <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                {view.domainScores.map((domain) => {
                  const color = DOMAIN_COLOR[domain.id] ?? "var(--c-dsp)";
                  return (
                    <Card key={domain.id} className="px-4 py-3.5" >
                      <div
                        className="-mx-[22px] -mt-5 mb-3 h-0.5"
                        style={{ background: color }}
                      />
                      <div className="mb-1 font-[family-name:var(--font-mono)] text-[10px] tracking-wide text-[var(--muted)]">
                        {domain.label.toUpperCase()}
                      </div>
                      <div className="mb-2 font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">
                        Weight: {present(domain.weight)}
                      </div>
                      <div className="mb-2 flex items-baseline gap-1">
                        <span className="font-[family-name:var(--font-display)] text-2xl font-bold" style={{ color }}>
                          {present(domain.score)}
                        </span>
                      </div>
                      {domain.scoreValue != null ? (
                        <div className="h-0.5 overflow-hidden rounded-full bg-[var(--border)]">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${Math.max(0, Math.min(100, domain.scoreValue))}%`, background: color }}
                          />
                        </div>
                      ) : null}
                    </Card>
                  );
                })}
              </div>
            </div>
            <Card className="mb-3">
              <div className="flex flex-wrap gap-5">
                <div className="min-w-[200px] flex-1">
                  <div className="mb-1 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
                    ECONOMIC MOAT
                  </div>
                  <div className="mb-2.5 font-[family-name:var(--font-display)] text-lg font-semibold text-[var(--fg)]">
                    {present(view.moat.label)}
                  </div>
                  <p className="m-0 mb-3 text-[13px] leading-relaxed text-[var(--fg)]">
                    {present(view.moat.decision)}
                  </p>
                  <AskButton label="Explain the moat" onClick={() => askAbout("Explain the economic moat.")} />
                </div>
                <div className="text-center">
                  <div className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">SCORE</div>
                  <div className="font-[family-name:var(--font-display)] text-5xl font-bold leading-none text-[var(--c-dsp)]">
                    {present(view.moat.score)}
                  </div>
                </div>
              </div>
            </Card>
          </section>

          <section ref={bind("s11")} className="mb-9">
            <SectionHead id="s11-head" num="06" title="Key Risks" status={present(view.risk?.overall_risk_level)} />
            <div className="flex flex-col gap-2.5">
              {riskCards.length === 0 ? (
                <Card>
                  <p className="m-0 text-sm text-[var(--muted)]">{UNAVAILABLE}</p>
                </Card>
              ) : (
                riskCards.map((risk) => (
                  <Card key={risk.name} className="border-l-[3px] border-l-[var(--c-risk)]">
                    <div className="mb-1.5 text-sm font-medium text-[var(--fg)]">{risk.name}</div>
                    <div className="mb-1.5 flex flex-wrap gap-1.5 text-xs">
                      <span className="font-[family-name:var(--font-mono)] text-[10px] tracking-wide text-[var(--muted)]">
                        EVIDENCE
                      </span>
                      <span className="text-[var(--muted)]">{risk.evidence}</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 text-xs">
                      <span className="font-[family-name:var(--font-mono)] text-[10px] tracking-wide text-[var(--c-risk)]">
                        LEVEL
                      </span>
                      <span className="text-[var(--muted)]">{risk.level}</span>
                    </div>
                  </Card>
                ))
              )}
            </div>
          </section>

          <section ref={bind("s06")} className="mb-9">
            <DeepDiveLabel title="Management & Capital Allocation" status={present(view.management.label)} />
            <SectionHead
              id="s06-head"
              num=""
              title="Management"
              subtitle="How is the business being led and how is capital being deployed?"
            />
            <div className="grid gap-3.5 md:grid-cols-2">
              <Card>
                <div className="mb-2.5 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
                  MANAGEMENT QUALITY
                </div>
                <StatusBadge text={present(view.management.label)} />
                <p className="mb-0 mt-3 text-[13px] leading-relaxed text-[var(--fg)]">
                  {present(view.management.decision)}
                </p>
              </Card>
              <Card>
                <div className="mb-2.5 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
                  STAGE METRICS
                </div>
                {view.management.metrics.length === 0 ? (
                  <p className="m-0 text-sm text-[var(--muted)]">{UNAVAILABLE}</p>
                ) : (
                  view.management.metrics.map((metric) => (
                    <div key={metric.label} className="flex items-center justify-between gap-3 border-b border-[var(--border)] py-2 text-sm">
                      <span>{metric.label}</span>
                      <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
                        {present(metric.value)}
                      </span>
                    </div>
                  ))
                )}
              </Card>
            </div>
          </section>

          <section ref={bind("s07")} className="mb-9">
            <DeepDiveLabel title="Earnings Quality" status={present(view.earnings.label)} />
            <SectionHead
              id="s07-head"
              num=""
              title="Earnings Quality"
              status={present(view.earnings.label)}
              subtitle="Are reported earnings durable and supported by the underlying business?"
            />
            <div className="grid gap-3.5 lg:grid-cols-2">
              <TrendChart series={trends.series.net_margin} />
              <MetricCard title="INDICATORS" metrics={view.earnings.metrics} />
            </div>
          </section>

          <section ref={bind("s08")} className="mb-9">
            <DeepDiveLabel title="Growth Quality" status={present(view.growth.label)} />
            <SectionHead
              id="s08-head"
              num=""
              title="Growth Quality"
              status={present(view.growth.label)}
              subtitle="Is growth consistent, and is it supported by the statements on file?"
            />
            <MetricCard title="GROWTH STAGE" metrics={view.growth.metrics} />
          </section>

          <section ref={bind("s10")} className="mb-9">
            <DeepDiveLabel title="Margin of Safety" status={present(view.marginOfSafetyView.classification)} />
            <SectionHead id="s10-head" num="" title="Margin of Safety" status={present(view.marginOfSafetyView.classification)} />
            <div className="grid gap-3.5 sm:grid-cols-2">
              <Card className="border-t-2" >
                <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
                  MARGIN OF SAFETY
                </p>
                <p
                  className="font-[family-name:var(--font-display)] text-4xl font-bold"
                  style={{ color: toneColor(toneFor(view.marginOfSafetyView.classification)) }}
                >
                  {present(view.marginOfSafetyView.display)}
                </p>
                <p className="text-xs text-[var(--muted)]">{present(view.marginOfSafetyView.classification)}</p>
              </Card>
              <Card>
                <Row label="Intrinsic value" value={present(view.marginOfSafetyView.intrinsicValue)} />
                <Row label="Current price" value={present(view.marginOfSafetyView.currentPrice)} />
                <Row label="Premium / discount" value={present(view.marginOfSafetyView.premiumDiscount)} />
                <Row label="Confidence" value={present(view.marginOfSafetyView.valuationConfidence)} />
              </Card>
            </div>
          </section>

          <section ref={bind("s12")} className="mb-9">
            <DeepDiveLabel title="Strengths & Weaknesses" />
            <SectionHead id="s12-head" num="" title="Strengths & Weaknesses" />
            <div className="grid gap-3 md:grid-cols-2">
              <BulletList title="STRENGTHS" items={strengths} tone="strong" marker="+" />
              <BulletList title="WEAKNESSES" items={weaknesses} tone="weak" marker="−" />
            </div>
            {view.strengthsWeaknesses.sources.length > 0 ? (
              <p className="mt-2 text-[11px] text-[var(--muted)]">
                Sources: {view.strengthsWeaknesses.sources.join(" · ")}
              </p>
            ) : null}
          </section>

          <section ref={bind("s13")} className="mb-9">
            <DeepDiveLabel title="Investment Context" />
            <SectionHead id="s13-head" num="" title="Investment Context" />
            <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {(
                [
                  ["Business quality", view.investmentContext.businessQuality],
                  ["Valuation", view.investmentContext.valuation],
                  ["Margin of safety", view.investmentContext.marginOfSafety],
                  ["Risk level", view.investmentContext.riskLevel],
                  ["Confidence", view.investmentContext.confidence],
                  ["Decision", view.investmentContext.decisionSummary],
                ] as const
              ).map(([label, value]) => (
                <Card key={label} className="px-4 py-3.5">
                  <div className="mb-1 font-[family-name:var(--font-mono)] text-[10px] tracking-wide text-[var(--muted)]">
                    {label.toUpperCase()}
                  </div>
                  <div className="text-sm text-[var(--fg)]">{present(value)}</div>
                </Card>
              ))}
            </div>
          </section>

          <section ref={bind("s14")} className="mb-9">
            <DeepDiveLabel title="Evidence" />
            <SectionHead
              id="s14-head"
              num=""
              title="Evidence"
              subtitle={present(view.transparency.dataInformation.primaryDataSource)}
            />
            <Card>
              <Row label="Analysis date" value={present(view.transparency.analysisDate)} />
              <Row label="Financial period" value={present(view.transparency.dataInformation.financialPeriodUsed)} />
              <Row label="Freshness" value={present(view.transparency.dataInformation.dataFreshness)} />
              <Row label="Pipeline" value={present(view.transparency.transparency.pipelineVersion)} />
              <Row label="Report id" value={present(view.transparency.reportId)} />
              <p className="mb-0 mt-3 text-xs leading-relaxed text-[var(--muted)]">
                {view.transparency.disclaimer}
              </p>
            </Card>
          </section>

          <section className="mb-9">
            <details className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-5 py-4">
              <summary className="cursor-pointer text-sm text-[var(--fg)]">
                Additional research
              </summary>
              <p className="mt-2 text-xs text-[var(--muted)]">
                Authenticated DSP feeds that are outside the Figma report sections.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {EXTRA_SECTIONS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setExtraSection(item.id)}
                    className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)]"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              {extraSection ? (
                <div className="mt-4">
                  <Suspense fallback={<p className="text-xs text-[var(--muted)]">Loading section…</p>}>
                    <ExtraResearch view={view} sectionId={extraSection} />
                  </Suspense>
                </div>
              ) : null}
            </details>
          </section>

          <section id="export" className="mb-9 scroll-mt-4">
            <SectionHead id="export-head" num="" title="Export" />
            <ExportSection
              view={view}
              analyseRequest={analyseRequest}
              analyseResponse={analyseResponse}
            />
          </section>

          {documentsOpen ? (
            <section id="documents" className="mb-9 scroll-mt-4">
              <SectionHead id="documents-head" num="" title="Documents" />
              <DocumentsSection view={view} />
            </section>
          ) : null}
        </div>
      </div>

      <div className="fixed inset-x-4 bottom-4 z-40 flex justify-center gap-2.5 md:hidden">
        <button
          type="button"
          onClick={() => setTocOpen(true)}
          className="rounded-full border border-[var(--border)] bg-[var(--card)] px-5 py-2.5 text-[13px] font-medium shadow-lg"
        >
          Sections
        </button>
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          className="rounded-full border border-[var(--border)] bg-[var(--card)] px-5 py-2.5 text-[13px] font-medium shadow-lg"
        >
          Ask DSP
        </button>
      </div>

      {tocOpen ? (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/55"
            aria-label="Close sections"
            onClick={() => setTocOpen(false)}
          />
          <nav
            aria-label="Analysis sections"
            className="absolute inset-x-0 bottom-0 max-h-[75vh] overflow-auto rounded-t-2xl border-t border-[var(--border)] bg-[var(--card)] pb-6"
          >
            <div className="flex justify-center py-3">
              <div className="h-1 w-9 rounded-full bg-[var(--border)]" />
            </div>
            {TOC.map((group) => (
              <div key={group.label}>
                <div className="px-5 py-2 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.1em] text-[var(--muted)]">
                  {group.label}
                </div>
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => scrollTo(item.id)}
                    className="block w-full px-5 py-2.5 text-left text-sm"
                    style={{ color: activeSection === item.id ? "var(--fg)" : "var(--muted)" }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            ))}
            <button
              type="button"
              className="block w-full px-5 py-2.5 text-left text-sm text-[var(--muted)]"
              onClick={() => {
                setDocumentsOpen(true);
                scrollTo("documents");
              }}
            >
              Documents
            </button>
          </nav>
        </div>
      ) : null}

      {chatOpen ? (
        <div
          className="fixed inset-x-0 bottom-0 z-50 flex max-h-[46vh] flex-col overflow-hidden border-t border-[var(--border)] bg-[var(--card)] shadow-[0_-4px_24px_rgba(0,0,0,0.4)]"
          role="dialog"
          aria-label="Ask DSP about this analysis"
        >
          <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-2.5">
            <div className="flex min-w-0 items-center gap-2">
              <span
                aria-hidden
                className="flex size-[22px] items-center justify-center rounded-md bg-[linear-gradient(135deg,#7c6af7,#2dd4bf)] text-[10px] font-bold text-white"
              >
                D
              </span>
              <span className="text-[13px] font-medium text-[var(--fg)]">Ask DSP about this analysis</span>
              <span className="truncate font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">
                · {view.ticker}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setChatOpen(false)}
              className="rounded-md px-2 py-1 text-base leading-none text-[var(--muted)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label="Close Ask DSP"
            >
              ×
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-auto p-3">
            <AiCopilotSection
              view={view}
              analyseRequest={analyseRequest}
              analyseResponse={analyseResponse}
              seedQuestion={chatSeed}
              presentation="conversation"
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ExtraResearch({
  view,
  sectionId,
}: {
  view: ResearchView;
  sectionId: string;
}) {
  const item = EXTRA_SECTIONS.find((section) => section.id === sectionId);
  if (!item) return null;
  const Section = item.Section;
  return <Section view={view} />;
}

function MetricCard({
  title,
  metrics,
}: {
  title: string;
  metrics: { label: string; value: string }[];
}) {
  return (
    <Card>
      <div className="mb-2.5 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">
        {title}
      </div>
      {metrics.length === 0 ? (
        <p className="m-0 text-sm text-[var(--muted)]">{UNAVAILABLE}</p>
      ) : (
        metrics.map((metric) => (
          <div key={metric.label} className="flex items-center justify-between gap-3 border-b border-[var(--border)] py-2 text-sm last:border-0">
            <span>{metric.label}</span>
            <StatusBadge text={present(metric.value)} />
          </div>
        ))
      )}
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-[var(--border)] py-2 text-sm last:border-0">
      <span className="text-[var(--muted)]">{label}</span>
      <span className="text-right font-[family-name:var(--font-mono)] text-xs">{value}</span>
    </div>
  );
}

function riskRows(view: ResearchView): { name: string; evidence: string; level: string }[] {
  const payload = view.risk;
  if (!payload) {
    return view.risks.map((risk) => ({ name: risk, evidence: UNAVAILABLE, level: UNAVAILABLE }));
  }
  const categories: RiskCategoryPayload[] = [
    payload.business_risk,
    payload.financial_risk,
    payload.regulatory_risk,
    payload.technology_risk,
    payload.currency_risk,
    payload.customer_concentration_risk,
  ];
  return categories
    .filter((category) => category.available)
    .map((category) => ({
      name: category.category,
      evidence: category.evidence?.filter(Boolean).join("; ") || present(category.message),
      level: present(category.level || category.source_rating),
    }));
}
