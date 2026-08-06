"use client";

/**
 * Portfolio Intelligence Analytics module — data-fetching hook.
 * Wraps the 6 stateless POST /api/v1/portfolio/analytics/* endpoints behind
 * react-query, mirroring the existing `/portfolio/intelligence` query
 * pattern in `PortfolioIntelligenceWorkspace`. No client-side computation —
 * every ratio/allocation/simulation value is server-computed.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import {
  api,
  type PortfolioAnalyticsAllocationPayload,
  type PortfolioAnalyticsConstraintsPayload,
  type PortfolioAnalyticsPerformancePayload,
  type PortfolioAnalyticsRiskPayload,
  type PortfolioAnalyticsSimulationPayload,
  type PortfolioAnalyticsStressPayload,
  type PortfolioAnalyticsTaxPayload,
} from "@/lib/api/client";
import type { PortfolioHolding } from "@/lib/portfolio/model";
import { buildPortfolioAnalyticsPortfolio } from "./mapPortfolioAnalytics";

export type PortfolioAnalyticsQueries = {
  performanceQuery: UseQueryResult<PortfolioAnalyticsPerformancePayload>;
  riskQuery: UseQueryResult<PortfolioAnalyticsRiskPayload>;
  allocationQuery: UseQueryResult<PortfolioAnalyticsAllocationPayload>;
  simulationQuery: UseQueryResult<PortfolioAnalyticsSimulationPayload>;
  stressQuery: UseQueryResult<PortfolioAnalyticsStressPayload>;
  constraintsQuery: UseQueryResult<PortfolioAnalyticsConstraintsPayload>;
  taxQuery: UseQueryResult<PortfolioAnalyticsTaxPayload>;
};

export function usePortfolioAnalyticsQueries(
  holdings: PortfolioHolding[],
  token: string | null | undefined,
  options?: {
    benchmarkSymbol?: string | null;
    targetWeights?: Record<string, number> | null;
    maxPositionWeight?: number | null;
    /** Gate the heavier simulation/stress/tax fetches to the tabs that need them. */
    includeSimulation?: boolean;
    includeStress?: boolean;
    includeTax?: boolean;
  },
): PortfolioAnalyticsQueries {
  const tickers = holdings.map((h) => h.ticker).join(",");
  const enabled = Boolean(token) && holdings.length > 0;
  const portfolio = buildPortfolioAnalyticsPortfolio(holdings);
  const benchmarkSymbol = options?.benchmarkSymbol ?? null;
  const includeSimulation = options?.includeSimulation ?? true;
  const includeStress = options?.includeStress ?? true;
  const includeTax = options?.includeTax ?? true;

  const performanceQuery = useQuery({
    queryKey: ["portfolio-analytics-performance", tickers, benchmarkSymbol, token ?? "anon"],
    queryFn: () =>
      api.portfolioAnalyticsPerformance(
        { portfolio, benchmark_symbol: benchmarkSymbol },
        { token },
      ),
    enabled,
    retry: false,
    staleTime: 60_000,
  });

  const riskQuery = useQuery({
    queryKey: ["portfolio-analytics-risk", tickers, token ?? "anon"],
    queryFn: () => api.portfolioAnalyticsRisk({ portfolio }, { token }),
    enabled,
    retry: false,
    staleTime: 60_000,
  });

  const allocationQuery = useQuery({
    queryKey: ["portfolio-analytics-allocation", tickers, token ?? "anon"],
    queryFn: () => api.portfolioAnalyticsAllocation({ portfolio }, { token }),
    enabled,
    retry: false,
    staleTime: 60_000,
  });

  const simulationQuery = useQuery({
    queryKey: ["portfolio-analytics-simulation", tickers, token ?? "anon"],
    queryFn: () =>
      api.portfolioAnalyticsSimulation(
        { portfolio, monte_carlo_paths: 1000, frontier_samples: 200, seed: 42 },
        { token },
      ),
    enabled: enabled && includeSimulation,
    retry: false,
    staleTime: 60_000,
  });

  const stressQuery = useQuery({
    queryKey: ["portfolio-analytics-stress", tickers, benchmarkSymbol, token ?? "anon"],
    queryFn: () =>
      api.portfolioAnalyticsStress(
        {
          portfolio,
          benchmark_symbol: benchmarkSymbol,
          stress_window_ids: ["gfc_2008", "covid_2020"],
          scenarios: [
            { name: "Market -10%", shock_pct: -0.1 },
            { name: "Market -20%", shock_pct: -0.2 },
          ],
        },
        { token },
      ),
    enabled: enabled && includeStress,
    retry: false,
    staleTime: 60_000,
  });

  const targetWeights = options?.targetWeights ?? null;
  const maxPositionWeight = options?.maxPositionWeight ?? null;
  const constraintsQuery = useQuery({
    queryKey: [
      "portfolio-analytics-constraints",
      tickers,
      JSON.stringify(targetWeights),
      maxPositionWeight,
      token ?? "anon",
    ],
    queryFn: () =>
      api.portfolioAnalyticsConstraints(
        {
          portfolio,
          target_weights: targetWeights,
          max_position_weight: maxPositionWeight,
        },
        { token },
      ),
    enabled,
    retry: false,
    staleTime: 60_000,
  });

  const taxQuery = useQuery({
    queryKey: ["portfolio-analytics-tax", tickers, token ?? "anon"],
    queryFn: () => api.portfolioAnalyticsTax({ portfolio }, { token }),
    enabled: enabled && includeTax,
    retry: false,
    staleTime: 60_000,
  });

  return {
    performanceQuery,
    riskQuery,
    allocationQuery,
    simulationQuery,
    stressQuery,
    constraintsQuery,
    taxQuery,
  };
}
