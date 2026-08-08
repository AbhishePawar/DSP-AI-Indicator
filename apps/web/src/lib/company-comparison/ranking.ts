/**
 * EPIC-012/013 — Presentation ranking helpers.
 * Parse existing server score text for medal assignment only.
 * Never invent, estimate, or substitute missing scores.
 */

import {
  DATA_UNAVAILABLE,
  UNABLE_TO_CALCULATE,
} from "./constants";
import type { Medal } from "./types";

export function isUnavailableDisplay(value: string | null | undefined): boolean {
  if (value == null) return true;
  const v = value.trim().toLowerCase();
  return (
    v === "" ||
    v === "unavailable" ||
    v === "data unavailable." ||
    v === "data unavailable" ||
    v === "unable to calculate." ||
    v === "unable to calculate" ||
    v === "coverage unavailable." ||
    v === "analysis pending." ||
    v === "analysis unavailable." ||
    v === "—" ||
    v === "n/a" ||
    v === "null"
  );
}

/** Parse an existing score string into a comparable number, or null. */
export function parseExistingScore(scoreText: string | null | undefined): number | null {
  if (isUnavailableDisplay(scoreText)) return null;
  const cleaned = String(scoreText)
    .replace(/%/g, "")
    .replace(/\/\s*10/g, "")
    .trim();
  const n = Number(cleaned);
  if (!Number.isFinite(n)) return null;
  // Confidence-like 0–1 → percent scale for ranking consistency.
  if (n >= 0 && n <= 1) return n * 100;
  return n;
}

/**
 * Assign medals from existing numeric scores only.
 * Ties share the same medal tier; missing scores get no medal.
 */
export function assignMedals(
  entries: { symbol: string; numeric: number | null }[],
): Record<string, Medal> {
  const out: Record<string, Medal> = {};
  for (const e of entries) out[e.symbol] = null;

  const ranked = entries
    .filter((e): e is { symbol: string; numeric: number } => e.numeric != null)
    .sort((a, b) => b.numeric - a.numeric);

  if (ranked.length === 0) return out;

  const tiers: Medal[] = ["gold", "silver", "bronze"];
  let tierIdx = 0;
  let i = 0;
  while (i < ranked.length && tierIdx < tiers.length) {
    const score = ranked[i]!.numeric;
    const medal = tiers[tierIdx]!;
    while (i < ranked.length && ranked[i]!.numeric === score) {
      out[ranked[i]!.symbol] = medal;
      i += 1;
    }
    tierIdx += 1;
  }
  return out;
}

export function honestDisplay(value: string | null | undefined): string {
  if (isUnavailableDisplay(value)) return DATA_UNAVAILABLE;
  return String(value);
}

export function unableOrUnavailable(
  reason: "missing" | "incomplete",
): string {
  return reason === "incomplete" ? UNABLE_TO_CALCULATE : DATA_UNAVAILABLE;
}
