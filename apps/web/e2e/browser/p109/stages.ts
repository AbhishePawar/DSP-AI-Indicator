import { test } from "@playwright/test";

/** Hard-gate stage names — appear in Playwright step titles and failure output. */
export const P109_STAGES = [
  "LOGIN",
  "ANALYSIS",
  "VALUATION",
  "BUFFETT",
  "PROVENANCE",
  "EXPORT",
] as const;

export type P109Stage = (typeof P109_STAGES)[number];

export type P109StageRecord = {
  stage: P109Stage;
  status: "passed";
};

/**
 * Wrap a business stage so CI failures name the stage explicitly.
 * Does not catch errors — a thrown assertion still fails the hard gate.
 */
export async function p109Stage<T>(
  stage: P109Stage,
  fn: () => Promise<T>,
): Promise<T> {
  return test.step(`[P1-09 ${stage}]`, fn);
}
