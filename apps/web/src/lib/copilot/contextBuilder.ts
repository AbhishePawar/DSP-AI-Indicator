/**
 * CopilotContextBuilder — deterministic research context from AnalyseResponse.
 * No scoring or invented fields.
 */

import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import {
  mapAnalyseResponse,
  type IntelligenceView,
} from "@/lib/intelligence/mapResponse";
import type {
  CopilotCompanyContext,
  StageFieldSummary,
} from "./types";

function stageSummary(
  view: IntelligenceView,
  stageName: string,
): StageFieldSummary {
  const stage = view.stages.find((s) => s.stage === stageName);
  if (!stage) {
    return {
      status: null,
      label: null,
      decision: null,
      score: null,
      confidence: null,
      available: false,
    };
  }
  const available = Boolean(
    stage.label ||
      stage.decision ||
      stage.score != null ||
      stage.confidence != null ||
      stage.status === "succeeded",
  );
  return {
    status: stage.status ?? null,
    label: stage.label ?? null,
    decision: stage.decision ?? null,
    score: stage.score ?? null,
    confidence: stage.confidence ?? null,
    available,
  };
}

export function buildCopilotContext(
  request: AnalyseRequest | null,
  response: AnalyseResponse | null,
): CopilotCompanyContext | null {
  if (!response) return null;
  const view = mapAnalyseResponse(response);
  const ticker = (request?.ticker || "—").toUpperCase();
  return {
    company: request?.company || ticker,
    ticker,
    exchange: request?.exchange ?? null,
    recommendation: view.recommendation,
    recommendationConfidence: view.recommendationConfidence,
    intrinsicValue:
      request?.valuation_signals?.intrinsic_value_per_share ?? null,
    currentPrice:
      request?.current_market_price ??
      request?.valuation_signals?.current_market_price ??
      null,
    marginOfSafety: view.marginOfSafety,
    economicMoat: stageSummary(view, "economic_moat"),
    managementQuality: stageSummary(view, "management_quality"),
    financialStrength: stageSummary(view, "financial_strength"),
    earningsQuality: stageSummary(view, "earnings_quality"),
    growthQuality: stageSummary(view, "growth_quality"),
    businessQualityLabel: view.businessQualityLabel,
    businessQualityScore: view.businessQualityScore,
    committeeDecision: view.committeeDecision,
    committeeConfidence: view.committeeConfidence,
    committeeConsensus: view.committeeConsensus,
    strengths: view.strengths,
    weaknesses: view.weaknesses,
    risks: view.risks,
    minorityNotes: view.minorityNotes,
    hasSession: true,
  };
}
