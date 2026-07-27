/** Build an AnalyseRequest for a ticker from the sample template — no calculations. */

import type { AnalyseRequest } from "@/lib/api/compositionTypes";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";

export function buildAnalyseRequestForTicker(
  ticker: string,
  overrides?: Partial<Pick<AnalyseRequest, "exchange" | "company">>,
): AnalyseRequest {
  const normalized = ticker.trim().toUpperCase() || "ACM";
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
