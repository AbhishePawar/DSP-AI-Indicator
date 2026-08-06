/**
 * Reshapes already-computed `SavedAnalysis.response.payload` (the
 * `/api/v1/analyse` composition envelope) into the minimal Research-Object
 * section shape the Portfolio Intelligence Engine's `research_objects`
 * input expects (`margin_of_safety` / `recommendation` / `business_quality`
 * sections, mirroring `dsp_platform.research_object.builder`).
 *
 * This performs **zero computation** — it only relabels fields that the
 * composition pipeline already computed and the user already saved by
 * analysing that company in the Company Workspace. No valuation, quality,
 * or confidence score is invented or recalculated on the client.
 */

import type { SavedAnalysis } from "@/lib/persistence/types";

function stageScore(
  payload: SavedAnalysis["response"],
  stage: string,
): number | null {
  const summaries = payload?.payload?.stage_summaries ?? [];
  const found = summaries.find((s) => s.stage === stage && s.has_result);
  return typeof found?.score === "number" ? found.score : null;
}

export function buildResearchObjectsFromSavedAnalyses(
  savedAnalyses: SavedAnalysis[],
): Record<string, unknown> | null {
  const out: Record<string, unknown> = {};
  for (const analysis of savedAnalyses) {
    const ticker = analysis.ticker?.trim().toUpperCase();
    const payload = analysis.response?.payload;
    if (!ticker || !payload) continue;

    const recSummary = payload.recommendation_summary ?? null;
    const marginOfSafety =
      typeof recSummary?.margin_of_safety === "number" ? recSummary.margin_of_safety : null;
    const confidence = recSummary?.confidence ?? null;
    const qualityScore = stageScore(analysis.response, "business_quality_aggregator");

    const doc: Record<string, unknown> = { metadata: { ticker } };
    if (marginOfSafety !== null) {
      doc.margin_of_safety = { available: true, payload: { margin_of_safety: marginOfSafety } };
    }
    if (confidence !== null || marginOfSafety !== null) {
      doc.recommendation = {
        available: true,
        payload: { confidence, margin_of_safety: marginOfSafety },
      };
    }
    if (qualityScore !== null) {
      doc.business_quality = { available: true, payload: { score: qualityScore } };
    }
    // Only include holdings with at least one usable signal.
    if (Object.keys(doc).length > 1) {
      out[ticker] = doc;
    }
  }
  return Object.keys(out).length > 0 ? out : null;
}
