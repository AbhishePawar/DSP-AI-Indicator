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

export const EXAMPLE_RESEARCH_VIEW = {
  ok: true,
  ticker: "TCS",
  exchange: "NSE",
  company: "Tata Consultancy Services",
  analysedAt: new Date().toISOString(),
  analysisId: "example-preview",
  recommendation: "Buy",
  recommendationConfidence: 0.82,
  marginOfSafety: 0.128,
  businessQualityScore: 8.4,
  strengths: [
    "Best-in-class ROE (~49%) and ROCE (~66%) among global IT peers.",
    "Dividend yield of 4.66% — among the highest in large-cap IT.",
    "Trading at a discount to its own five-year valuation history.",
  ],
  weaknesses: [
    "Net margin compressed ~1.9 percentage points from FY20 to FY26.",
    "Revenue growth has slowed relative to the broader IT sector.",
  ],
  risks: [
    "Client concentration in a small number of large accounts.",
    "Currency and macro exposure across key export markets.",
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
    score: "8.4/10",
    confidence: "High",
    error: null,
    warnings: [],
    metrics: [
      { label: "ROE", value: "49%" },
      { label: "ROCE", value: "66%" },
      { label: "Net Margin (FY26)", value: "18.1%" },
      { label: "Dividend Yield", value: "4.66%" },
    ],
  },
  businessQuality: {
    stage: "business_quality_aggregator",
    status: "ok",
    label: "Strong",
    decision: "High quality",
    score: "8.4/10",
    confidence: "High",
    error: null,
    warnings: [],
    metrics: [
      { label: "P/E (TTM)", value: "22.4x" },
      { label: "EV/EBITDA (TTM)", value: "18.2x" },
    ],
  },
  valuation: {
    intrinsicValue: "₹3,580",
    currentPrice: "₹3,120",
    marginOfSafety: "12.8%",
    method: "DCF · relative multiples",
    confidence: "High",
  },
  committee: {
    finalRecommendation: "Buy",
    supportingReasons: [
      "Best-in-class ROE (~49%) and ROCE (~66%) among global IT peers.",
      "Dividend yield of 4.66% — among the highest in large-cap IT.",
    ],
    opposingReasons: [
      "Net margin compressed ~1.9 percentage points from FY20 to FY26.",
      "Client concentration in a small number of large accounts.",
    ],
  },
  buffett: {
    overallRating: "Wonderful business",
    disclaimer:
      "Presentation synthesis of existing analysis outputs — no recalculation.",
    verdict:
      "TCS exhibits durable competitive advantages, high returns on capital, and a shareholder-friendly capital allocation record, trading close to fair value.",
    recommendation: {
      action: "Buy on weakness",
      currentValuation: "Slightly undervalued",
    },
    keyStrengths: [
      "Durable moat from switching costs and client relationships.",
      "Consistent, high-quality earnings across cycles.",
    ],
    keyWeaknesses: ["Margin pressure from wage inflation and pricing."],
  },
} as unknown as ResearchView;
