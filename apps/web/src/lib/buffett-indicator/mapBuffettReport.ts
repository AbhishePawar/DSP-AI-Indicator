/**
 * ARCH-001 / P1-05 — Buffett Indicator Analysis report mapper.
 *
 * Display-only presentation of server-authoritative pipeline stages:
 * - No recalculation of ROE, ROCE, DCF, IV, MoS, debt, FCF, moat, etc.
 * - No client invention of overall Buffett rating / investment conclusion
 * - Overall rating remaps existing business_quality_aggregator score 1:1
 * - Fully deterministic
 */

import type { ResearchView, StageSectionView } from "@/lib/research/mapResearchView";
import type {
  BuffettAction,
  BuffettMatrixItem,
  BuffettMatrixState,
  BuffettReportView,
  BuffettScorecardRow,
  BuffettSubsection,
} from "./types";

const DISCLAIMER =
  "Buffett Indicator Analysis displays server-authoritative /api/v1/analyse stage outputs only. It does not recalculate fundamentals, invent Buffett scores, or override recommendations. Research Mode — not investment advice.";

function isUnavailable(value: string | null | undefined): boolean {
  if (value == null) return true;
  const v = value.trim().toLowerCase();
  return (
    v === "" ||
    v === "unavailable" ||
    v === "data unavailable." ||
    v === "—" ||
    v === "n/a"
  );
}

function stageAvailable(section: StageSectionView): boolean {
  return (
    section.status === "succeeded" &&
    !isUnavailable(section.score) &&
    section.score.toLowerCase() !== "data unavailable."
  );
}

/**
 * Letter-band formatting of an *existing* 0–100 stage score for display.
 * Not a new scoring engine — display taxonomy only.
 */
export function letterGradeFromExistingScore(scoreText: string): string {
  if (isUnavailable(scoreText)) return "Unavailable";
  const cleaned = scoreText.replace(/%/g, "").trim();
  let n = Number(cleaned);
  if (!Number.isFinite(n)) {
    // Fall back to existing label text when score is non-numeric.
    return scoreText;
  }
  // Some stage summaries use 0–1 confidence-like scores; band as percent.
  if (n >= 0 && n <= 1) n = n * 100;
  if (n >= 90) return "A+";
  if (n >= 80) return "A";
  if (n >= 70) return "B+";
  if (n >= 60) return "B";
  if (n >= 50) return "C";
  if (n >= 40) return "D";
  return "F";
}

/** Map existing recommendation / committee decision → Buffett Action vocabulary. */
export function buffettActionFromExistingDecision(decision: string): BuffettAction {
  if (isUnavailable(decision)) return "Unavailable";
  const d = decision.toLowerCase().replace(/[\s-]+/g, "_");
  if (
    d.includes("strong_buy") ||
    d === "buy" ||
    d.includes("accumulate") ||
    d.includes("strong buy")
  ) {
    return "BUY";
  }
  if (d.includes("strong_sell") || d.includes("sell") || d.includes("avoid")) {
    return "AVOID";
  }
  if (d.includes("watch") || d.includes("reduce") || d.includes("underweight")) {
    return "WATCH";
  }
  if (d.includes("hold") || d.includes("neutral")) {
    return "HOLD";
  }
  if (d.includes("buy")) return "BUY";
  return "WATCH";
}

function metricValue(section: StageSectionView, label: string): string {
  const hit = section.metrics.find(
    (m) => m.label.toLowerCase() === label.toLowerCase(),
  );
  return hit?.value ?? "Unavailable";
}

function subsection(
  title: string,
  bullets: string[],
  verdict: string,
  evidenceSources: string[],
): BuffettSubsection {
  return {
    title,
    bullets: bullets.length ? bullets : ["Data unavailable."],
    verdict,
    evidenceSources,
  };
}

function matrixItem(
  criterion: string,
  state: BuffettMatrixState,
  evidence: string,
): BuffettMatrixItem {
  return { criterion, state, evidence };
}

function scorecardRow(
  dimension: string,
  grade: string,
  evidence: string,
): BuffettScorecardRow {
  return { dimension, grade, evidence };
}

export function mapBuffettReport(
  view: Omit<ResearchView, "buffett" | "ratings" | "transparency" | "explainability" | "valuationTransparency">,
): BuffettReportView {
  const moat = view.moat;
  const mgmt = view.management;
  const strength = view.financialStrength;
  const earnings = view.earnings;
  const growth = view.growth;
  const financial = view.financial;
  const bq = view.businessQuality;
  const valuation = view.valuation;

  const circle = subsection(
    "Circle of Competence",
    [
      `Financial stage status: ${financial.status}`,
      `Financial summary: ${financial.label}`,
      `Growth / reinvestment label: ${growth.label}`,
      "Business free-text description is not exposed on AnalyseResponse — simplicity assessed from stage availability only.",
    ],
    stageAvailable(financial)
      ? `Financial analysis is available (${financial.label}). Industry narrative depth: Data unavailable from AnalyseResponse.`
      : "Unable to assess circle of competence — financial stage evidence unavailable.",
    ["financial", "growth_quality"],
  );

  const economicMoat = subsection(
    "Economic Moat",
    [
      `Moat label: ${moat.label}`,
      `Competitive position: ${moat.decision}`,
      `Moat score (existing): ${moat.score}`,
      `Confidence: ${moat.confidence}`,
    ],
    stageAvailable(moat)
      ? `Existing economic moat analysis indicates ${moat.label}.`
      : "Economic moat evidence unavailable from existing stage summary.",
    ["economic_moat"],
  );

  const managementQuality = subsection(
    "Management Quality",
    [
      `Management label: ${mgmt.label}`,
      `Capital allocation / governance fields: ${mgmt.decision}`,
      `Score (existing): ${mgmt.score}`,
      `Confidence: ${mgmt.confidence}`,
    ],
    stageAvailable(mgmt)
      ? `Existing management quality analysis indicates ${mgmt.label}.`
      : "Management quality evidence unavailable from existing stage summary.",
    ["management_quality"],
  );

  const financialFortress = subsection(
    "Financial Fortress",
    [
      `Financial strength label: ${strength.label}`,
      `Debt (stage field): ${metricValue(strength, "Debt")}`,
      `Liquidity (stage field): ${metricValue(strength, "Liquidity")}`,
      `Cash flow (stage field): ${metricValue(strength, "Cash Flow")}`,
      `Score (existing): ${strength.score}`,
      "ROE / ROCE are not separately exposed on AnalyseResponse — not restated here.",
    ],
    stageAvailable(strength)
      ? `Existing financial strength analysis indicates ${strength.label}.`
      : "Financial fortress evidence unavailable from existing stage summary.",
    ["financial_strength"],
  );

  const earningsPredictability = subsection(
    "Earnings Predictability",
    [
      `Earnings quality label: ${earnings.label}`,
      `Consistency field: ${metricValue(earnings, "Consistency")}`,
      `Cash conversion field: ${metricValue(earnings, "Cash Conversion")}`,
      `Growth revenue field: ${metricValue(growth, "Revenue Growth")}`,
      `Growth profit field: ${metricValue(growth, "Profit Growth")}`,
    ],
    stageAvailable(earnings)
      ? `Existing earnings quality analysis indicates ${earnings.label}.`
      : "Earnings predictability evidence unavailable from existing stage summary.",
    ["earnings_quality", "growth_quality"],
  );

  const capitalAllocation = subsection(
    "Capital Allocation",
    [
      `Management capital-allocation field: ${metricValue(mgmt, "Capital Allocation")}`,
      `Management label: ${mgmt.label}`,
      `Growth reinvestment field: ${metricValue(growth, "Reinvestment")}`,
      "Dividends / buybacks are not separately exposed on AnalyseResponse — not invented.",
    ],
    stageAvailable(mgmt)
      ? `Capital allocation evidence drawn from management quality stage (${mgmt.label}).`
      : "Capital allocation evidence unavailable from existing stage summary.",
    ["management_quality", "growth_quality"],
  );

  const intrinsic = {
    ...subsection(
      "Intrinsic Value & Margin of Safety",
      [
        `Current price (request/signals): ${valuation.currentPrice}`,
        `Intrinsic value (existing signals): ${valuation.intrinsicValue}`,
        `Margin of safety (existing recommendation summary): ${valuation.marginOfSafety}`,
        `Valuation method/label: ${valuation.method}`,
        `Valuation confidence: ${valuation.confidence}`,
      ],
      !isUnavailable(valuation.marginOfSafety) ||
        !isUnavailable(valuation.intrinsicValue)
        ? `Existing valuation outputs show price ${valuation.currentPrice}, intrinsic value ${valuation.intrinsicValue}, MoS ${valuation.marginOfSafety}.`
        : "Intrinsic value / margin of safety unavailable from existing valuation outputs.",
      ["valuation", "recommendation_summary", "valuation_signals"],
    ),
    currentPrice: valuation.currentPrice,
    intrinsicValue: valuation.intrinsicValue,
    marginOfSafety: valuation.marginOfSafety,
  };

  const longTermRisks = subsection(
    "Long-Term Risks",
    [
      ...(view.risks.length
        ? view.risks.slice(0, 8)
        : ["No stage warnings surfaced on AnalyseResponse."]),
      ...(view.weaknesses.length
        ? view.weaknesses.slice(0, 4)
        : ["No stage failure weaknesses surfaced."]),
      "Competition / regulation / technology disruption narratives are not fabricated when absent from stage warnings.",
    ],
    view.risks.length || view.weaknesses.length
      ? "Risks listed above are taken from existing stage warnings and weakness fields only."
      : "Long-term risk detail unavailable beyond empty stage warning lists.",
    ["stage_summaries.warnings", "weaknesses"],
  );

  const decisionMatrix: BuffettMatrixItem[] = [
    matrixItem(
      "Easy to Understand Business",
      stageAvailable(financial) ? "met" : "unavailable",
      `Evidence: financial stage status=${financial.status}, label=${financial.label}`,
    ),
    matrixItem(
      "Durable Economic Moat",
      stageAvailable(moat) ? "met" : "unavailable",
      `Evidence: economic_moat label=${moat.label}, score=${moat.score}`,
    ),
    matrixItem(
      "Honest Management",
      stageAvailable(mgmt) ? "met" : "unavailable",
      `Evidence: management_quality label=${mgmt.label}`,
    ),
    matrixItem(
      "Strong Financial Position",
      stageAvailable(strength) ? "met" : "unavailable",
      `Evidence: financial_strength label=${strength.label}`,
    ),
    matrixItem(
      "Consistent Earnings",
      stageAvailable(earnings) ? "met" : "unavailable",
      `Evidence: earnings_quality label=${earnings.label}`,
    ),
    matrixItem(
      "Low Debt",
      !isUnavailable(metricValue(strength, "Debt")) || stageAvailable(strength)
        ? stageAvailable(strength)
          ? "met"
          : "unavailable"
        : "unavailable",
      `Evidence: financial_strength Debt field=${metricValue(strength, "Debt")} (no client debt recalculation)`,
    ),
    matrixItem(
      "High ROE",
      "unavailable",
      "Evidence: ROE is not separately exposed on AnalyseResponse — not invented.",
    ),
    matrixItem(
      "Positive Free Cash Flow",
      !isUnavailable(metricValue(strength, "Cash Flow"))
        ? "met"
        : "unavailable",
      `Evidence: financial_strength Cash Flow field=${metricValue(strength, "Cash Flow")} (no client FCF recalculation)`,
    ),
    matrixItem(
      "Attractive Valuation",
      !isUnavailable(valuation.intrinsicValue) ||
        !isUnavailable(valuation.currentPrice)
        ? "met"
        : "unavailable",
      `Evidence: price=${valuation.currentPrice}, IV=${valuation.intrinsicValue}`,
    ),
    matrixItem(
      "Margin of Safety",
      !isUnavailable(valuation.marginOfSafety) ? "met" : "unavailable",
      `Evidence: marginOfSafety=${valuation.marginOfSafety} from existing recommendation/signals`,
    ),
  ];

  const scorecard: BuffettScorecardRow[] = [
    scorecardRow(
      "Business Quality",
      letterGradeFromExistingScore(bq.score),
      `business_quality_aggregator score=${bq.score}, label=${bq.label}`,
    ),
    scorecardRow(
      "Economic Moat",
      letterGradeFromExistingScore(moat.score),
      `economic_moat score=${moat.score}`,
    ),
    scorecardRow(
      "Management",
      letterGradeFromExistingScore(mgmt.score),
      `management_quality score=${mgmt.score}`,
    ),
    scorecardRow(
      "Financial Strength",
      letterGradeFromExistingScore(strength.score),
      `financial_strength score=${strength.score}`,
    ),
    scorecardRow(
      "Earnings Quality",
      letterGradeFromExistingScore(earnings.score),
      `earnings_quality score=${earnings.score}`,
    ),
    scorecardRow(
      "Capital Allocation",
      letterGradeFromExistingScore(mgmt.score),
      `Mapped from management_quality (capital allocation not a separate pipeline score)`,
    ),
    scorecardRow(
      "Valuation",
      !isUnavailable(valuation.method) || !isUnavailable(valuation.intrinsicValue)
        ? letterGradeFromExistingScore(
            view.recommendationStage.score !== "Unavailable"
              ? view.recommendationStage.score
              : "Unavailable",
          )
        : "Unavailable",
      `valuation method=${valuation.method}; recommendation stage score=${view.recommendationStage.score}`,
    ),
    scorecardRow(
      "Margin of Safety",
      !isUnavailable(valuation.marginOfSafety)
        ? valuation.marginOfSafety
        : "Unavailable",
      `Existing MoS display=${valuation.marginOfSafety}`,
    ),
  ];

  // P1-05 — overall Buffett rating is a 1:1 display remap of the server
  // business_quality_aggregator score. Never invent by averaging letter grades.
  const overallRating = letterGradeFromExistingScore(bq.score);

  const actionSource =
    view.committee.finalRecommendation !== "Unavailable"
      ? view.committee.finalRecommendation
      : view.recommendation;
  const action = buffettActionFromExistingDecision(actionSource);

  const keyStrengths = view.strengths.slice(0, 8);
  const keyWeaknesses = view.weaknesses.slice(0, 8);

  const metCount = decisionMatrix.filter((m) => m.state === "met").length;
  const verdict = [
    `Based solely on existing platform analysis for ${view.company} (${view.ticker}),`,
    `${metCount} of ${decisionMatrix.length} Buffett-style checklist items have supporting stage evidence.`,
    `Business quality label: ${view.businessQualityLabel}.`,
    `Economic moat: ${moat.label}.`,
    `Management: ${mgmt.label}.`,
    `Financial strength: ${strength.label}.`,
    `Earnings quality: ${earnings.label}.`,
    `Margin of safety (existing): ${valuation.marginOfSafety}.`,
    `Final mapped recommendation: ${actionSource}.`,
    "No fundamentals were recalculated in this report section.",
  ].join(" ");

  const confidenceParts = [
    view.recommendationConfidence != null
      ? `recommendation confidence=${view.recommendationConfidence}`
      : null,
    view.committeeConfidence != null
      ? `committee confidence=${view.committeeConfidence}`
      : null,
    bq.confidence !== "Unavailable" ? `BQ confidence=${bq.confidence}` : null,
  ].filter(Boolean);

  return {
    kind: "buffett_indicator_report",
    circleOfCompetence: circle,
    economicMoat,
    managementQuality,
    financialFortress,
    earningsPredictability,
    capitalAllocation,
    intrinsicValue: intrinsic,
    longTermRisks,
    decisionMatrix,
    scorecard: [
      ...scorecard,
      scorecardRow(
        "Overall Buffett Rating",
        overallRating,
        `Server-authoritative business_quality_aggregator score=${bq.score} (P1-05 display remap only).`,
      ),
    ],
    overallRating,
    verdict,
    recommendation: {
      businessQuality: view.businessQualityLabel,
      investmentQuality: view.recommendationStage.label,
      currentValuation: `${valuation.currentPrice} vs IV ${valuation.intrinsicValue}`,
      marginOfSafety: valuation.marginOfSafety,
      action,
      actionEvidence: `Mapped from existing decision "${actionSource}" (committee/recommendation summary).`,
    },
    keyStrengths: keyStrengths.length ? keyStrengths : ["Data unavailable."],
    keyWeaknesses: keyWeaknesses.length ? keyWeaknesses : ["Data unavailable."],
    confidence: confidenceParts.length
      ? confidenceParts.join("; ")
      : "Unavailable",
    disclaimer: DISCLAIMER,
  };
}
