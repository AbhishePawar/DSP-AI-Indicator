/** Educational metric templates — copy only; values come from API or Unavailable. */

export type MetricTemplate = {
  id: string;
  title: string;
  meaning: string;
  whyItMatters: string;
  investorTakeawayWhenMissing: string;
  learnMore: string;
  aiPrompts: string[];
};

export const BUSINESS_QUALITY_METRICS: MetricTemplate[] = [
  {
    id: "business_quality",
    title: "Business Quality",
    meaning: "Overall quality of the underlying enterprise as cited by research artifacts.",
    whyItMatters: "Higher-quality businesses tend to compound more reliably over long horizons.",
    investorTakeawayWhenMissing: "Investigate segment mix and ROIC trends in filings when data arrives.",
    learnMore: "term:roic",
    aiPrompts: [
      "Explain business quality for this company in plain English",
      "What would improve business quality here?",
    ],
  },
  {
    id: "competitive_position",
    title: "Competitive Position",
    meaning: "How durable the company’s relative standing appears versus peers.",
    whyItMatters: "Weak competitive position can erase otherwise attractive valuation.",
    investorTakeawayWhenMissing: "Compare switching costs and market share narratives in the annual report.",
    learnMore: "term:moat",
    aiPrompts: [
      "Describe the competitive position",
      "What threatens this position?",
    ],
  },
  {
    id: "revenue_stability",
    title: "Revenue Stability",
    meaning: "How steady or cyclical top-line results have been.",
    whyItMatters: "Stable revenue supports predictability of cash flows and planning.",
    investorTakeawayWhenMissing: "Review multi-year revenue history when fundamentals are available.",
    learnMore: "term:cagr",
    aiPrompts: ["How stable is revenue?", "Is growth cyclical?"],
  },
  {
    id: "profitability",
    title: "Profitability",
    meaning: "Ability to convert sales into lasting economic profit.",
    whyItMatters: "Thin or volatile profits raise downside risk in stress periods.",
    investorTakeawayWhenMissing: "Inspect margin trends in the income statement when wired.",
    learnMore: "term:free_cash_flow",
    aiPrompts: ["Explain profitability drivers", "Are margins durable?"],
  },
  {
    id: "capital_allocation",
    title: "Capital Allocation",
    meaning: "How management deploys capital across reinvestment, M&A, and returns.",
    whyItMatters: "Poor allocation can destroy value even in good businesses.",
    investorTakeawayWhenMissing: "Read capital allocation commentary in the latest annual report.",
    learnMore: "term:roic",
    aiPrompts: ["How does management allocate capital?", "Any red flags?"],
  },
  {
    id: "business_predictability",
    title: "Business Predictability",
    meaning: "How foreseeable operating outcomes appear under normal conditions.",
    whyItMatters: "Low predictability widens intrinsic value ranges and raises research caution.",
    investorTakeawayWhenMissing: "List key uncertainties before sizing any research conclusion.",
    learnMore: "term:research_conclusion",
    aiPrompts: ["What makes this business hard to predict?", "What is more knowable?"],
  },
];

export const FINANCIAL_STRENGTH_METRICS: MetricTemplate[] = [
  {
    id: "revenue_growth",
    title: "Revenue Growth",
    meaning: "Pace of top-line expansion over the analysis window.",
    whyItMatters: "Growth frames how quickly the business can scale earnings power.",
    investorTakeawayWhenMissing: "Pull multi-year revenue CAGR from filings when available.",
    learnMore: "term:cagr",
    aiPrompts: ["Explain revenue growth", "Is growth volume or price?"],
  },
  {
    id: "operating_margin",
    title: "Operating Margin",
    meaning: "Operating profit as a share of revenue.",
    whyItMatters: "Shows operating leverage and cost discipline.",
    investorTakeawayWhenMissing: "Compare operating margin to peers when metrics arrive.",
    learnMore: "term:free_cash_flow",
    aiPrompts: ["Are operating margins healthy?", "What drives them?"],
  },
  {
    id: "net_margin",
    title: "Net Margin",
    meaning: "Bottom-line profitability after all expenses.",
    whyItMatters: "Captures the full P&L burden including interest and tax.",
    investorTakeawayWhenMissing: "Review net income quality when statements are connected.",
    learnMore: "term:free_cash_flow",
    aiPrompts: ["Explain net margin", "Any one-offs?"],
  },
  {
    id: "roe",
    title: "ROE",
    meaning: "Return on equity — earnings relative to shareholder equity.",
    whyItMatters: "Helps gauge capital efficiency for equity holders (context required).",
    investorTakeawayWhenMissing: "Interpret ROE with leverage context once fundamentals load.",
    learnMore: "term:roic",
    aiPrompts: ["Is ROE meaningful here?", "How levered is it?"],
  },
  {
    id: "roce",
    title: "ROCE",
    meaning: "Return on capital employed — broader capital efficiency signal.",
    whyItMatters: "Useful for comparing capital-heavy businesses.",
    investorTakeawayWhenMissing: "Await calculated ROCE from the valuation/fundamentals envelope.",
    learnMore: "term:roic",
    aiPrompts: ["Explain ROCE for this firm", "Trend vs peers?"],
  },
  {
    id: "debt",
    title: "Debt",
    meaning: "Leverage posture (e.g. debt levels relative to equity or cash flow).",
    whyItMatters: "Higher debt can amplify losses in downturns.",
    investorTakeawayWhenMissing: "Review debt maturity and covenants in the annual report.",
    learnMore: "term:debt_to_equity",
    aiPrompts: ["How risky is the debt?", "Can they service it?"],
  },
  {
    id: "interest_coverage",
    title: "Interest Coverage",
    meaning: "Earnings relative to interest expense.",
    whyItMatters: "Thin coverage raises refinancing and downturn risk.",
    investorTakeawayWhenMissing: "Check interest coverage once income statement metrics are present.",
    learnMore: "term:interest_coverage",
    aiPrompts: ["Explain interest coverage", "Stress-case coverage?"],
  },
  {
    id: "free_cash_flow",
    title: "Free Cash Flow",
    meaning: "Cash available after operating and investment needs (per methodology).",
    whyItMatters: "Supports resilience, reinvestment, and capital returns.",
    investorTakeawayWhenMissing: "Inspect cash flow statement when fundamentals are wired.",
    learnMore: "term:free_cash_flow",
    aiPrompts: ["How reliable is FCF?", "Any working-capital traps?"],
  },
];
