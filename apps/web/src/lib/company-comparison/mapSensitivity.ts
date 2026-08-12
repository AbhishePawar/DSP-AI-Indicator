/**
 * Sensitivity Panel — coverage / evidence / confidence sensitivity.
 * Frozen /analyse does not expose certified sensitivity surfaces →
 * Analysis unavailable. for analytical sensitivity; inputs remain honest.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import {
  ANALYSIS_UNAVAILABLE,
  COVERAGE_UNAVAILABLE,
  DATA_UNAVAILABLE,
} from "./constants";
import type { SensitivityCell } from "./types";

export function mapSensitivityPanel(views: ResearchView[]): SensitivityCell[] {
  return views.map((v) => {
    const succeeded = v.stages.filter((s) => s.status === "succeeded").length;
    const total = v.stages.length;
    const coverageInput =
      total === 0
        ? COVERAGE_UNAVAILABLE
        : `${succeeded}/${total} stages succeeded (input only)`;
    const evidenceCount = Object.values(v.evidenceCounts ?? {}).reduce(
      (a, b) => a + (typeof b === "number" ? b : 0),
      0,
    );
    const evidenceInput =
      evidenceCount > 0
        ? `${evidenceCount} evidence count total (input only)`
        : DATA_UNAVAILABLE;
    const confidenceInput =
      v.recommendationConfidence != null
        ? `${Math.round(v.recommendationConfidence * 100)}% (input only)`
        : DATA_UNAVAILABLE;

    return {
      symbol: v.ticker,
      coverageInput,
      evidenceInput,
      confidenceInput,
      coverageSensitivity: ANALYSIS_UNAVAILABLE,
      evidenceSensitivity: ANALYSIS_UNAVAILABLE,
      confidenceSensitivity: ANALYSIS_UNAVAILABLE,
      note: "Sensitivity analysis is not certified on frozen /api/v1/analyse. Inputs shown for transparency; sensitivity outputs remain Analysis unavailable.",
    };
  });
}
