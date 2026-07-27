/** Sprint 2 educational catalogs — presentation templates only. */

export type GrowthMetricTemplate = {
  id: string;
  title: string;
  meaning: string;
  whyItMatters: string;
  investorTakeaway: string;
  aiExplanation: string;
  learnMore: string;
};

export type RiskTemplate = {
  id: string;
  title: string;
  reason: string;
  mitigation: string;
  watchpoints: string[];
};

export type ManagementMetricTemplate = {
  id: string;
  title: string;
  meaning: string;
  importance: string;
  aiInterpretation: string;
  learnMore: string;
};

export type MoatMetricTemplate = {
  id: string;
  title: string;
  meaning: string;
  investorTakeaway: string;
  learnMore: string;
};

export const GROWTH_METRICS: GrowthMetricTemplate[] = [
  {
    id: "historical_revenue_trend",
    title: "Historical Revenue Trend",
    meaning: "How top-line results have evolved over the analysis window.",
    whyItMatters: "Past revenue path frames whether growth is durable or episodic.",
    investorTakeaway: "Confirm multi-year revenue trajectory in filings when metrics load.",
    aiExplanation: "AI will interpret trend shape once calculated series are in the envelope.",
    learnMore: "term:cagr",
  },
  {
    id: "historical_profit_trend",
    title: "Historical Profit Trend",
    meaning: "How profitability has moved alongside revenue.",
    whyItMatters: "Growth without profit quality can destroy economic value.",
    investorTakeaway: "Watch whether profits compound with sales or lag.",
    aiExplanation: "Pending envelope profit series — interpretation deferred, not invented.",
    learnMore: "term:free_cash_flow",
  },
  {
    id: "growth_drivers",
    title: "Growth Drivers",
    meaning: "Primary engines that can expand the business (volume, price, mix, geography).",
    whyItMatters: "Knowing the driver tells you what must keep working for the thesis.",
    investorTakeaway: "List 1–2 driver hypotheses and seek evidence in segment disclosures.",
    aiExplanation: "Driver narratives require cited segments — unavailable until present.",
    learnMore: "term:cagr",
  },
  {
    id: "growth_sustainability",
    title: "Growth Sustainability",
    meaning: "Whether recent growth looks repeatable under normal conditions.",
    whyItMatters: "One-off spikes mislead decade-horizon research.",
    investorTakeaway: "Separate cyclical rebound from structural expansion.",
    aiExplanation: "Sustainability is an interpretation — labeled AI when generated later.",
    learnMore: "term:research_conclusion",
  },
  {
    id: "addressable_market",
    title: "Addressable Market",
    meaning: "How large the opportunity set appears for the company’s offerings.",
    whyItMatters: "A small or saturated market caps long-term growth.",
    investorTakeaway: "Seek independent TAM context; DSP will not invent market size.",
    aiExplanation: "External market sizing is consensus/research input when providers exist.",
    learnMore: "term:market_consensus",
  },
  {
    id: "expansion_opportunities",
    title: "Expansion Opportunities",
    meaning: "Adjacent products, geos, or channels that could extend growth.",
    whyItMatters: "Expansion optionality supports longer research horizons.",
    investorTakeaway: "Track announced expansions vs execution evidence.",
    aiExplanation: "Options remain Unavailable without cited pipeline evidence.",
    learnMore: "term:moat",
  },
  {
    id: "innovation",
    title: "Innovation",
    meaning: "Capacity to renew offerings and stay relevant.",
    whyItMatters: "Stagnant product sets erode growth and moat over a decade.",
    investorTakeaway: "Review R&D and launch cadence in reports when available.",
    aiExplanation: "Innovation quality is interpretive — never shown as verified fact alone.",
    learnMore: "term:moat",
  },
  {
    id: "operating_leverage",
    title: "Operating Leverage",
    meaning: "How profits may change faster than revenue as scale shifts.",
    whyItMatters: "High leverage boosts upside and deepens downturn pain.",
    investorTakeaway: "Pair leverage discussion with fixed-cost structure in filings.",
    aiExplanation: "Learn More: operating leverage is a structural concept, not a tip.",
    learnMore: "term:operating_leverage",
  },
  {
    id: "growth_constraints",
    title: "Growth Constraints",
    meaning: "Factors that can cap or slow expansion (capacity, regulation, capital).",
    whyItMatters: "Constraints define realistic decade paths.",
    investorTakeaway: "Write down the top constraint and monitor it each reporting cycle.",
    aiExplanation: "Constraints stay Unavailable until evidence cites them.",
    learnMore: "term:debt_to_equity",
  },
  {
    id: "future_monitoring_points",
    title: "Future Monitoring Points",
    meaning: "Specific signals to watch that would validate or break the growth story.",
    whyItMatters: "Turns growth research into an actionable checklist.",
    investorTakeaway: "Prefer 3 measurable watchpoints over vague optimism.",
    aiExplanation: "Monitoring lists are user research aids until API provides structured ones.",
    learnMore: "term:research_conclusion",
  },
];

export const RISK_CATEGORIES: RiskTemplate[] = [
  {
    id: "operational",
    title: "Operational Risk",
    reason: "Day-to-day execution, supply, quality, or process failures can impair results.",
    mitigation: "Look for diversified operations, controls, and recovery history in filings.",
    watchpoints: ["Service outages", "Supply disruptions", "Quality recalls"],
  },
  {
    id: "financial",
    title: "Financial Risk",
    reason: "Leverage, liquidity, and funding structure can amplify stress.",
    mitigation: "Review debt maturity, coverage, and cash buffers when fundamentals load.",
    watchpoints: ["Interest coverage", "Refinancing wall", "Cash burn"],
  },
  {
    id: "valuation",
    title: "Valuation Risk",
    reason: "Paying too much for uncertain cash flows raises permanent capital risk.",
    mitigation: "Rely on Estimated Intrinsic Value Range only when present; widen uncertainty otherwise.",
    watchpoints: ["Assumption sensitivity", "Multiple compression", "Missed growth"],
  },
  {
    id: "competitive",
    title: "Competitive Risk",
    reason: "Rivals can erode share, pricing, or relevance.",
    mitigation: "Track share, switching costs, and new entrants in industry disclosures.",
    watchpoints: ["Share loss", "Price wars", "Substitute products"],
  },
  {
    id: "regulatory",
    title: "Regulatory Risk",
    reason: "Rules, licenses, or policy shifts can change economics overnight.",
    mitigation: "Read risk-factor regulatory language; do not ignore jurisdiction exposure.",
    watchpoints: ["Pending rules", "Fines", "License renewals"],
  },
  {
    id: "execution",
    title: "Execution Risk",
    reason: "Strategy may be sound but delivery fails (integrations, launches, pivots).",
    mitigation: "Compare guidance vs outcomes across reporting periods when available.",
    watchpoints: ["Missed timelines", "Integration write-downs", "Strategy U-turns"],
  },
  {
    id: "technology",
    title: "Technology Risk",
    reason: "Platform, cyber, or tech obsolescence can impair the franchise.",
    mitigation: "Seek security incidents, tech debt signals, and roadmap credibility.",
    watchpoints: ["Breaches", "Legacy stack", "Disruption"],
  },
  {
    id: "industry",
    title: "Industry Risk",
    reason: "Sector structure (cyclicality, commoditization) shapes outcomes.",
    mitigation: "Place the firm in industry context before decade conclusions.",
    watchpoints: ["Cycle position", "Capacity glut", "Demand shock"],
  },
  {
    id: "macroeconomic",
    title: "Macroeconomic Risk",
    reason: "Rates, FX, inflation, and growth regimes affect demand and discount rates.",
    mitigation: "Note sensitivity qualitatively until economic context is in the envelope.",
    watchpoints: ["Rate shock", "FX swings", "Recession demand"],
  },
];

export const MANAGEMENT_METRICS: ManagementMetricTemplate[] = [
  {
    id: "capital_allocation",
    title: "Capital Allocation",
    meaning: "How leadership deploys capital across reinvestment, M&A, and returns.",
    importance: "Allocation quality often matters more than a single year’s earnings beat.",
    aiInterpretation: "Interpret only from cited uses of cash — never invent buyback motives.",
    learnMore: "term:capital_allocation",
  },
  {
    id: "execution_history",
    title: "Execution History",
    meaning: "Track record of delivering stated plans.",
    importance: "Credibility compounds; repeated misses erode trust in forecasts.",
    aiInterpretation: "Compare promises vs outcomes when historical guidance is available.",
    learnMore: "term:research_conclusion",
  },
  {
    id: "governance",
    title: "Governance",
    meaning: "Board oversight, controls, and accountability structures.",
    importance: "Weak governance raises fraud and misalignment risk.",
    aiInterpretation: "Governance scores stay Unavailable without disclosed structures.",
    learnMore: "term:research_conclusion",
  },
  {
    id: "shareholder_friendliness",
    title: "Shareholder Friendliness",
    meaning: "Whether policies respect minority owners’ economic interests.",
    importance: "Extractive policies can nullify operating excellence.",
    aiInterpretation: "Label opinions as AI Interpretation when generated later.",
    learnMore: "term:capital_allocation",
  },
  {
    id: "transparency",
    title: "Transparency",
    meaning: "Clarity and candor of reporting and communication.",
    importance: "Opaque reporting forces investors to guess — trust falls.",
    aiInterpretation: "Judge from disclosure quality when filings are cited.",
    learnMore: "term:research_conclusion",
  },
  {
    id: "promoter_alignment",
    title: "Promoter Alignment",
    meaning: "Incentives and ownership alignment with long-term value.",
    importance: "Misaligned incentives predict value leakage.",
    aiInterpretation: "Requires ownership/comp data — Unavailable until present.",
    learnMore: "term:capital_allocation",
  },
  {
    id: "decision_quality",
    title: "Decision Quality",
    meaning: "Quality of major strategic and capital decisions over time.",
    importance: "A few poor mega-decisions can define a decade.",
    aiInterpretation: "Case-based, cite-backed — not a tip label.",
    learnMore: "term:capital_allocation",
  },
  {
    id: "long_term_thinking",
    title: "Long-term Thinking",
    meaning: "Willingness to invest through cycles for durable advantage.",
    importance: "Short-termism undercuts moat and growth sustainability.",
    aiInterpretation: "Inferred from reinvestment patterns when evidence exists.",
    learnMore: "term:moat",
  },
];

export const MOAT_METRICS: MoatMetricTemplate[] = [
  {
    id: "brand_strength",
    title: "Brand Strength",
    meaning: "Customer preference and pricing supported by brand.",
    investorTakeaway: "Ask whether brand allows pricing power without volume loss.",
    learnMore: "term:pricing_power",
  },
  {
    id: "network_effects",
    title: "Network Effects",
    meaning: "Value rises as more users participate.",
    investorTakeaway: "Confirm true network loops vs marketing slogans.",
    learnMore: "term:network_effect",
  },
  {
    id: "switching_costs",
    title: "Switching Costs",
    meaning: "Friction customers face when leaving.",
    investorTakeaway: "High switching costs support retention — verify with churn evidence.",
    learnMore: "term:switching_cost",
  },
  {
    id: "cost_advantage",
    title: "Cost Advantage",
    meaning: "Structurally lower cost position vs peers.",
    investorTakeaway: "Look for scale, process, or input advantages in disclosures.",
    learnMore: "term:moat",
  },
  {
    id: "scale",
    title: "Scale",
    meaning: "Size advantages in purchasing, distribution, or R&D.",
    investorTakeaway: "Scale helps only if it translates to returns.",
    learnMore: "term:moat",
  },
  {
    id: "distribution",
    title: "Distribution",
    meaning: "Reach and channel control that rivals struggle to match.",
    investorTakeaway: "Map channel dependence and concentration risk.",
    learnMore: "term:moat",
  },
  {
    id: "technology",
    title: "Technology",
    meaning: "Tech or IP that sustains differentiation.",
    investorTakeaway: "Separate durable tech from easily copied features.",
    learnMore: "term:moat",
  },
  {
    id: "customer_loyalty",
    title: "Customer Loyalty",
    meaning: "Repeat behavior and retention beyond price.",
    investorTakeaway: "Seek retention/NPS-like evidence when available.",
    learnMore: "term:switching_cost",
  },
  {
    id: "pricing_power",
    title: "Pricing Power",
    meaning: "Ability to raise prices without losing demand disproportionately.",
    investorTakeaway: "Test with historical price actions and volume response.",
    learnMore: "term:pricing_power",
  },
  {
    id: "industry_position",
    title: "Industry Position",
    meaning: "Relative standing in the competitive structure.",
    investorTakeaway: "Leader vs niche — different decade paths.",
    learnMore: "term:moat",
  },
  {
    id: "moat_sustainability",
    title: "Moat Sustainability",
    meaning: "How durable advantages look over a long horizon.",
    investorTakeaway: "Ask what could erode the moat in 5–10 years.",
    learnMore: "term:moat",
  },
];

/** Tooltip concepts required by Sprint 2 */
export const CONCEPT_TOOLTIPS: Record<
  string,
  { title: string; definition: string; aiExplanation: string }
> = {
  roce: {
    title: "ROCE",
    definition: "Return on capital employed — profit relative to capital tied up in the business.",
    aiExplanation: "Higher ROCE can signal efficient use of capital; always compare within industry.",
  },
  operating_leverage: {
    title: "Operating Leverage",
    definition: "Sensitivity of operating profit to changes in revenue given fixed vs variable costs.",
    aiExplanation: "High operating leverage magnifies both upcycles and downcycles.",
  },
  switching_cost: {
    title: "Switching Cost",
    definition: "Effort, risk, or expense a customer faces when changing providers.",
    aiExplanation: "High switching costs can support retention and pricing power.",
  },
  capital_allocation: {
    title: "Capital Allocation",
    definition: "Management choices about where to invest, acquire, return, or hold cash.",
    aiExplanation: "Good allocation compounds; poor allocation destroys value even in strong businesses.",
  },
  network_effect: {
    title: "Network Effect",
    definition: "Product value increases as more participants join the network.",
    aiExplanation: "True network effects are rare; verify reinforcing loops with evidence.",
  },
  pricing_power: {
    title: "Pricing Power",
    definition: "Ability to raise prices without losing customers disproportionately.",
    aiExplanation: "Pricing power often coexists with brand, switching costs, or unique supply.",
  },
};
