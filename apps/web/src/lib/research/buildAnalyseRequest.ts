/** Build an AnalyseRequest for a ticker from the sample template — no calculations. */

import type { AnalyseRequest } from "@/lib/api/compositionTypes";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";

export function buildAnalyseRequestForTicker(
  ticker: string,
  overrides?: Partial<Pick<AnalyseRequest, "exchange" | "company">>,
): AnalyseRequest {
  // RC3-003 — never invent a demo ticker when the caller omits one.
  const normalized = ticker.trim().toUpperCase();
  if (!normalized) {
    throw new Error(
      "Ticker is required — no default company is invented in the thin client.",
    );
  }
  return {
    ...SAMPLE_ANALYSE_REQUEST,
    ticker: normalized,
    exchange: overrides?.exchange ?? SAMPLE_ANALYSE_REQUEST.exchange,
    company:
      overrides?.company ??
      (normalized === SAMPLE_ANALYSE_REQUEST.ticker
        ? SAMPLE_ANALYSE_REQUEST.company
        : `${normalized} Research`),
  };
}
