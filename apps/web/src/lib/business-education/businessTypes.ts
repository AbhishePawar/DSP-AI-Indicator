/** Business-type metric selection (presentation) — mirrors platform presets. */

export type BusinessType =
  | "bank"
  | "nbfc"
  | "insurance"
  | "asset_manager"
  | "exchange"
  | "it_saas"
  | "consumer"
  | "manufacturing"
  | "infrastructure"
  | "general";

const METRIC_PRESETS: Record<BusinessType, string[]> = {
  bank: [
    "aum",
    "nim",
    "roa",
    "roe",
    "credit_cost",
    "gnpa",
    "nnpa",
    "capital_adequacy",
  ],
  nbfc: [
    "aum",
    "nim",
    "roa",
    "roe",
    "credit_cost",
    "gnpa",
    "nnpa",
    "capital_adequacy",
  ],
  insurance: [
    "premium_growth",
    "combined_ratio",
    "solvency",
    "roe",
    "investment_yield",
  ],
  asset_manager: [
    "aum",
    "fee_income",
    "market_share",
    "operating_margin",
    "roe",
    "net_flows",
  ],
  exchange: [
    "transaction_volumes",
    "market_share",
    "recurring_revenue",
    "operating_leverage",
    "roe",
    "regulatory_moat",
  ],
  it_saas: [
    "revenue_growth",
    "ebit_margin",
    "fcf",
    "roce",
    "recurring_revenue",
    "arr",
    "retention",
    "client_concentration",
  ],
  consumer: [
    "volume_growth",
    "pricing",
    "gross_margin",
    "distribution",
    "brand_strength",
    "roce",
  ],
  manufacturing: [
    "capacity",
    "utilization",
    "margins",
    "working_capital",
    "roce",
    "capex",
  ],
  infrastructure: [
    "asset_base",
    "utilization",
    "regulatory_returns",
    "leverage",
    "cash_conversion",
    "roce",
  ],
  general: [
    "revenue_growth",
    "operating_margin",
    "net_margin",
    "roe",
    "roce",
    "operating_cash_flow",
    "free_cash_flow",
    "debt",
    "interest_coverage",
  ],
};

const KEYWORD_MAP: Array<{ keys: string[]; type: BusinessType }> = [
  { keys: ["bank", "banking", "lender"], type: "bank" },
  { keys: ["nbfc", "non-banking", "housing finance"], type: "nbfc" },
  { keys: ["insurance"], type: "insurance" },
  { keys: ["asset management", "mutual fund", "amc"], type: "asset_manager" },
  { keys: ["exchange", "clearing", "depository"], type: "exchange" },
  { keys: ["software", "saas", "it services", "information technology"], type: "it_saas" },
  { keys: ["fmcg", "consumer"], type: "consumer" },
  { keys: ["manufactur", "industrial"], type: "manufacturing" },
  { keys: ["infra", "power", "utility"], type: "infrastructure" },
];

export function detectBusinessType(blob: string): BusinessType {
  const text = blob.toLowerCase();
  if (!text.trim()) return "general";
  for (const row of KEYWORD_MAP) {
    if (row.keys.some((k) => text.includes(k))) return row.type;
  }
  return "general";
}

export function preferredMetrics(businessType: BusinessType): string[] {
  return METRIC_PRESETS[businessType] ?? METRIC_PRESETS.general;
}

export function economicsFocus(businessType: BusinessType): string[] {
  const focuses: Record<BusinessType, string[]> = {
    bank: [
      "Revenue engine: net interest income and fee income from loans and deposits.",
      "Key lenses: NIM, credit cost, GNPA/NNPA, capital adequacy, ROA/ROE.",
      "Capital intensity: balance-sheet leverage and regulatory capital are central.",
    ],
    nbfc: [
      "Revenue engine: interest and fee income on credit books (AUM).",
      "Key lenses: NIM, AUM growth, credit cost, GNPA/NNPA, capital adequacy.",
      "Funding and asset quality drive cash generation more than plant & equipment.",
    ],
    insurance: [
      "Revenue engine: premiums and investment income on float.",
      "Key lenses: premium growth, combined/solvency ratios, investment yield.",
      "Underwriting discipline and float management shape economics.",
    ],
    asset_manager: [
      "Revenue engine: fees on assets under management (AUM).",
      "Key lenses: AUM, net flows, fee rates, operating margin, ROE.",
      "Operating leverage can be high once scale is achieved.",
    ],
    exchange: [
      "Revenue engine: transaction fees and often listing/data services.",
      "Key lenses: volumes, market share, operating leverage, regulatory position.",
      "Fixed-cost platforms can show strong incremental margins with volume.",
    ],
    it_saas: [
      "Revenue engine: services contracts and/or subscription (ARR) revenue.",
      "Key lenses: revenue growth, EBIT margin, FCF, retention, client concentration.",
      "Capital intensity is often lower; talent and delivery quality matter.",
    ],
    consumer: [
      "Revenue engine: product sales through brand and distribution.",
      "Key lenses: volume, pricing, gross margin, brand, ROCE.",
      "Working capital and advertising/distribution spend shape cash conversion.",
    ],
    manufacturing: [
      "Revenue engine: production and sale of goods.",
      "Key lenses: capacity, utilization, raw materials, working capital, ROCE, capex.",
      "Operating leverage and inventory cycles are often material.",
    ],
    infrastructure: [
      "Revenue engine: regulated or contracted returns on long-lived assets.",
      "Key lenses: asset base, utilization, leverage, cash conversion, ROCE.",
      "Capex and financing structure dominate reinvestment needs.",
    ],
    general: [
      "Revenue engine: how customers pay for products or services.",
      "Key lenses: growth, margins, returns on capital, cash flow, leverage.",
      "Reinvestment needs depend on capital intensity and working capital.",
    ],
  };
  return focuses[businessType] ?? focuses.general;
}
