/**
 * Research view-model — maps API AnalyseResponse + request context only.
 * No scoring, no valuation math, no recommendation overrides.
 */

import type {
  AnalyseRequest,
  AnalyseResponse,
  StageSummary,
} from "@/lib/api/compositionTypes";
import {
  formatPct,
  formatScore,
  mapAnalyseResponse,
  type IntelligenceView,
} from "@/lib/intelligence/mapResponse";
import {
  mapBuffettReport,
  type BuffettReportView,
} from "@/lib/buffett-indicator";
import {
  mapInstitutionalRatings,
  type InstitutionalRatingFramework,
} from "@/lib/institutional-rating";
import {
  mapReportTransparency,
  type ReportTransparencyView,
} from "@/lib/report-transparency";
import {
  mapInstitutionalExplainability,
  type InstitutionalExplainabilityFramework,
} from "@/lib/explainability";
import {
  mapValuationTransparency,
  type ValuationTransparencyView,
} from "@/lib/valuation-transparency";

export type StageSectionView = {
  stage: string;
  status: string;
  label: string;
  decision: string;
  score: string;
  confidence: string;
  error: string | null;
  warnings: string[];
  metrics: { label: string; value: string }[];
};

export type ResearchView = IntelligenceView & {
  ticker: string;
  exchange: string;
  company: string;
  analysedAt: string | null;
  valuation: {
    intrinsicValue: string;
    currentPrice: string;
    marginOfSafety: string;
    method: string;
    confidence: string;
  };
  financial: StageSectionView;
  moat: StageSectionView;
  management: StageSectionView;
  financialStrength: StageSectionView;
  earnings: StageSectionView;
  growth: StageSectionView;
  businessQuality: StageSectionView;
  recommendationStage: StageSectionView;
  committee: StageSectionView & {
    supportingReasons: string[];
    opposingReasons: string[];
    finalRecommendation: string;
  };
  /** ARCH-001 — presentation synthesis after final recommendation (no new engine). */
  buffett: BuffettReportView;
  /** ARCH-002 — unified institutional rating framework (presentation aggregate). */
  ratings: InstitutionalRatingFramework;
  /** P2.1 — report transparency / Report Information card. */
  transparency: ReportTransparencyView;
  /** P2.2 — expandable explainability for each institutional rating. */
  explainability: InstitutionalExplainabilityFramework;
  /** P2.3 — institutional valuation transparency (presentation). */
  valuationTransparency: ValuationTransparencyView;
};

function stageOrEmpty(
  stages: StageSummary[],
  name: string,
): StageSummary | undefined {
  return stages.find((s) => s.stage === name);
}

function display(value: unknown, fallback = "Unavailable"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function money(value: unknown): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value.toLocaleString(undefined, {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    });
  }
  return "Unavailable";
}

function toSection(
  stage: StageSummary | undefined,
  metricLabels: string[],
): StageSectionView {
  const status = stage?.status ?? "unavailable";
  const label = display(stage?.label);
  const decision = display(stage?.decision);
  const score = formatScore(stage?.score ?? null);
  const confidence = formatPct(stage?.confidence ?? null);

  // Sub-metrics reflect stage summary fields only — never invent scores.
  const metrics = metricLabels.map((metricLabel, index) => {
    if (index === 0) return { label: metricLabel, value: score };
    if (index === 1) return { label: metricLabel, value: label };
    if (index === 2) return { label: metricLabel, value: decision };
    if (index === 3) return { label: metricLabel, value: confidence };
    return { label: metricLabel, value: "Unavailable" };
  });

  return {
    stage: stage?.stage ?? "—",
    status,
    label,
    decision,
    score,
    confidence,
    error: stage?.error ?? null,
    warnings: stage?.warnings ?? [],
    metrics,
  };
}

/** Map analyse API response + request context → ResearchView. */
export function mapResearchView(
  response: AnalyseResponse,
  request: AnalyseRequest,
  analysedAt?: string | null,
): ResearchView {
  const base = mapAnalyseResponse(response);
  const stages = base.stages;
  const signals = request.valuation_signals;
  const valuationStage = stageOrEmpty(stages, "valuation");

  const financial = toSection(stageOrEmpty(stages, "financial"), [
    "Score",
    "Summary",
    "Decision",
    "Confidence",
  ]);
  const moat = toSection(stageOrEmpty(stages, "economic_moat"), [
    "Score",
    "Moat",
    "Competitive Position",
    "Confidence",
  ]);
  const management = toSection(stageOrEmpty(stages, "management_quality"), [
    "Score",
    "Capital Allocation",
    "Governance",
    "Shareholder Alignment",
  ]);
  const financialStrength = toSection(
    stageOrEmpty(stages, "financial_strength"),
    ["Score", "Debt", "Liquidity", "Cash Flow"],
  );
  // Coverage as 4th metric via confidence when present
  financialStrength.metrics.push({
    label: "Coverage",
    value: financialStrength.confidence,
  });

  const earnings = toSection(stageOrEmpty(stages, "earnings_quality"), [
    "Score",
    "Consistency",
    "Cash Conversion",
    "Accounting Quality",
  ]);
  const growth = toSection(stageOrEmpty(stages, "growth_quality"), [
    "Score",
    "Revenue Growth",
    "Profit Growth",
    "Reinvestment",
  ]);
  const businessQuality = toSection(
    stageOrEmpty(stages, "business_quality_aggregator"),
    ["Overall Score", "Moat", "Capital Allocation", "Competitive Position"],
  );
  // Prefer aggregator score for Overall; moat/capital from sibling stages when available
  businessQuality.metrics = [
    { label: "Overall Score", value: formatScore(base.businessQualityScore) },
    { label: "Moat", value: moat.label },
    { label: "Capital Allocation", value: management.label },
    { label: "Competitive Position", value: moat.decision },
  ];

  const recommendationStage = toSection(
    stageOrEmpty(stages, "investment_recommendation"),
    ["Score", "Label", "Decision", "Confidence"],
  );
  const committeeBase = toSection(
    stageOrEmpty(stages, "investment_committee"),
    ["Score", "Label", "Decision", "Confidence"],
  );

  const committee = {
      ...committeeBase,
      supportingReasons: base.strengths,
      opposingReasons: [...base.weaknesses, ...base.risks],
      finalRecommendation: base.recommendation,
  };

  const draft = {
    ...base,
    ticker: request.ticker.toUpperCase(),
    exchange: display(request.exchange, "—"),
    company: display(request.company, request.ticker.toUpperCase()),
    analysedAt: analysedAt ?? null,
    valuation: {
      intrinsicValue: money(signals?.intrinsic_value_per_share),
      currentPrice: money(
        request.current_market_price ?? signals?.current_market_price,
      ),
      marginOfSafety: formatPct(base.marginOfSafety),
      method: display(
        valuationStage?.label ?? valuationStage?.decision,
        "API valuation stage",
      ),
      confidence: formatPct(
        valuationStage?.confidence ?? signals?.confidence ?? null,
      ),
    },
    financial,
    moat,
    management,
    financialStrength,
    earnings,
    growth,
    businessQuality,
    recommendationStage,
    committee,
  };
  const withBuffett = {
    ...draft,
    buffett: mapBuffettReport(draft),
  };
  const withRatings = {
    ...withBuffett,
    ratings: mapInstitutionalRatings(withBuffett),
  };
  const withTransparency = {
    ...withRatings,
    transparency: mapReportTransparency(withRatings),
    explainability: mapInstitutionalExplainability(withRatings.ratings.modules),
  };
  return {
    ...withTransparency,
    valuationTransparency: mapValuationTransparency(withTransparency),
  };
}
