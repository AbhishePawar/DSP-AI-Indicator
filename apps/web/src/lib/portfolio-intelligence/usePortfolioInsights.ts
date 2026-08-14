"use client";

/**
 * Portfolio Intelligence Engine (RC1 Milestone 4) — data-fetching hook.
 * Wraps the stateless POST /api/v1/portfolio/insights endpoint behind
 * react-query. No client-side computation — every score, classification,
 * and ranking is computed server-side by orchestrating Portfolio Analytics
 * and linked-research valuation/quality/committee signals.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, type PortfolioInsightsPayload } from "@/lib/api/client";
import type { SavedAnalysis } from "@/lib/persistence/types";
import type { PortfolioHolding } from "@/lib/portfolio/model";
import { buildPortfolioAnalyticsPortfolio } from "./mapPortfolioAnalytics";
import { buildResearchObjectsFromSavedAnalyses } from "./researchObjectsAdapter";

export function usePortfolioInsights(
  holdings: PortfolioHolding[],
  token: string | null | undefined,
  options?: {
    savedAnalyses?: SavedAnalysis[];
    benchmarkSymbol?: string | null;
    cashWeight?: number | null;
    enabled?: boolean;
  },
): UseQueryResult<PortfolioInsightsPayload> {
  const tickers = holdings.map((h) => h.ticker).join(",");
  const enabled =
    Boolean(token) && holdings.length > 0 && (options?.enabled ?? true);
  const portfolio = buildPortfolioAnalyticsPortfolio(holdings);
  const benchmarkSymbol = options?.benchmarkSymbol ?? null;
  const cashWeight = options?.cashWeight ?? null;
  const savedAnalyses = options?.savedAnalyses ?? [];
  const researchObjects = buildResearchObjectsFromSavedAnalyses(savedAnalyses);
  const researchKey = savedAnalyses.map((a) => `${a.ticker}:${a.savedAt}`).join(",");

  return useQuery({
    queryKey: [
      "portfolio-insights",
      tickers,
      benchmarkSymbol,
      cashWeight,
      researchKey,
      token ?? "anon",
    ],
    queryFn: () =>
      api.portfolioInsights(
        {
          portfolio,
          research_objects: researchObjects,
          benchmark_symbol: benchmarkSymbol,
          cash_weight: cashWeight,
        },
        { token },
      ),
    enabled,
    retry: false,
    staleTime: 60_000,
  });
}
