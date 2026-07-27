/** Sprint 8 — Portfolio Intelligence view-model (presentation aggregations only). */

import type { ConfidenceLevel } from "@/lib/trust/labels";
import { CONFIDENCE_LABELS } from "@/lib/trust/labels";

export type TrustedMetric = {
  id: string;
  label: string;
  value: string | null;
  numeric: number | null;
  presence: "available" | "unavailable";
  confidence: ConfidenceLevel;
  evidence: string;
  timestamp: string | null;
  methodology: string;
};

export type RebalanceAction = "reduce" | "increase" | "hold" | "add_cash" | "deploy_cash";

export type PortfolioHolding = {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  country: string;
  currency: string;
  shares: number;
  purchasePrice: number | null;
  currentPrice: number | null;
  marketValue: number | null;
  weight: number | null;
  targetAllocation: number | null;
  intrinsicValue: number | null;
  marginOfSafety: number | null;
  expectedCagr: number | null;
  confidence: ConfidenceLevel;
  businessQuality: string | null;
  financialStrength: string | null;
  managementScore: string | null;
  capitalAllocation: string | null;
  moatRating: string | null;
  riskRating: string | null;
  theme: "growth" | "value" | "blend" | "unavailable";
  style: "dividend" | "growth" | "blend" | "unavailable";
  cyclicality: "cyclical" | "defensive" | "blend" | "unavailable";
  marketCapBucket: "large" | "mid" | "small" | "unavailable";
  notes: string;
  lastUpdated: string | null;
  evidence: string;
  methodology: string;
};

export type WatchlistItem = {
  id: string;
  symbol: string;
  name: string;
  targetBuyPrice: number | null;
  currentPrice: number | null;
  currentDiscount: number | null;
  marginOfSafety: number | null;
  intrinsicValue: number | null;
  expectedCagr: number | null;
  reasonToWatch: string;
  alertPlaceholder: string;
  confidence: ConfidenceLevel;
  evidence: string;
  lastUpdated: string | null;
  methodology: string;
};

export type AllocationSlice = {
  id: string;
  label: string;
  weight: number;
  value: number | null;
};

export type RebalanceSuggestion = {
  id: string;
  symbol: string;
  action: RebalanceAction;
  rationale: string;
  confidence: ConfidenceLevel;
  evidence: string;
};

export type ScenarioId =
  | "bull"
  | "base"
  | "bear"
  | "market_crash"
  | "rate_rise"
  | "recession"
  | "commodity_spike"
  | "ai_boom"
  | "renewable_boom";

export type ScenarioRow = {
  id: ScenarioId;
  label: string;
  portfolioImpact: string;
  expectedReturnDelta: string | null;
  confidence: ConfidenceLevel;
  evidence: string;
  methodology: string;
};

export type PortfolioWorkspaceView = {
  version: string;
  asOf: string | null;
  currency: string;
  cash: TrustedMetric;
  holdings: PortfolioHolding[];
  watchlist: WatchlistItem[];
  overview: {
    portfolioValue: TrustedMetric;
    cashPercent: TrustedMetric;
    investedPercent: TrustedMetric;
    holdingCount: TrustedMetric;
    averageMos: TrustedMetric;
    averageIntrinsicDiscount: TrustedMetric;
    averageQuality: TrustedMetric;
    weightedRoce: TrustedMetric;
    weightedRoe: TrustedMetric;
    expectedCagr: TrustedMetric;
    expectedUpside: TrustedMetric;
    downsideRisk: TrustedMetric;
    concentrationScore: TrustedMetric;
    diversificationScore: TrustedMetric;
    portfolioRiskScore: TrustedMetric;
  };
  risk: {
    largestPosition: TrustedMetric;
    largestSector: TrustedMetric;
    largestDrawdownRisk: TrustedMetric;
    overvaluedHoldings: string[];
    undervaluedHoldings: string[];
    highDebtHoldings: string[];
    lowConfidenceHoldings: string[];
    topRisks: string[];
    topOpportunities: string[];
  };
  allocations: {
    sector: AllocationSlice[];
    industry: AllocationSlice[];
    marketCap: AllocationSlice[];
    country: AllocationSlice[];
    theme: AllocationSlice[];
    growthVsValue: AllocationSlice[];
    dividendVsGrowth: AllocationSlice[];
    cyclicalVsDefensive: AllocationSlice[];
  };
  expectedReturn: {
    expectedCagr: TrustedMetric;
    expectedDividendYield: TrustedMetric;
    expectedTotalReturn: TrustedMetric;
    portfolioFairValue: TrustedMetric;
    portfolioIntrinsicValue: TrustedMetric;
  };
  qualityDistribution: AllocationSlice[];
  moatDistribution: AllocationSlice[];
  mosDistribution: AllocationSlice[];
  rebalance: RebalanceSuggestion[];
  scenarios: ScenarioRow[];
  notes: string[];
  empty: boolean;
  disclosures: string[];
};

function metric(
  id: string,
  label: string,
  numeric: number | null,
  format: (n: number) => string,
  confidence: ConfidenceLevel,
  evidence: string,
  methodology: string,
  timestamp: string | null,
): TrustedMetric {
  if (numeric == null || Number.isNaN(numeric)) {
    return {
      id,
      label,
      value: null,
      numeric: null,
      presence: "unavailable",
      confidence: "insufficient_evidence",
      evidence,
      timestamp,
      methodology,
    };
  }
  return {
    id,
    label,
    value: format(numeric),
    numeric,
    presence: "available",
    confidence,
    evidence,
    timestamp,
    methodology,
  };
}

const pct = (n: number) => `${n.toFixed(1)}%`;
const money = (n: number, ccy = "INR") =>
  `${ccy} ${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const num = (n: number) => n.toFixed(1);

function weightedAvg(
  items: { weight: number | null; value: number | null }[],
): number | null {
  let wSum = 0;
  let vSum = 0;
  for (const it of items) {
    if (it.weight == null || it.value == null) continue;
    wSum += it.weight;
    vSum += it.weight * it.value;
  }
  if (wSum <= 0) return null;
  return vSum / wSum;
}

function groupWeights(
  holdings: PortfolioHolding[],
  keyFn: (h: PortfolioHolding) => string,
  total: number,
): AllocationSlice[] {
  const map = new Map<string, number>();
  for (const h of holdings) {
    const key = keyFn(h) || "Unavailable";
    const mv = h.marketValue ?? 0;
    map.set(key, (map.get(key) ?? 0) + mv);
  }
  return Array.from(map.entries())
    .map(([label, value], i) => ({
      id: `${label}-${i}`,
      label,
      value: total > 0 ? value : null,
      weight: total > 0 ? (value / total) * 100 : 0,
    }))
    .sort((a, b) => b.weight - a.weight);
}

/** Educational session sample — not broker-synced. Numbers are illustrative presentation fields. */
export function buildDemoPortfolio(): PortfolioWorkspaceView {
  const asOf = new Date().toISOString().slice(0, 10);
  const cashAmount = 250_000;
  const holdings: PortfolioHolding[] = [
    {
      id: "h-infy",
      symbol: "INFY",
      name: "Infosys Ltd",
      sector: "Information Technology",
      industry: "IT Services",
      country: "India",
      currency: "INR",
      shares: 120,
      purchasePrice: 1450,
      currentPrice: 1580,
      marketValue: 120 * 1580,
      weight: null,
      targetAllocation: 18,
      intrinsicValue: 1720,
      marginOfSafety: ((1720 - 1580) / 1720) * 100,
      expectedCagr: 11,
      confidence: "moderate",
      businessQuality: "Strong",
      financialStrength: "Strong",
      managementScore: "Good",
      capitalAllocation: "Disciplined",
      moatRating: "Wide",
      riskRating: "Moderate",
      theme: "growth",
      style: "growth",
      cyclicality: "defensive",
      marketCapBucket: "large",
      notes: "Mapped from prior DSP Research session (presentation seed).",
      lastUpdated: asOf,
      evidence: "Session seed holding — not live broker data",
      methodology: "Presentation aggregation · Sprint 8 portfolioWorkspace",
    },
    {
      id: "h-hdfcbank",
      symbol: "HDFCBANK",
      name: "HDFC Bank",
      sector: "Financials",
      industry: "Private Banks",
      country: "India",
      currency: "INR",
      shares: 80,
      purchasePrice: 1520,
      currentPrice: 1480,
      marketValue: 80 * 1480,
      weight: null,
      targetAllocation: 16,
      intrinsicValue: 1650,
      marginOfSafety: ((1650 - 1480) / 1650) * 100,
      expectedCagr: 10,
      confidence: "moderate",
      businessQuality: "Strong",
      financialStrength: "Strong",
      managementScore: "Good",
      capitalAllocation: "Conservative",
      moatRating: "Wide",
      riskRating: "Low",
      theme: "value",
      style: "dividend",
      cyclicality: "cyclical",
      marketCapBucket: "large",
      notes: "Quality compounder seed.",
      lastUpdated: asOf,
      evidence: "Session seed holding",
      methodology: "Presentation aggregation · Sprint 8",
    },
    {
      id: "h-tcs",
      symbol: "TCS",
      name: "Tata Consultancy Services",
      sector: "Information Technology",
      industry: "IT Services",
      country: "India",
      currency: "INR",
      shares: 40,
      purchasePrice: 3600,
      currentPrice: 3850,
      marketValue: 40 * 3850,
      weight: null,
      targetAllocation: 14,
      intrinsicValue: 4000,
      marginOfSafety: ((4000 - 3850) / 4000) * 100,
      expectedCagr: 9,
      confidence: "moderate",
      businessQuality: "Strong",
      financialStrength: "Strong",
      managementScore: "Good",
      capitalAllocation: "Shareholder-friendly",
      moatRating: "Wide",
      riskRating: "Low",
      theme: "blend",
      style: "dividend",
      cyclicality: "defensive",
      marketCapBucket: "large",
      notes: "",
      lastUpdated: asOf,
      evidence: "Session seed holding",
      methodology: "Presentation aggregation · Sprint 8",
    },
    {
      id: "h-sparse",
      symbol: "DEMO",
      name: "Sparse Envelope Co",
      sector: "Unavailable",
      industry: "Unavailable",
      country: "India",
      currency: "INR",
      shares: 50,
      purchasePrice: 100,
      currentPrice: 95,
      marketValue: 50 * 95,
      weight: null,
      targetAllocation: 5,
      intrinsicValue: null,
      marginOfSafety: null,
      expectedCagr: null,
      confidence: "insufficient_evidence",
      businessQuality: null,
      financialStrength: null,
      managementScore: null,
      capitalAllocation: null,
      moatRating: null,
      riskRating: "High",
      theme: "unavailable",
      style: "unavailable",
      cyclicality: "unavailable",
      marketCapBucket: "small",
      notes: "Illustrates Unavailable research fields — Copilot/Analysis not overridden.",
      lastUpdated: asOf,
      evidence: "No DSP intrinsic value in seed — left Unavailable",
      methodology: "Honest Unavailable preferred over invention",
    },
  ];

  return finalizePortfolio({
    cashAmount,
    holdings,
    watchlist: [
      {
        id: "w-reliance",
        symbol: "RELIANCE",
        name: "Reliance Industries",
        targetBuyPrice: 2400,
        currentPrice: 2650,
        currentDiscount: ((2400 - 2650) / 2650) * 100,
        marginOfSafety: null,
        intrinsicValue: null,
        expectedCagr: null,
        reasonToWatch: "Wait for wider MOS vs DSP Research when available",
        alertPlaceholder: "Price alerts deferred — no broker/alert engine in Sprint 8",
        confidence: "insufficient_evidence",
        evidence: "Watchlist is session presentation only",
        lastUpdated: asOf,
        methodology: "Manual watch reason · no automated alerts",
      },
      {
        id: "w-asianpaint",
        symbol: "ASIANPAINT",
        name: "Asian Paints",
        targetBuyPrice: 2800,
        currentPrice: 2950,
        currentDiscount: ((2800 - 2950) / 2950) * 100,
        marginOfSafety: 8,
        intrinsicValue: 3200,
        expectedCagr: 8,
        reasonToWatch: "Quality franchise — patience for entry zone",
        alertPlaceholder: "Alert placeholder",
        confidence: "low",
        evidence: "Illustrative watchlist seed",
        lastUpdated: asOf,
        methodology: "Presentation seed",
      },
    ],
    notes: [
      "Portfolio Intelligence is a presentation layer over session holdings — not broker-synced.",
      "Aggregations use only fields present on holdings; missing research stays Unavailable.",
      "Rebalance suggestions are educational — never automatic trades.",
    ],
    asOf,
  });
}

export function emptyPortfolioWorkspace(): PortfolioWorkspaceView {
  return finalizePortfolio({
    cashAmount: 0,
    holdings: [],
    watchlist: [],
    notes: ["Add holdings when portfolio APIs or session import arrive (out of scope)."],
    asOf: null,
  });
}

function finalizePortfolio(args: {
  cashAmount: number;
  holdings: PortfolioHolding[];
  watchlist: WatchlistItem[];
  notes: string[];
  asOf: string | null;
}): PortfolioWorkspaceView {
  const { cashAmount, holdings: raw, watchlist, notes, asOf } = args;
  const invested = raw.reduce((s, h) => s + (h.marketValue ?? 0), 0);
  const total = invested + cashAmount;
  const holdings = raw.map((h) => ({
    ...h,
    weight: total > 0 && h.marketValue != null ? (h.marketValue / total) * 100 : null,
  }));

  const meth = "Portfolio roll-up from session holdings (presentation only · Sprint 8)";
  const ev = "Derived from session portfolio model — not Decision Engine output";

  const avgMos = weightedAvg(
    holdings.map((h) => ({ weight: h.weight, value: h.marginOfSafety })),
  );
  const avgDisc = weightedAvg(
    holdings.map((h) => {
      if (h.intrinsicValue == null || h.currentPrice == null) return { weight: h.weight, value: null };
      return {
        weight: h.weight,
        value: ((h.intrinsicValue - h.currentPrice) / h.intrinsicValue) * 100,
      };
    }),
  );
  const expCagr = weightedAvg(
    holdings.map((h) => ({ weight: h.weight, value: h.expectedCagr })),
  );

  const qualityScore = (q: string | null) =>
    q === "Strong" ? 3 : q === "Good" ? 2 : q === "Fair" ? 1 : null;
  const avgQuality = weightedAvg(
    holdings.map((h) => ({
      weight: h.weight,
      value: qualityScore(h.businessQuality),
    })),
  );

  // ROCE/ROE intentionally Unavailable — not inventing from incomplete seeds
  const weightedRoce = null;
  const weightedRoe = null;

  const sortedByWeight = [...holdings].sort(
    (a, b) => (b.weight ?? 0) - (a.weight ?? 0),
  );
  const largest = sortedByWeight[0];
  const sectorWeights = groupWeights(holdings, (h) => h.sector, total);
  const largestSector = sectorWeights[0];

  const overvalued = holdings
    .filter((h) => h.marginOfSafety != null && h.marginOfSafety < 0)
    .map((h) => h.symbol);
  const undervalued = holdings
    .filter((h) => h.marginOfSafety != null && h.marginOfSafety >= 15)
    .map((h) => h.symbol);
  const lowConf = holdings
    .filter(
      (h) =>
        h.confidence === "low" || h.confidence === "insufficient_evidence",
    )
    .map((h) => h.symbol);
  const highDebt = holdings
    .filter((h) => h.financialStrength === "Weak" || h.riskRating === "High")
    .map((h) => h.symbol);

  const maxWeight = largest?.weight ?? 0;
  const concentrationScore = maxWeight;
  const diversificationScore =
    holdings.length <= 1 ? 10 : Math.max(0, 100 - maxWeight * 1.5);

  const intrinsicSum = holdings.reduce((s, h) => {
    if (h.intrinsicValue == null || h.shares == null) return s;
    return s + h.intrinsicValue * h.shares;
  }, 0);
  const hasAnyIv = holdings.some((h) => h.intrinsicValue != null);

  const rebalance: RebalanceSuggestion[] = holdings.map((h) => {
    const w = h.weight ?? 0;
    const t = h.targetAllocation ?? w;
    let action: RebalanceAction = "hold";
    let rationale = `${h.symbol} near target allocation.`;
    if (w > t + 3) {
      action = "reduce";
      rationale = `${h.symbol} weight ${w.toFixed(1)}% above target ${t}% — consider reduce (suggestion only).`;
    } else if (w < t - 3) {
      action = "increase";
      rationale = `${h.symbol} weight ${w.toFixed(1)}% below target ${t}% — consider increase when research supports.`;
    }
    return {
      id: `rb-${h.id}`,
      symbol: h.symbol,
      action,
      rationale,
      confidence: h.confidence,
      evidence: "Target vs current weight comparison (presentation)",
    };
  });
  if (cashAmount / Math.max(total, 1) > 0.2) {
    rebalance.push({
      id: "rb-deploy",
      symbol: "CASH",
      action: "deploy_cash",
      rationale: "Cash weight elevated — deploy only into researched ideas (no auto-trade).",
      confidence: "moderate",
      evidence: `Cash ${pct((cashAmount / Math.max(total, 1)) * 100)}`,
    });
  } else if (cashAmount / Math.max(total, 1) < 0.05 && total > 0) {
    rebalance.push({
      id: "rb-add-cash",
      symbol: "CASH",
      action: "add_cash",
      rationale: "Cash buffer thin — consider add cash for flexibility (suggestion only).",
      confidence: "low",
      evidence: "Cash buffer heuristic",
    });
  }

  const scenarios: ScenarioRow[] = [
    {
      id: "bull",
      label: "Bull",
      portfolioImpact: "Quality compounders may extend; MOS compresses.",
      expectedReturnDelta: expCagr != null ? `~+${(expCagr * 0.3).toFixed(1)} pp (illustrative)` : null,
      confidence: "low",
      evidence: "Scenario narrative — not a forecast",
      methodology: "Educational scenario overlay",
    },
    {
      id: "base",
      label: "Base",
      portfolioImpact: "Path aligned with weighted expected CAGR when available.",
      expectedReturnDelta: expCagr != null ? `~${expCagr.toFixed(1)}% CAGR context` : null,
      confidence: expCagr != null ? "low" : "insufficient_evidence",
      evidence: "Uses holding expected CAGR fields only",
      methodology: "Weighted presentation CAGR",
    },
    {
      id: "bear",
      label: "Bear",
      portfolioImpact: "Cyclicals and high-weight names drive drawdowns.",
      expectedReturnDelta: expCagr != null ? `~-${(expCagr * 0.5).toFixed(1)} pp (illustrative)` : null,
      confidence: "low",
      evidence: "Scenario narrative",
      methodology: "Educational scenario overlay",
    },
    {
      id: "market_crash",
      label: "Market Crash",
      portfolioImpact: "Largest positions dominate loss path; cash cushion matters.",
      expectedReturnDelta: null,
      confidence: "insufficient_evidence",
      evidence: "No stress-engine in UI",
      methodology: "Qualitative only",
    },
    {
      id: "rate_rise",
      label: "Interest Rate Rise",
      portfolioImpact: "Financials mixed; long-duration growth may de-rate.",
      expectedReturnDelta: null,
      confidence: "insufficient_evidence",
      evidence: "Qualitative",
      methodology: "Educational",
    },
    {
      id: "recession",
      label: "Recession",
      portfolioImpact: "Cyclical sleeves pressured; defensive IT/consumer may fare better.",
      expectedReturnDelta: null,
      confidence: "insufficient_evidence",
      evidence: "Qualitative",
      methodology: "Educational",
    },
    {
      id: "commodity_spike",
      label: "Commodity Spike",
      portfolioImpact: "Limited direct commodity sleeve in this seed — monitor inflation pass-through.",
      expectedReturnDelta: null,
      confidence: "insufficient_evidence",
      evidence: "Seed has weak commodity exposure",
      methodology: "Educational",
    },
    {
      id: "ai_boom",
      label: "AI Boom",
      portfolioImpact: "IT services sleeve may benefit if demand sustains — not guaranteed.",
      expectedReturnDelta: null,
      confidence: "low",
      evidence: "IT weight in seed",
      methodology: "Theme overlay",
    },
    {
      id: "renewable_boom",
      label: "Renewable Boom",
      portfolioImpact: "No dedicated renewable holdings in seed — opportunity gap.",
      expectedReturnDelta: null,
      confidence: "insufficient_evidence",
      evidence: "Theme absent in holdings",
      methodology: "Educational",
    },
  ];

  const qualityDistribution = groupWeights(
    holdings,
    (h) => h.businessQuality ?? "Unavailable",
    total,
  );
  const moatDistribution = groupWeights(
    holdings,
    (h) => h.moatRating ?? "Unavailable",
    total,
  );
  const mosBuckets = holdings.map((h) => {
    if (h.marginOfSafety == null) return { ...h, bucket: "Unavailable" };
    if (h.marginOfSafety < 0) return { ...h, bucket: "Negative MOS" };
    if (h.marginOfSafety < 10) return { ...h, bucket: "0–10%" };
    if (h.marginOfSafety < 20) return { ...h, bucket: "10–20%" };
    return { ...h, bucket: "20%+" };
  });
  const mosDistribution = groupWeights(mosBuckets, (h) => (h as { bucket: string }).bucket, total);

  const empty = holdings.length === 0 && cashAmount <= 0;

  return {
    version: "portfolio-presentation v1 / web-0.7.0",
    asOf,
    currency: "INR",
    cash: metric("cash", "Cash", cashAmount, (n) => money(n), "high", "Session cash balance", meth, asOf),
    holdings,
    watchlist,
    overview: {
      portfolioValue: metric("pv", "Portfolio Value", total > 0 ? total : null, (n) => money(n), "moderate", ev, meth, asOf),
      cashPercent: metric("cash_pct", "Cash %", total > 0 ? (cashAmount / total) * 100 : null, pct, "moderate", ev, meth, asOf),
      investedPercent: metric("inv_pct", "Invested %", total > 0 ? (invested / total) * 100 : null, pct, "moderate", ev, meth, asOf),
      holdingCount: metric("count", "Holdings", holdings.length, (n) => String(n), "high", ev, meth, asOf),
      averageMos: metric("avg_mos", "Average MOS", avgMos, pct, avgMos != null ? "low" : "insufficient_evidence", "Weight-averaged holding MOS where present", meth, asOf),
      averageIntrinsicDiscount: metric("avg_disc", "Average Intrinsic Discount", avgDisc, pct, avgDisc != null ? "low" : "insufficient_evidence", "Weight-averaged (IV−price)/IV", meth, asOf),
      averageQuality: metric("avg_q", "Average Quality", avgQuality, num, avgQuality != null ? "low" : "insufficient_evidence", "Mapped Strong=3 Good=2 Fair=1 — illustrative index", meth, asOf),
      weightedRoce: metric("roce", "Weighted ROCE", weightedRoce, pct, "insufficient_evidence", "ROCE not present on holdings — Unavailable", meth, asOf),
      weightedRoe: metric("roe", "Weighted ROE", weightedRoe, pct, "insufficient_evidence", "ROE not present on holdings — Unavailable", meth, asOf),
      expectedCagr: metric("cagr", "Expected CAGR", expCagr, pct, expCagr != null ? "low" : "insufficient_evidence", "Weight-averaged holding expected CAGR fields", meth, asOf),
      expectedUpside: metric("upside", "Expected Upside", avgDisc, pct, avgDisc != null ? "low" : "insufficient_evidence", "Uses intrinsic discount as upside proxy when IV present", meth, asOf),
      downsideRisk: metric("down", "Downside Risk", maxWeight, pct, "low", "Proxied by largest position weight (presentation heuristic)", meth, asOf),
      concentrationScore: metric("conc", "Concentration Score", concentrationScore, num, "moderate", "Equal to largest position weight %", meth, asOf),
      diversificationScore: metric("div", "Diversification Score", total > 0 ? diversificationScore : null, num, "low", "Heuristic 100 − 1.5× max weight", meth, asOf),
      portfolioRiskScore: metric(
        "prisk",
        "Portfolio Risk Score",
        total > 0 ? Math.min(100, maxWeight + lowConf.length * 5 + (largestSector?.weight ?? 0) * 0.3) : null,
        num,
        "low",
        "Heuristic from concentration + low-confidence count + sector weight",
        meth,
        asOf,
      ),
    },
    risk: {
      largestPosition: metric(
        "lp",
        "Largest Position",
        largest?.weight ?? null,
        (n) => `${largest?.symbol ?? "—"} ${pct(n)}`,
        "moderate",
        largest ? largest.evidence : "No holdings",
        meth,
        asOf,
      ),
      largestSector: metric(
        "ls",
        "Largest Sector",
        largestSector?.weight ?? null,
        (n) => `${largestSector?.label ?? "—"} ${pct(n)}`,
        "moderate",
        "Sum of market values by sector",
        meth,
        asOf,
      ),
      largestDrawdownRisk: metric(
        "ddr",
        "Largest Drawdown Risk",
        maxWeight,
        pct,
        "insufficient_evidence",
        "No path simulation — shown as single-name exposure proxy",
        meth,
        asOf,
      ),
      overvaluedHoldings: overvalued,
      undervaluedHoldings: undervalued,
      highDebtHoldings: highDebt,
      lowConfidenceHoldings: lowConf,
      topRisks: [
        largest ? `Single-name exposure: ${largest.symbol}` : "No holdings",
        largestSector ? `Sector concentration: ${largestSector.label}` : "No sector data",
        ...lowConf.map((s) => `Low confidence: ${s}`),
      ].slice(0, 5),
      topOpportunities: [
        ...undervalued.map((s) => `Wider MOS: ${s}`),
        cashAmount / Math.max(total, 1) > 0.15 ? "Dry powder available to deploy into researched ideas" : "Review watchlist for patient entries",
      ].slice(0, 5),
    },
    allocations: {
      sector: sectorWeights,
      industry: groupWeights(holdings, (h) => h.industry, total),
      marketCap: groupWeights(holdings, (h) => h.marketCapBucket, total),
      country: groupWeights(holdings, (h) => h.country, total),
      theme: groupWeights(holdings, (h) => h.theme, total),
      growthVsValue: groupWeights(
        holdings,
        (h) => (h.theme === "growth" ? "Growth" : h.theme === "value" ? "Value" : "Blend/Unavailable"),
        total,
      ),
      dividendVsGrowth: groupWeights(
        holdings,
        (h) => (h.style === "dividend" ? "Dividend" : h.style === "growth" ? "Growth" : "Blend/Unavailable"),
        total,
      ),
      cyclicalVsDefensive: groupWeights(
        holdings,
        (h) =>
          h.cyclicality === "cyclical"
            ? "Cyclical"
            : h.cyclicality === "defensive"
              ? "Defensive"
              : "Blend/Unavailable",
        total,
      ),
    },
    expectedReturn: {
      expectedCagr: metric("er_cagr", "Expected CAGR", expCagr, pct, expCagr != null ? "low" : "insufficient_evidence", ev, meth, asOf),
      expectedDividendYield: metric("er_div", "Expected Dividend Yield", null, pct, "insufficient_evidence", "Dividend fields not on holdings — Unavailable", meth, asOf),
      expectedTotalReturn: metric("er_tot", "Expected Total Return", expCagr, pct, expCagr != null ? "low" : "insufficient_evidence", "Equals expected CAGR when dividend yield Unavailable", meth, asOf),
      portfolioFairValue: metric("er_fv", "Portfolio Fair Value", total > 0 ? total : null, (n) => money(n), "low", "Uses current market value sum as fair-value stand-in — not a DSP valuation", meth, asOf),
      portfolioIntrinsicValue: metric(
        "er_iv",
        "Portfolio Intrinsic Value",
        hasAnyIv ? intrinsicSum + cashAmount : null,
        (n) => money(n),
        hasAnyIv ? "low" : "insufficient_evidence",
        "Sum of share×IV for holdings with IV + cash; skips Unavailable IVs",
        meth,
        asOf,
      ),
    },
    qualityDistribution,
    moatDistribution,
    mosDistribution,
    rebalance,
    scenarios,
    notes,
    empty,
    disclosures: [
      "Research Mode: DSP does not issue Buy/Sell/Hold recommendations in this UI.",
      "Portfolio Intelligence is presentation-only — not broker-synced and not tax advice.",
      "Rebalance suggestions are educational; no automatic trading.",
      "Unavailable metrics are shown explicitly rather than invented.",
      `Portfolio model version: portfolio-presentation v1 / web-0.7.0`,
      `As of: ${asOf ?? "Unavailable"}`,
    ],
  };
}

export const PORTFOLIO_TOC = [
  { id: "pf_overview", title: "Overview" },
  { id: "pf_holdings", title: "Holdings" },
  { id: "pf_allocations", title: "Allocations" },
  { id: "pf_risk", title: "Risk" },
  { id: "pf_watchlist", title: "Watchlist" },
  { id: "pf_rebalance", title: "Rebalance" },
  { id: "pf_scenarios", title: "Scenarios" },
  { id: "pf_expected", title: "Expected Return" },
  { id: "pf_quality", title: "Quality & Moat" },
  { id: "pf_export", title: "Export" },
  { id: "pf_notes", title: "Notes" },
] as const;

export function confidenceLabel(level: ConfidenceLevel): string {
  return CONFIDENCE_LABELS[level];
}
