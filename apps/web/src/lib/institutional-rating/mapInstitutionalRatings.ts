/**
 * ARCH-002 — Map ResearchView → Institutional Rating Framework.
 * Presentation aggregation only — reuses existing stage/Buffett/recommendation fields.
 */

import type { ResearchView, StageSectionView } from "@/lib/research/mapResearchView";
import type {
  InstitutionalRatingFramework,
  InvestmentAction,
  ModuleRating,
  OverallInvestmentRating,
  RatingDimension,
  ScorecardRow,
} from "./types";
import {
  averageGradeFromExisting,
  averageScoreOutOf10,
  confidenceDisplay,
  isUnavailableDisplay,
  letterGradeFromExistingScore,
  scoreOutOf10FromExisting,
  starsFromGrade,
} from "./scale";

const DISCLAIMER =
  "Institutional Rating Framework is a presentation remapping of existing /api/v1/analyse outputs. It does not recalculate fundamentals, valuation, or recommendations. Missing fields show Unavailable. Research Mode — not investment advice.";

function metric(
  section: StageSectionView,
  label: string,
): string {
  const hit = section.metrics.find(
    (m) => m.label.toLowerCase() === label.toLowerCase(),
  );
  return hit?.value ?? "Unavailable";
}

function dim(label: string, value: string, evidence: string): RatingDimension {
  return { label, value, evidence };
}

function fromStage(
  id: string,
  title: string,
  section: StageSectionView,
  sourceStages: string[],
  dimensions: RatingDimension[],
  extraStrengths: string[] = [],
  extraWeaknesses: string[] = [],
  explanationExtra = "",
): ModuleRating {
  const available =
    section.status === "succeeded" && !isUnavailableDisplay(section.score);
  const strengths = [
    ...extraStrengths,
    ...(available && section.label !== "Unavailable"
      ? [`${title} label: ${section.label}`]
      : []),
  ];
  const weaknesses = [
    ...extraWeaknesses,
    ...(section.error ? [`Stage error: ${section.error}`] : []),
    ...section.warnings.map((w) => `Warning: ${w}`),
    ...(!available ? [`${title}: stage score unavailable`] : []),
  ];
  return {
    id,
    title,
    scoreOutOf10: scoreOutOf10FromExisting(section.score),
    grade: letterGradeFromExistingScore(section.score),
    confidence: confidenceDisplay(section.confidence),
    evidence: [
      `stage=${section.stage}`,
      `status=${section.status}`,
      `score(existing)=${section.score}`,
      `label=${section.label}`,
      `decision=${section.decision}`,
      ...dimensions.map((d) => `${d.label}: ${d.value} (${d.evidence})`),
    ],
    strengths: strengths.length ? strengths : ["Data unavailable."],
    weaknesses: weaknesses.length ? weaknesses : ["Data unavailable."],
    explanation:
      explanationExtra ||
      (available
        ? `${title} remapped from existing ${section.stage} stage (score ${section.score}, label ${section.label}).`
        : `${title} cannot be graded — existing ${section.stage} score unavailable.`),
    dimensions,
    sourceStages,
  };
}

export function investmentActionFromExisting(decision: string): InvestmentAction {
  if (isUnavailableDisplay(decision)) return "Unavailable";
  const d = decision.toLowerCase().replace(/[\s-]+/g, "_");
  if (d.includes("strong_buy") || d.includes("strong buy")) return "BUY";
  if (d.includes("accumulate")) return "ACCUMULATE";
  if (d === "buy" || d.endsWith("_buy") || d.includes("overweight")) return "BUY";
  if (d.includes("watch") || d.includes("monitor")) return "WATCH";
  if (d.includes("reduce") || d.includes("underweight")) return "REDUCE";
  if (
    d.includes("strong_sell") ||
    d.includes("sell") ||
    d.includes("avoid")
  ) {
    return "AVOID";
  }
  if (d.includes("hold") || d.includes("neutral") || d.includes("approve")) {
    return "HOLD";
  }
  return "WATCH";
}

export function mapInstitutionalRatings(
  view: Omit<ResearchView, "ratings" | "transparency" | "explainability" | "valuationTransparency">,
): InstitutionalRatingFramework {
  const financialStrength = fromStage(
    "financial_strength",
    "Financial Strength",
    view.financialStrength,
    ["financial_strength"],
    [
      dim("Debt", metric(view.financialStrength, "Debt"), "financial_strength metric"),
      dim(
        "Liquidity",
        metric(view.financialStrength, "Liquidity"),
        "financial_strength metric",
      ),
      dim(
        "Cash Flow",
        metric(view.financialStrength, "Cash Flow"),
        "financial_strength metric",
      ),
      dim("Coverage", metric(view.financialStrength, "Coverage"), "financial_strength metric"),
    ],
  );

  const valuationMethods = [
    "DCF",
    "Reverse DCF",
    "Residual Income",
    "EPV",
    "Dividend Discount Model",
    "Asset Based",
    "Relative Valuation",
    "Cross Method Consensus",
  ].map((name) =>
    dim(
      name,
      view.valuation.method.toLowerCase().includes(name.toLowerCase().split(" ")[0]!)
        ? view.valuation.method
        : "Unavailable",
      "Sub-method detail is not separately exposed on AnalyseResponse stage_summaries — not invented.",
    ),
  );

  const valuation: ModuleRating = {
    id: "valuation",
    title: "Valuation Rating",
    scoreOutOf10: scoreOutOf10FromExisting(view.recommendationStage.score),
    grade: letterGradeFromExistingScore(view.recommendationStage.score),
    confidence: confidenceDisplay(view.valuation.confidence),
    evidence: [
      `valuation.method=${view.valuation.method}`,
      `currentPrice=${view.valuation.currentPrice}`,
      `intrinsicValue=${view.valuation.intrinsicValue}`,
      `marginOfSafety=${view.valuation.marginOfSafety}`,
      `recommendation_stage.score=${view.recommendationStage.score}`,
    ],
    strengths: !isUnavailableDisplay(view.valuation.intrinsicValue)
      ? [`Intrinsic value present: ${view.valuation.intrinsicValue}`]
      : ["Data unavailable."],
    weaknesses: isUnavailableDisplay(view.valuation.marginOfSafety)
      ? ["Margin of safety unavailable from existing outputs"]
      : ["Data unavailable."],
    explanation: `Valuation Rating remaps existing valuation signals and recommendation-stage score. Individual engine lines show Unavailable unless the method string matches. Verdict uses existing MoS ${view.valuation.marginOfSafety}.`,
    dimensions: [
      dim("Current Price", view.valuation.currentPrice, "request/valuation_signals"),
      dim(
        "Intrinsic Value",
        view.valuation.intrinsicValue,
        "valuation_signals",
      ),
      dim(
        "Margin of Safety",
        view.valuation.marginOfSafety,
        "recommendation_summary",
      ),
      dim("Valuation Verdict", view.recommendationStage.label, "investment_recommendation"),
      ...valuationMethods,
    ],
    sourceStages: ["valuation", "investment_recommendation", "valuation_signals"],
  };

  const economicMoat = fromStage(
    "economic_moat",
    "Economic Moat",
    view.moat,
    ["economic_moat"],
    [
      dim("Brand", "Unavailable", "Moat sub-dimensions not on stage_summaries"),
      dim("Network Effect", "Unavailable", "Moat sub-dimensions not on stage_summaries"),
      dim("Switching Costs", "Unavailable", "Moat sub-dimensions not on stage_summaries"),
      dim("Scale", "Unavailable", "Moat sub-dimensions not on stage_summaries"),
      dim("Cost Advantage", "Unavailable", "Moat sub-dimensions not on stage_summaries"),
      dim(
        "Regulatory Advantage",
        "Unavailable",
        "Moat sub-dimensions not on stage_summaries",
      ),
      dim("Moat Label", view.moat.label, "economic_moat.label"),
      dim("Competitive Position", view.moat.decision, "economic_moat.decision"),
    ],
  );

  const managementQuality = fromStage(
    "management_quality",
    "Management Quality",
    view.management,
    ["management_quality"],
    [
      dim(
        "Governance",
        metric(view.management, "Governance"),
        "management_quality metric",
      ),
      dim(
        "Capital Allocation",
        "Unavailable",
        "RC3-001 — Capital Allocation is Book 04, not management_quality",
      ),
      dim("Execution", "Unavailable", "Not separately exposed on AnalyseResponse"),
      dim(
        "Shareholder Alignment",
        metric(view.management, "Shareholder Alignment"),
        "management_quality metric",
      ),
      dim("Integrity", "Unavailable", "Not separately exposed on AnalyseResponse"),
    ],
  );

  const earningsQuality = fromStage(
    "earnings_quality",
    "Earnings Quality",
    view.earnings,
    ["earnings_quality", "growth_quality"],
    [
      dim(
        "Revenue Stability",
        "Unavailable",
        "Not on earnings_quality stage — RC3-001 forbids growth_quality aliases",
      ),
      dim(
        "Profit Stability",
        "Unavailable",
        "Not on earnings_quality stage — RC3-001 forbids growth_quality aliases",
      ),
      dim(
        "Margin Stability",
        "Unavailable",
        "Not separately exposed on AnalyseResponse",
      ),
      dim(
        "Cash Flow Quality",
        metric(view.earnings, "Cash Conversion"),
        "earnings_quality metric",
      ),
      dim(
        "Consistency",
        metric(view.earnings, "Consistency"),
        "earnings_quality metric",
      ),
    ],
  );

  const financialFortress = fromStage(
    "financial_fortress",
    "Financial Fortress",
    view.financialStrength,
    ["financial_strength"],
    [
      dim("Debt", metric(view.financialStrength, "Debt"), "financial_strength"),
      dim(
        "Liquidity",
        metric(view.financialStrength, "Liquidity"),
        "financial_strength",
      ),
      dim(
        "Cash Generation",
        metric(view.financialStrength, "Cash Flow"),
        "financial_strength",
      ),
      dim("ROE", "Unavailable", "ROE not exposed on AnalyseResponse"),
      dim("ROCE", "Unavailable", "ROCE not exposed on AnalyseResponse"),
      dim(
        "Balance Sheet",
        view.financialStrength.label,
        "financial_strength.label",
      ),
    ],
    [],
    [],
    "Financial Fortress is a presentation lens on the existing financial_strength stage — not a second engine.",
  );

  const capitalAllocation = fromStage(
    "capital_allocation",
    "Capital Allocation",
    view.businessQuality,
    ["business_quality_aggregator"],
    [
      dim(
        "Reinvestment",
        "Unavailable",
        "RC3-001 — no dedicated capital_allocation stage on AnalyseResponse",
      ),
      dim("Dividend Policy", "Unavailable", "Not exposed on AnalyseResponse"),
      dim("Buybacks", "Unavailable", "Not exposed on AnalyseResponse"),
      dim(
        "Capital Efficiency",
        "Unavailable",
        "RC3-001 — never alias management_quality as Capital Allocation",
      ),
    ],
    [],
    [],
    "Capital Allocation presentation — Book 04 fields stay Unavailable until the API exposes them on business_quality_aggregator.",
  );

  const riskItems = [...view.risks, ...view.weaknesses].slice(0, 12);
  const riskAssessment: ModuleRating = {
    id: "risk_assessment",
    title: "Risk Assessment",
    scoreOutOf10: "Unavailable",
    grade: "Unavailable",
    confidence: "Unavailable",
    evidence: riskItems.length
      ? riskItems.map((r) => `Existing warning/weakness: ${r}`)
      : ["No stage warnings or weaknesses on AnalyseResponse"],
    strengths: riskItems.length === 0 ? ["No risk warnings surfaced"] : ["Data unavailable."],
    weaknesses: riskItems.length
      ? riskItems.slice(0, 6)
      : ["Dedicated risk score not available on AnalyseResponse"],
    explanation:
      "No dedicated risk pipeline stage. Evidence lists existing stage warnings and weakness fields only — score/grade remain Unavailable (not estimated).",
    dimensions: [
      dim(
        "Industry Risk",
        riskItems.find((r) => /industr/i.test(r)) ?? "Unavailable",
        "stage warnings",
      ),
      dim(
        "Competition",
        riskItems.find((r) => /compet/i.test(r)) ?? "Unavailable",
        "stage warnings",
      ),
      dim(
        "Regulatory Risk",
        riskItems.find((r) => /regulat/i.test(r)) ?? "Unavailable",
        "stage warnings",
      ),
      dim(
        "Technology Risk",
        riskItems.find((r) => /tech/i.test(r)) ?? "Unavailable",
        "stage warnings",
      ),
      dim(
        "Financial Risk",
        riskItems.find((r) => /financ|debt|liquidity/i.test(r)) ?? "Unavailable",
        "stage warnings",
      ),
    ],
    sourceStages: ["stage_summaries.warnings", "weaknesses"],
  };

  const aiCommittee: ModuleRating = {
    id: "ai_committee",
    title: "AI Committee",
    scoreOutOf10: scoreOutOf10FromExisting(view.committee.score),
    grade: letterGradeFromExistingScore(view.committee.score),
    confidence: confidenceDisplay(
      view.committeeConfidence != null
        ? String(view.committeeConfidence)
        : view.committee.confidence,
    ),
    evidence: [
      `committee.decision=${view.committeeDecision}`,
      `consensus=${view.committeeConsensus ?? "Unavailable"}`,
      `finalRecommendation=${view.committee.finalRecommendation}`,
      ...view.committee.supportingReasons.slice(0, 6).map((r) => `support: ${r}`),
      ...view.committee.opposingReasons.slice(0, 4).map((r) => `concern: ${r}`),
    ],
    strengths:
      view.committee.supportingReasons.length > 0
        ? view.committee.supportingReasons.slice(0, 6)
        : ["Data unavailable."],
    weaknesses:
      view.committee.opposingReasons.length > 0
        ? view.committee.opposingReasons.slice(0, 6)
        : ["Data unavailable."],
    explanation: `Committee display remapped from investment_committee stage and committee_summary. Recommendation: ${view.committee.finalRecommendation}.`,
    dimensions: [
      dim("Committee Consensus", view.committeeConsensus ?? "Unavailable", "committee_summary"),
      dim("Major Reasons", view.committee.supportingReasons[0] ?? "Unavailable", "strengths"),
      dim(
        "Minor Concerns",
        view.committee.opposingReasons[0] ?? "Unavailable",
        "weaknesses/risks",
      ),
      dim(
        "Recommendation",
        view.committee.finalRecommendation,
        "recommendation_summary",
      ),
    ],
    sourceStages: ["investment_committee", "committee_summary"],
  };

  const buffett = view.buffett;
  const buffettIndicator: ModuleRating = {
    id: "buffett_indicator",
    title: "Buffett Indicator",
    scoreOutOf10: scoreOutOf10FromExisting(
      buffett.overallRating === "Unavailable"
        ? "Unavailable"
        : // Convert letter overall back via scorecard business quality if needed
          view.businessQuality.score,
    ),
    grade: buffett.overallRating,
    confidence: confidenceDisplay(
      buffett.confidence.includes("=")
        ? buffett.confidence
        : buffett.confidence,
    ),
    evidence: [
      buffett.disclaimer,
      ...buffett.decisionMatrix.map(
        (m) => `${m.criterion}: ${m.state} — ${m.evidence}`,
      ),
    ],
    strengths: buffett.keyStrengths,
    weaknesses: buffett.keyWeaknesses,
    explanation: buffett.verdict,
    dimensions: [
      dim(
        "Circle of Competence",
        buffett.circleOfCompetence.verdict,
        "buffett report",
      ),
      dim("Economic Moat", buffett.economicMoat.verdict, "buffett report"),
      dim("Management", buffett.managementQuality.verdict, "buffett report"),
      dim(
        "Financial Fortress",
        buffett.financialFortress.verdict,
        "buffett report",
      ),
      dim(
        "Capital Allocation",
        buffett.capitalAllocation.verdict,
        "buffett report",
      ),
      dim(
        "Margin of Safety",
        buffett.intrinsicValue.marginOfSafety,
        "buffett/valuation",
      ),
      dim("Buffett Action", buffett.recommendation.action, "buffett recommendation"),
      dim("Buffett Verdict", buffett.verdict.slice(0, 160) + "…", "buffett verdict"),
    ],
    sourceStages: ["buffett_indicator_report", ...buffett.circleOfCompetence.evidenceSources],
  };

  // Prefer overall letter from buffett; score from BQ when overall is letter-only
  if (buffett.overallRating !== "Unavailable") {
    buffettIndicator.grade = buffett.overallRating;
    const bqScore = scoreOutOf10FromExisting(view.businessQuality.score);
    buffettIndicator.scoreOutOf10 =
      bqScore !== "Unavailable" ? bqScore : "Unavailable";
  }

  const modules = {
    financialStrength,
    valuation,
    economicMoat,
    managementQuality,
    earningsQuality,
    financialFortress,
    capitalAllocation,
    riskAssessment,
    aiCommittee,
    buffettIndicator,
  };

  const scorecard: ScorecardRow[] = [
    {
      module: "Financial Strength",
      scoreOutOf10: financialStrength.scoreOutOf10,
      grade: financialStrength.grade,
      confidence: financialStrength.confidence,
    },
    {
      module: "Valuation",
      scoreOutOf10: valuation.scoreOutOf10,
      grade: valuation.grade,
      confidence: valuation.confidence,
    },
    {
      module: "Economic Moat",
      scoreOutOf10: economicMoat.scoreOutOf10,
      grade: economicMoat.grade,
      confidence: economicMoat.confidence,
    },
    {
      module: "Management",
      scoreOutOf10: managementQuality.scoreOutOf10,
      grade: managementQuality.grade,
      confidence: managementQuality.confidence,
    },
    {
      module: "Earnings",
      scoreOutOf10: earningsQuality.scoreOutOf10,
      grade: earningsQuality.grade,
      confidence: earningsQuality.confidence,
    },
    {
      module: "Financial Fortress",
      scoreOutOf10: financialFortress.scoreOutOf10,
      grade: financialFortress.grade,
      confidence: financialFortress.confidence,
    },
    {
      module: "Capital Allocation",
      scoreOutOf10: capitalAllocation.scoreOutOf10,
      grade: capitalAllocation.grade,
      confidence: capitalAllocation.confidence,
    },
    {
      module: "Risk",
      scoreOutOf10: riskAssessment.scoreOutOf10,
      grade: riskAssessment.grade,
      confidence: riskAssessment.confidence,
    },
    {
      module: "AI Committee",
      scoreOutOf10: aiCommittee.scoreOutOf10,
      grade: aiCommittee.grade,
      confidence: aiCommittee.confidence,
    },
    {
      module: "Buffett Indicator",
      scoreOutOf10: buffettIndicator.scoreOutOf10,
      grade: buffettIndicator.grade,
      confidence: buffettIndicator.confidence,
    },
  ];

  const gradePool = scorecard
    .map((r) => r.grade)
    .filter((g) => g !== "Unavailable");
  const scorePool = scorecard
    .map((r) => r.scoreOutOf10)
    .filter((s) => s !== "Unavailable");
  const overallGrade = averageGradeFromExisting(gradePool);
  const overallScore = averageScoreOutOf10(scorePool);
  const actionSource =
    view.committee.finalRecommendation !== "Unavailable"
      ? view.committee.finalRecommendation
      : view.recommendation;
  const recommendation = investmentActionFromExisting(actionSource);

  const overall: OverallInvestmentRating = {
    scoreOutOf10: overallScore,
    grade: overallGrade,
    confidence: confidenceDisplay(
      view.recommendationConfidence != null
        ? String(view.recommendationConfidence)
        : view.recommendationStage.confidence,
    ),
    stars: starsFromGrade(overallGrade),
    investmentQuality: view.recommendationStage.label,
    businessQuality: view.businessQualityLabel,
    valuationQuality: view.valuation.method,
    riskLevel:
      riskAssessment.weaknesses[0] &&
      riskAssessment.weaknesses[0] !== "Data unavailable."
        ? "See Risk Assessment evidence"
        : "Unavailable",
    expectedLongTermQuality: "Unavailable",
    recommendation,
    recommendationReasoning: `Mapped from existing decision "${actionSource}". Overall grade ${overallGrade} averages available module letter bands only.`,
    explanation: `Overall Investment Rating is a display aggregate of available module grades/scores from existing analyse outputs for ${view.company} (${view.ticker}). No new engine scores were computed.`,
  };

  scorecard.push({
    module: "Overall Investment Rating",
    scoreOutOf10: overall.scoreOutOf10,
    grade: overall.grade,
    confidence: overall.confidence,
  });

  return {
    kind: "institutional_rating_framework",
    disclaimer: DISCLAIMER,
    modules,
    scorecard,
    overall,
  };
}
