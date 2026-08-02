/**
 * Evidence Strength Meter — Strong / Moderate / Limited / Data unavailable.
 * Derived only from existing research fields. Never fabricates coverage.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import {
  COVERAGE_UNAVAILABLE,
  DATA_UNAVAILABLE,
} from "./constants";
import { isUnavailableDisplay } from "./ranking";
import type { EvidenceStrengthMeter } from "./types";

function stageCompleteness(view: ResearchView): {
  display: string;
  ratio: number | null;
} {
  const total = view.stages.length;
  if (total === 0) return { display: COVERAGE_UNAVAILABLE, ratio: null };
  const succeeded = view.stages.filter((s) => s.status === "succeeded").length;
  return {
    display: `${succeeded}/${total} stages succeeded`,
    ratio: succeeded / total,
  };
}

function evidenceCount(view: ResearchView): number {
  return Object.values(view.evidenceCounts ?? {}).reduce(
    (a, b) => a + (typeof b === "number" ? b : 0),
    0,
  );
}

/**
 * Map evidence strength from coverage, freshness, completeness,
 * source provenance, and research confidence — existing fields only.
 */
export function mapEvidenceStrengthMeters(
  views: ResearchView[],
): EvidenceStrengthMeter[] {
  return views.map((v) => {
    const completeness = stageCompleteness(v);
    const count = evidenceCount(v);
    const confidence = v.recommendationConfidence;
    const freshness = v.analysedAt ?? DATA_UNAVAILABLE;
    const sources: string[] = [];
    if (v.correlationId) sources.push(`correlation_id=${v.correlationId}`);
    if (v.pipelineVersion) sources.push(`pipeline=${v.pipelineVersion}`);
    if (v.platformVersion) sources.push(`platform=${v.platformVersion}`);
    const sourceQuality =
      sources.length > 0 ? sources.join("; ") : DATA_UNAVAILABLE;

    const coverageDisplay = completeness.display;
    const confidenceDisplay =
      confidence != null
        ? `${Math.round(confidence * 100)}%`
        : DATA_UNAVAILABLE;

    // Honest unavailable when mandatory signals are missing.
    if (
      completeness.ratio == null &&
      count === 0 &&
      confidence == null &&
      isUnavailableDisplay(freshness)
    ) {
      return {
        symbol: v.ticker,
        level: DATA_UNAVAILABLE,
        coverage: COVERAGE_UNAVAILABLE,
        freshness: DATA_UNAVAILABLE,
        completeness: COVERAGE_UNAVAILABLE,
        sourceQuality: DATA_UNAVAILABLE,
        researchConfidence: DATA_UNAVAILABLE,
        rationale:
          "Insufficient existing research fields to classify evidence strength.",
      };
    }

    let score = 0;
    let signals = 0;
    if (completeness.ratio != null) {
      signals += 1;
      score += completeness.ratio;
    }
    if (count > 0) {
      signals += 1;
      score += count >= 6 ? 1 : count >= 3 ? 0.65 : 0.35;
    }
    if (confidence != null) {
      signals += 1;
      score += confidence;
    }
    if (!isUnavailableDisplay(freshness)) {
      signals += 1;
      score += 0.75;
    }
    if (sources.length >= 2) {
      signals += 1;
      score += 0.8;
    }

    if (signals === 0) {
      return {
        symbol: v.ticker,
        level: DATA_UNAVAILABLE,
        coverage: coverageDisplay,
        freshness,
        completeness: completeness.display,
        sourceQuality,
        researchConfidence: confidenceDisplay,
        rationale: "Data unavailable.",
      };
    }

    const avg = score / signals;
    let level: EvidenceStrengthMeter["level"];
    if (avg >= 0.75) level = "Strong";
    else if (avg >= 0.5) level = "Moderate";
    else level = "Limited";

    return {
      symbol: v.ticker,
      level,
      coverage: coverageDisplay,
      freshness,
      completeness: completeness.display,
      sourceQuality,
      researchConfidence: confidenceDisplay,
      rationale: `Classified ${level} from ${signals} existing research signals (coverage, evidence counts, confidence, freshness, provenance). Presentation classification only — not a new analytical engine.`,
    };
  });
}
