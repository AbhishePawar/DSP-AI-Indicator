/**
 * Research view-model — maps API AnalyseResponse + request context only.
 * No scoring, no valuation math, no recommendation overrides.
 */

import type {
  AnalyseRequest,
  AnalyseResponse,
  BusinessQualityPublic,
  CompanyRiskPayload,
  DecisionSummary,
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

/**
 * Figma `CompanyAnalysis` domain scorecard row. Score comes from the existing
 * pipeline stage summary; weight from `business_quality.engine_weights`
 * (BusinessQualityAggregatorWeights.as_dict()). Presentation only — nothing
 * is recomputed in the browser.
 */
export type DomainScoreView = {
  id:
    | "economic_moat"
    | "management_quality"
    | "financial_strength"
    | "earnings_quality"
    | "growth_quality";
  label: string;
  /** 0–100 or null when the stage has no result. */
  scoreValue: number | null;
  score: string;
  /** Aggregator weight as a percentage (0–100) or null when not exposed. */
  weightValue: number | null;
  weight: string;
  status: string;
};

/**
 * Figma `CompanyAnalysis` S10 — standalone Margin of Safety card pair.
 * RS-005. Values come from `recommendation_summary.margin_of_safety_assessment`
 * (recommendation engine) with `server_valuation` as the price / IV authority.
 * The browser formats; it never recomputes MoS.
 */
export type MarginOfSafetyView = {
  /** Ratio as published (e.g. -0.188) or null. */
  value: number | null;
  /** Formatted percentage or "Unavailable". */
  display: string;
  /** discount → price below IV; premium → price above IV. */
  status: "discount" | "premium" | "unavailable";
  /** Engine classification label (e.g. "NEGATIVE") or "Unavailable". */
  classification: string;
  reasoning: string | null;
  intrinsicValue: string;
  currentPrice: string;
  premiumDiscount: string;
  valuationConfidence: string;
};

/**
 * Figma S12 — Strengths & Weaknesses. Powered by the recommendation engine's
 * `positive_factors` / `negative_factors` and the Business Quality aggregator's
 * `strengths` / `weaknesses`. Not client-authored; not AI-generated in browser.
 */
export type StrengthsWeaknessesView = {
  strengths: string[];
  weaknesses: string[];
  /** Which authoritative sources contributed (for the provenance footer). */
  sources: string[];
};

/** Figma S13 — Investment Context tiles (all from existing payload fields). */
export type InvestmentContextView = {
  businessQuality: string;
  valuation: string;
  marginOfSafety: string;
  riskLevel: string;
  confidence: string;
  decisionSummary: string | null;
  keyDrivers: string[];
};

export type ResearchView = IntelligenceView & {
  ticker: string;
  exchange: string;
  company: string;
  analysedAt: string | null;
  /** Figma weighted domain scorecard — existing stage scores + aggregator weights. */
  domainScores: DomainScoreView[];
  marginOfSafetyView: MarginOfSafetyView;
  strengthsWeaknesses: StrengthsWeaknessesView;
  investmentContext: InvestmentContextView;
  /** Reporting currency from source_evidence (ISO 4217) or null. */
  currency: string | null;
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
  /** SIMPLE-19A — additive official-research completeness. Display only. */
  officialResearch: {
    analysisState: string;
    fullAnalysis: boolean;
    identityStatus: string | null;
    detail: string | null;
    overallScoreStatus: string;
    coreDsp: {
      status: string;
      overallScoreStatus: string;
      businessQualityRating: string;
      moatRating: string;
      managementRating: string;
      riskLevel: string;
    } | null;
    advancedCheck: {
      name: string;
      uiName: string;
      status: string;
      detail: string;
      hardFailStatus: string;
      replacesCoreDsp: boolean;
      altersDcf: boolean;
      findings: Array<{
        finding: string;
        dimension: string;
        evidence: string;
        dataClass: string;
        verificationStatus: string;
        severity: string;
      }>;
      thesisBreakers: Array<{
        id: string;
        dimension: string;
        description: string;
        severity: string;
        verificationStatus: string;
        trigger: string;
        monitoringMetric: string;
      }>;
      thesis: {
        status: string;
        confidence: string;
        positiveFactors: string[];
        negativeFactors: string[];
        keyAssumptions: string[];
      };
      asymmetry: {
        upside: string;
        downside: string;
        probability: string;
        detail: string;
      };
    } | null;
    thesisStatus: string | null;
  };
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

/**
 * Format a per-share amount in the reporting currency published by the
 * backend (`source_evidence.reporting_currency`). When the currency is not
 * known we show the bare number rather than inventing a symbol (CV-001).
 */
export function money(value: unknown, currency: string | null = null): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    if (currency && /^[A-Z]{3}$/.test(currency)) {
      try {
        return value.toLocaleString(undefined, {
          style: "currency",
          currency,
          maximumFractionDigits: 2,
        });
      } catch {
        // Unknown ISO code in this runtime — fall through to bare number.
      }
    }
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return "Unavailable";
}

function reportingCurrency(response: AnalyseResponse): string | null {
  const raw = (
    response.payload as { source_evidence?: { reporting_currency?: unknown } | null }
  )?.source_evidence?.reporting_currency;
  if (typeof raw !== "string") return null;
  const code = raw.trim().toUpperCase();
  return /^[A-Z]{3}$/.test(code) ? code : null;
}

function uniqueStrings(...lists: Array<readonly string[] | undefined>): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const list of lists) {
    for (const item of list ?? []) {
      const text = String(item).trim();
      if (!text || seen.has(text)) continue;
      seen.add(text);
      out.push(text);
    }
  }
  return out;
}

/**
 * RS-005 Margin of Safety presentation (Figma S10). Prefers the recommendation
 * engine's assessment; IV / price fall back to server_valuation. No arithmetic.
 */
export function mapMarginOfSafety(
  recommendation: DecisionSummary | null | undefined,
  serverValuation:
    | { intrinsic_value_per_share?: number | null; current_market_price?: number | null }
    | null
    | undefined,
  currency: string | null,
): MarginOfSafetyView {
  const assessment = recommendation?.margin_of_safety_assessment ?? null;
  const ratioRaw = assessment?.margin_of_safety ?? recommendation?.margin_of_safety;
  const value =
    typeof ratioRaw === "number" && Number.isFinite(ratioRaw) ? ratioRaw : null;
  const iv =
    assessment?.intrinsic_value_per_share ?? serverValuation?.intrinsic_value_per_share;
  const price =
    assessment?.current_market_price ?? serverValuation?.current_market_price;
  const premium = assessment?.premium_discount;
  return {
    value,
    display: formatPct(value),
    status: value == null ? "unavailable" : value >= 0 ? "discount" : "premium",
    classification: display(assessment?.classification),
    reasoning: assessment?.reasoning?.trim() ? assessment.reasoning.trim() : null,
    intrinsicValue: money(iv ?? null, currency),
    currentPrice: money(price ?? null, currency),
    premiumDiscount: formatPct(
      typeof premium === "number" && Number.isFinite(premium) ? premium : null,
    ),
    valuationConfidence: formatPct(
      typeof assessment?.valuation_confidence === "number"
        ? assessment.valuation_confidence
        : null,
    ),
  };
}

/** Figma S12 — engine-published factors only (no browser synthesis). */
export function mapStrengthsWeaknesses(
  recommendation: DecisionSummary | null | undefined,
  businessQuality: BusinessQualityPublic | null | undefined,
): StrengthsWeaknessesView {
  const sources: string[] = [];
  if (recommendation?.positive_factors?.length || recommendation?.negative_factors?.length) {
    sources.push("investment_recommendation");
  }
  if (businessQuality?.strengths?.length || businessQuality?.weaknesses?.length) {
    sources.push("business_quality_aggregator");
  }
  return {
    strengths: uniqueStrings(recommendation?.positive_factors, businessQuality?.strengths),
    weaknesses: uniqueStrings(recommendation?.negative_factors, businessQuality?.weaknesses),
    sources,
  };
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

const DOMAIN_SCORE_ORDER: readonly { id: DomainScoreView["id"]; label: string }[] = [
  { id: "economic_moat", label: "Economic Moat" },
  { id: "management_quality", label: "Management Quality" },
  { id: "financial_strength", label: "Financial Strength" },
  { id: "earnings_quality", label: "Earnings Quality" },
  { id: "growth_quality", label: "Growth Quality" },
];

/**
 * Weighted domain scorecard (Figma `DOMAIN_SCORES`). Scores are the existing
 * stage_summaries scores; weights are the aggregator's published
 * `engine_weights` (fractions summing to 1). Missing inputs stay Unavailable.
 */
export function mapDomainScores(
  stages: StageSummary[],
  engineWeights: unknown,
): DomainScoreView[] {
  const weights =
    engineWeights && typeof engineWeights === "object"
      ? (engineWeights as Record<string, unknown>)
      : null;
  return DOMAIN_SCORE_ORDER.map(({ id, label }) => {
    const stage = stageOrEmpty(stages, id);
    const status = stage?.status ?? "unavailable";
    const available =
      Boolean(stage?.has_result) &&
      (status === "succeeded" || status === "degraded") &&
      typeof stage?.score === "number" &&
      Number.isFinite(stage.score);
    const scoreValue = available ? (stage!.score as number) : null;
    const rawWeight = weights?.[id];
    const weightValue =
      typeof rawWeight === "number" && Number.isFinite(rawWeight) && rawWeight >= 0
        ? Math.round(rawWeight * 1000) / 10
        : null;
    return {
      id,
      label,
      scoreValue,
      score: formatScore(scoreValue),
      weightValue,
      weight: weightValue == null ? "Unavailable" : `${weightValue}%`,
      status: available ? status : "unavailable",
    };
  });
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
        price_kind?: string | null;
        price_as_of?: string | null;
        valuation_status?: string | null;
        valuation_detail?: string | null;
      } | null;
      source_evidence?: {
        current_market_price?: number | null;
        price_kind?: string | null;
      } | null;
    }
  ).server_valuation;
  const sourceEvidence = (
    response.payload as {
      source_evidence?: {
        current_market_price?: number | null;
        price_kind?: string | null;
      } | null;
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

  const businessQualityPublic = response.payload?.business_quality ?? null;
  const recommendationSummary = response.payload?.recommendation_summary ?? null;
  const currency = reportingCurrency(response);
  const domainScores = mapDomainScores(
    stages,
    businessQualityPublic?.engine_weights,
  );
  const marginOfSafetyView = mapMarginOfSafety(
    recommendationSummary,
    serverValuation,
    currency,
  );
  const strengthsWeaknesses = mapStrengthsWeaknesses(
    recommendationSummary,
    businessQualityPublic,
  );
  const riskPayload =
    (response.payload?.risk as CompanyRiskPayload | null | undefined) ?? null;
  const investmentContext: InvestmentContextView = {
    businessQuality:
      base.businessQualityScore == null
        ? display(base.businessQualityLabel)
        : `${formatScore(base.businessQualityScore)} / 100`,
    valuation: marginOfSafetyView.classification,
    marginOfSafety: marginOfSafetyView.display,
    riskLevel: display(riskPayload?.overall_risk_level),
    confidence: formatPct(base.recommendationConfidence),
    decisionSummary: recommendationSummary?.decision_summary?.trim()
      ? recommendationSummary.decision_summary.trim()
      : null,
    keyDrivers: uniqueStrings(recommendationSummary?.key_drivers),
  };

  const draft = {
    ...base,
    ticker: request.ticker.toUpperCase(),
    exchange: display(request.exchange, "—"),
    company: display(request.company, request.ticker.toUpperCase()),
    analysedAt: analysedAt ?? null,
    domainScores,
    marginOfSafetyView,
    strengthsWeaknesses,
    investmentContext,
    currency,
    valuation: {
      intrinsicValue: money(
        serverValuation?.intrinsic_value_per_share ?? null,
        currency,
      ),
      currentPrice: money(
        serverValuation?.current_market_price ??
          sourceEvidence?.current_market_price ??
          null,
        currency,
      ),
      marginOfSafety: formatPct(base.marginOfSafety),
      method: display(
        serverValuation?.valuation_status === "REFRESH_REQUIRED"
          ? "REFRESH REQUIRED"
          : serverValuation?.valuation_status === "UNAVAILABLE"
            ? "VALUATION UNAVAILABLE"
            : serverValuation?.valuation_status === "VERIFIED"
              ? "VALUATION AVAILABLE"
          : serverValuation?.price_kind === "EOD"
            ? `EOD ${serverValuation.price_as_of ?? ""}`.trim()
            : (valuationStage?.label ?? valuationStage?.decision),
        "API valuation stage",
      ),
      confidence: formatPct(
        serverValuation?.intrinsic_value_per_share == null
          ? null
          : (serverValuation?.confidence ??
            valuationStage?.confidence ??
            null),
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
    officialResearch: (() => {
      const official = (
        response.payload as {
          official_research?: {
            analysis_state?: string;
            full_analysis?: boolean;
            identity_status?: string;
            detail?: string;
            core_dsp?: {
              status?: string;
              overall_score_status?: string;
              overall_business_quality?: string | null;
              business_quality?: { rating?: string | null };
              moat?: { rating?: string | null };
              management?: { rating?: string | null };
              risk?: { overall_risk_level?: string | null };
            } | null;
            advanced_check?: {
              name?: string;
              ui_name?: string;
              status?: string;
              detail?: string;
              hard_fail_status?: string;
              replaces_core_dsp?: boolean;
              alters_dcf?: boolean;
              findings?: Array<{
                finding?: string;
                dimension?: string;
                evidence?: string;
                data_class?: string;
                verification_status?: string;
                severity?: string;
              }>;
              thesis_breakers?: Array<{
                id?: string;
                dimension?: string;
                description?: string;
                severity?: string;
                verification_status?: string;
                trigger?: string;
                monitoring_metric?: string;
              }>;
              thesis?: {
                status?: string;
                confidence?: string;
                positive_factors?: string[];
                negative_factors?: string[];
                key_assumptions?: string[];
              };
              asymmetry?: {
                upside?: string;
                downside?: string;
                probability?: string;
                detail?: string;
              };
            } | null;
            thesis?: { status?: string };
            result_contract?: { overall_score?: string };
          } | null;
        }
      ).official_research;
      const state = official?.analysis_state;
      const core = official?.core_dsp ?? null;
      const adv = official?.advanced_check ?? null;
      const overallScoreStatus =
        core?.overall_score_status ||
        official?.result_contract?.overall_score ||
        "NOT_CURRENTLY_DEFINED";
      return {
        analysisState: state
          ? state === "FULL_ANALYSIS"
            ? "FULL ANALYSIS"
            : state === "PARTIAL_DATA"
              ? "PARTIAL ANALYSIS"
              : state.replaceAll("_", " ")
          : "PARTIAL ANALYSIS",
        fullAnalysis: official?.full_analysis === true,
        identityStatus: official?.identity_status ?? null,
        detail: official?.detail ?? null,
        overallScoreStatus,
        coreDsp: core
          ? {
              status: core.status || "UNKNOWN",
              overallScoreStatus,
              businessQualityRating:
                core.overall_business_quality ||
                core.business_quality?.rating ||
                "UNKNOWN",
              moatRating: core.moat?.rating || "UNKNOWN",
              managementRating: core.management?.rating || "UNKNOWN",
              riskLevel: core.risk?.overall_risk_level || "UNKNOWN",
            }
          : null,
        advancedCheck: adv
          ? {
              name: adv.name || "ADVANCED_FAILURE_ASYMMETRY",
              uiName: adv.ui_name || "Advanced Investment Check",
              status: adv.status || "UNKNOWN",
              detail: adv.detail || "Data unavailable.",
              hardFailStatus: adv.hard_fail_status || "REVIEW_REQUIRED",
              replacesCoreDsp: adv.replaces_core_dsp === true,
              altersDcf: adv.alters_dcf === true,
              findings: (adv.findings || []).map((item) => ({
                finding: item.finding || "Data unavailable.",
                dimension: item.dimension || "UNKNOWN",
                evidence: item.evidence || "Data unavailable.",
                dataClass: item.data_class || "UNVERIFIED",
                verificationStatus: item.verification_status || "UNKNOWN",
                severity: item.severity || "MEDIUM",
              })),
              thesisBreakers: (adv.thesis_breakers || []).map((item) => ({
                id: item.id || "unknown",
                dimension: item.dimension || "UNKNOWN",
                description: item.description || "Data unavailable.",
                severity: item.severity || "MEDIUM",
                verificationStatus: item.verification_status || "UNKNOWN",
                trigger: item.trigger || "Data unavailable.",
                monitoringMetric:
                  item.monitoring_metric || "descriptive only — no monitor built",
              })),
              thesis: {
                status: adv.thesis?.status || official?.thesis?.status || "UNKNOWN",
                confidence: adv.thesis?.confidence || "none",
                positiveFactors: adv.thesis?.positive_factors || [],
                negativeFactors: adv.thesis?.negative_factors || [],
                keyAssumptions: adv.thesis?.key_assumptions || [],
              },
              asymmetry: {
                upside: adv.asymmetry?.upside || "UNKNOWN",
                downside: adv.asymmetry?.downside || "UNKNOWN",
                probability: adv.asymmetry?.probability || "UNKNOWN",
                detail:
                  adv.asymmetry?.detail ||
                  "probabilities are not defined by existing methodology",
              },
            }
          : null,
        thesisStatus: adv?.thesis?.status || official?.thesis?.status || null,
      };
    })(),
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
