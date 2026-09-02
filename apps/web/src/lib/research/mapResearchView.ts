/**
 * Research view-model — maps API AnalyseResponse + request context only.
 * No scoring, no valuation math, no recommendation overrides.
 */

import type {
  AnalyseRequest,
  AnalyseResponse,
  CompanyRiskPayload,
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
import {
  mapCanonicalMoatDimensions,
  type CanonicalMoatDimensionView,
} from "@/lib/research/canonicalMoatDimensions";

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
  /** Composition Risk stage — structural aggregation of existing engines only. */
  risk: CompanyRiskPayload | null;
  /**
   * Frozen six-row Economic Moat dimensions from the public DSP contract.
   * Copied when present; never derived from overall moat or client X/10 math.
   */
  canonicalMoatDimensions: CanonicalMoatDimensionView[];
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

function readEconomicMoatDimensionsField(payload: unknown): unknown {
  if (!payload || typeof payload !== "object") return null;
  return (payload as Record<string, unknown>).economic_moat_dimensions ?? null;
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
  const valuationStage = stageOrEmpty(stages, "valuation");
  // Server-authoritative valuation display — never client valuation_signals IV/MoS.
  const serverValuation = (
    response.payload as {
      server_valuation?: {
        intrinsic_value_per_share?: number | null;
        current_market_price?: number | null;
        confidence?: number | null;
      } | null;
      source_evidence?: {
        current_market_price?: number | null;
      } | null;
    }
  ).server_valuation;
  const sourceEvidence = (
    response.payload as {
      source_evidence?: { current_market_price?: number | null } | null;
    }
  ).source_evidence;

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
  // RC3-001 / GOV-001 — Business Quality metrics from business_quality_aggregator only.
  // Never alias Management / Growth / Moat / Risk / Financial into Book 04 fields.
  const businessQuality = toSection(
    stageOrEmpty(stages, "business_quality_aggregator"),
    [
      "Overall Score",
      "Label",
      "Decision",
      "Confidence",
      "Capital Allocation Quality",
      "Industry Structure",
      "Operating Discipline",
      "Franchise Durability",
      "Reinvestment Opportunity",
    ],
  );
  if (base.businessQualityScore != null) {
    businessQuality.metrics = businessQuality.metrics.map((m) =>
      m.label === "Overall Score"
        ? { ...m, value: formatScore(base.businessQualityScore) }
        : m,
    );
  }

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
      intrinsicValue: money(serverValuation?.intrinsic_value_per_share ?? null),
      currentPrice: money(
        serverValuation?.current_market_price ??
          sourceEvidence?.current_market_price ??
          request.current_market_price ??
          null,
      ),
      marginOfSafety: formatPct(base.marginOfSafety),
      method: display(
        valuationStage?.label ?? valuationStage?.decision,
        "API valuation stage",
      ),
      confidence: formatPct(
        serverValuation?.confidence ??
          valuationStage?.confidence ??
          null,
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
    risk: (response.payload?.risk as CompanyRiskPayload | null | undefined) ?? null,
    canonicalMoatDimensions: mapCanonicalMoatDimensions(
      readEconomicMoatDimensionsField(response.payload),
    ).dimensions,
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
