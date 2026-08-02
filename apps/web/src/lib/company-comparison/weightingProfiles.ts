/**
 * Comparison Weighting Profiles — presentation emphasis only.
 * NEVER alters analytical scores, Winner Matrix numerics, or recommendations.
 */

import type { WinnerMatrixDimensionId } from "./types";

export type WeightingProfileId =
  | "equal"
  | "quality"
  | "value"
  | "growth"
  | "conservative"
  | "buffett";

/** Dimensions that may receive visual emphasis under a profile. */
export type EmphasisDimensionId =
  | WinnerMatrixDimensionId
  | "researchConfidence"
  | "evidenceStrength"
  | "overallPosition";

export type WeightingProfile = {
  id: WeightingProfileId;
  label: string;
  description: string;
  /** Relative presentation emphasis (1 = baseline). Does not rescale scores. */
  emphasis: Partial<Record<EmphasisDimensionId, number>>;
};

export const WEIGHTING_PROFILES: readonly WeightingProfile[] = [
  {
    id: "equal",
    label: "Equal",
    description: "Balanced presentation emphasis across all dimensions.",
    emphasis: {},
  },
  {
    id: "quality",
    label: "Quality",
    description: "Emphasizes Business Quality, Management, and Moat visually.",
    emphasis: {
      businessQuality: 1.4,
      management: 1.3,
      moat: 1.3,
      financialStrength: 1.15,
    },
  },
  {
    id: "value",
    label: "Value",
    description: "Emphasizes Valuation and Overall Position visually.",
    emphasis: {
      valuation: 1.45,
      overall: 1.2,
      overallPosition: 1.25,
      confidence: 1.1,
    },
  },
  {
    id: "growth",
    label: "Growth",
    description: "Emphasizes Growth and related quality signals visually.",
    emphasis: {
      growth: 1.45,
      businessQuality: 1.15,
      overall: 1.1,
    },
  },
  {
    id: "conservative",
    label: "Conservative",
    description: "Emphasizes Risk, Financial Strength, and Evidence Strength visually.",
    emphasis: {
      risk: 1.4,
      financialStrength: 1.35,
      evidenceStrength: 1.3,
      researchConfidence: 1.25,
      confidence: 1.2,
    },
  },
  {
    id: "buffett",
    label: "Buffett-style",
    description:
      "Emphasizes Moat, Management, Valuation, and Business Quality visually. Presentation only — not a buy endorsement.",
    emphasis: {
      moat: 1.4,
      management: 1.35,
      valuation: 1.35,
      businessQuality: 1.3,
      capitalAllocation: 1.2,
    },
  },
] as const;

export function getWeightingProfile(
  id: WeightingProfileId | string | null | undefined,
): WeightingProfile {
  const hit = WEIGHTING_PROFILES.find((p) => p.id === id);
  return hit ?? WEIGHTING_PROFILES[0]!;
}

/**
 * Presentation emphasis class for a dimension under the active profile.
 * Raw score displays must remain unchanged regardless of return value.
 */
export function presentationEmphasis(
  profile: WeightingProfile,
  dimension: EmphasisDimensionId,
): "highlight" | "normal" | "deemphasize" {
  if (profile.id === "equal") return "normal";
  const weight = profile.emphasis[dimension];
  if (weight == null) return "deemphasize";
  if (weight >= 1.25) return "highlight";
  if (weight >= 1.1) return "normal";
  return "deemphasize";
}

/** Guard: weighting must never mutate numeric score arrays. */
export function assertWeightingIsPresentationOnly(
  rawScoresBefore: readonly (number | null)[],
  rawScoresAfter: readonly (number | null)[],
): boolean {
  if (rawScoresBefore.length !== rawScoresAfter.length) return false;
  return rawScoresBefore.every((v, i) => v === rawScoresAfter[i]);
}
