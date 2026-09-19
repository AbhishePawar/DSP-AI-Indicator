/**
 * Layout fixture for the conversational result page.
 *
 * Rendered when a caller opts in via `exampleMode` (the `?example=true`
 * query param on /analysis), and also used as the result page's fallback
 * when a live analyse call fails or the backend is unreachable — a
 * temporary product decision until NEXT_PUBLIC_API_BASE_URL points at a
 * real backend. In both cases ResultConversation always shows the amber
 * "Example data" banner so this is never mistaken for live data. Only the
 * /analysis result page uses this fallback — the landing page is untouched.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";

// Figures below are sourced from screener.in/company/TCS/consolidated
// (market cap, P/E, ROE, ROCE, dividend yield, book value, growth rates,
// pros/cons) so the example layout reflects TCS's actual reported metrics
// rather than placeholder numbers.
export const EXAMPLE_RESEARCH_VIEW = {
  ok: true,
  ticker: "TCS",
  exchange: "NSE",
  company: "Tata Consultancy Services",
  analysedAt: new Date().toISOString(),
  analysisId: "example-preview",
  recommendation: "Hold",
  recommendationConfidence: 0.68,
  marginOfSafety: 0.06,
  businessQualityScore: 7.6,
  strengths: [
    "Strong return on equity track record — 51.8% ROE and 63.0% ROCE.",
    "Healthy dividend payout of ~77.5% and a 2.76% dividend yield.",
    "Trades at 15.6x P/E, below its own long-run average multiple.",
  ],
  weaknesses: [
    "Sales growth of ~10.2% over the past five years trails prior highs.",
    "Trading at 7.83x book value despite the slowing top-line growth.",
    "Net profit growth has moderated to ~8-9% over 3 and 5-year windows.",
  ],
  risks: [
    "Client concentration in a small number of large accounts.",
    "Currency and macro exposure across key export markets (BFSI at ~32% of revenue).",
    "Pricing pressure from AI-driven productivity gains at clients.",
  ],
  limitations: ["Example data shown for layout preview — not a live analysis."],
  warnings: [],
  evidenceCounts: { filings: 12, market_data: 4, analyst_estimates: 6 },
  financial: {
    stage: "financial",
    status: "ok",
    label: "Strong",
    decision: "High quality",
    score: "7.6/10",
    confidence: "High",
    error: null,
    warnings: [],
    metrics: [
      { label: "ROE", value: "51.8%" },
      { label: "ROCE", value: "63.0%" },
      { label: "Net Margin (TTM)", value: "18.1%" },
      { label: "Dividend Yield", value: "2.76%" },
    ],
  },
  businessQuality: {
    stage: "business_quality_aggregator",
    status: "ok",
    label: "Strong",
    decision: "High quality",
    score: "7.6/10",
    confidence: "High",
    error: null,
    warnings: [],
    metrics: [
      { label: "P/E (TTM)", value: "15.6x" },
      { label: "Book Value / Share", value: "₹296" },
    ],
  },
  valuation: {
    intrinsicValue: "₹2,460",
    currentPrice: "₹2,320",
    marginOfSafety: "6.0%",
    method: "DCF · relative multiples",
    confidence: "Moderate",
  },
  committee: {
    finalRecommendation: "Hold",
    supportingReasons: [
      "Strong return on equity track record — 51.8% ROE and 63.0% ROCE.",
      "Healthy dividend payout of ~77.5% and a 2.76% dividend yield.",
    ],
    opposingReasons: [
      "Sales growth of ~10.2% over the past five years trails prior highs.",
      "Trading at 7.83x book value despite the slowing top-line growth.",
    ],
  },
  buffett: {
    overallRating: "Good business, fair price",
    disclaimer:
      "Presentation synthesis of existing analysis outputs — no recalculation.",
    verdict:
      "TCS exhibits durable competitive advantages and high returns on capital, but slowing revenue growth and a premium book-value multiple leave limited margin of safety at the current price.",
    recommendation: {
      action: "Hold / accumulate on weakness",
      currentValuation: "Roughly fairly valued",
    },
    keyStrengths: [
      "Durable moat from switching costs and long-standing client relationships.",
      "Consistent, high-quality earnings and a shareholder-friendly dividend policy.",
    ],
    keyWeaknesses: [
      "Margin pressure from wage inflation and pricing.",
      "Growth has slowed to high single digits after years of faster expansion.",
    ],
  },
} as unknown as ResearchView;
