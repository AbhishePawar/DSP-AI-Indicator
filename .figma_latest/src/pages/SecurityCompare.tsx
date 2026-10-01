import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { TopBar } from '../components/Nav'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts'

// ─── Types ────────────────────────────────────────────────────────────────────

type StockData = {
  name: string; sector: string; rating: string
  price: string; mcap: string; revenue: string; profit: string
  pe: number
  pb: number | null
  evEbitda: number | null
  dividendYield: number | null
  growth: number
  profitGrowth: number
  epsGrowth: number
  roe: number
  roce: number
  operatingMargin: number
  netMargin: number
  de: number
  interestCoverage: number | null
  fcf: number
  strengths: string[]
  risks: string[]
}

type ComparePhase = null | 'loading' | 'done'

// ─── Static dataset ───────────────────────────────────────────────────────────

const COMPARE_DATA: Record<string, StockData> = {
  TCS: {
    name: 'Tata Consultancy Services', sector: 'IT Services', rating: 'A+',
    price: '₹3,842', mcap: '₹13.9L Cr', revenue: '₹2,41,000 Cr', profit: '₹46,000 Cr',
    pe: 27.4, pb: 14.2, evEbitda: 22.4, dividendYield: 1.4,
    growth: 12.4, profitGrowth: 9.8, epsGrowth: 10.2,
    roe: 51.2, roce: 47.8, operatingMargin: 24.8, netMargin: 19.1,
    de: 0.03, interestCoverage: 142.8, fcf: 92,
    strengths: ['Market leader in IT exports with unmatched scale', 'Exceptional capital efficiency — highest ROE in tier-1 IT', 'Consistent dividend and buyback track record'],
    risks: ['Revenue concentration in developed markets', 'Attrition and talent cost headwinds', 'USD/INR currency risk on earnings'],
  },
  INFY: {
    name: 'Infosys', sector: 'IT Services', rating: 'A',
    price: '₹1,792', mcap: '₹7.5L Cr', revenue: '₹1,53,000 Cr', profit: '₹26,000 Cr',
    pe: 24.1, pb: 7.8, evEbitda: 19.2, dividendYield: 2.8,
    growth: 9.1, profitGrowth: 7.2, epsGrowth: 7.8,
    roe: 32.8, roce: 40.2, operatingMargin: 22.4, netMargin: 17.0,
    de: 0.05, interestCoverage: 89.4, fcf: 88,
    strengths: ['Strong AI/cloud transformation pipeline', 'Margin improvement levers intact', 'Consistent large enterprise deal wins'],
    risks: ['CEO transition execution risk', 'Pricing pressure from hyperscalers', 'Slower growth vs tier-1 peers'],
  },
  WIPRO: {
    name: 'Wipro', sector: 'IT Services', rating: 'B+',
    price: '₹476', mcap: '₹2.5L Cr', revenue: '₹89,000 Cr', profit: '₹11,500 Cr',
    pe: 19.8, pb: 3.8, evEbitda: 14.2, dividendYield: 0.8,
    growth: 4.2, profitGrowth: 3.1, epsGrowth: 3.6,
    roe: 18.4, roce: 22.1, operatingMargin: 16.2, netMargin: 12.9,
    de: 0.04, interestCoverage: 48.2, fcf: 71,
    strengths: ['Improving EBIT margins', 'Diversified geography mix', 'Strategic acquisitions in consulting'],
    risks: ['Weakest growth among tier-1 IT peers', 'Low ROE relative to sector', 'Slower deal conversion cycle'],
  },
  HCLTECH: {
    name: 'HCL Technologies', sector: 'IT Services', rating: 'A',
    price: '₹1,348', mcap: '₹3.7L Cr', revenue: '₹1,07,000 Cr', profit: '₹15,700 Cr',
    pe: 22.3, pb: 6.4, evEbitda: 16.8, dividendYield: 3.4,
    growth: 13.8, profitGrowth: 11.4, epsGrowth: 12.8,
    roe: 24.6, roce: 30.1, operatingMargin: 19.4, netMargin: 14.7,
    de: 0.06, interestCoverage: 62.4, fcf: 80,
    strengths: ['Fastest-growing tier-1 IT company', 'Engineering services vertical leadership', 'Products business provides high-margin moat'],
    risks: ['Products revenue lumpy quarter-to-quarter', 'Margin pressure from aggressive hiring', 'Smaller consulting footprint vs TCS/Infy'],
  },
  TECHM: {
    name: 'Tech Mahindra', sector: 'IT Services', rating: 'B+',
    price: '₹1,284', mcap: '₹1.2L Cr', revenue: '₹51,000 Cr', profit: '₹3,200 Cr',
    pe: 32.4, pb: 3.8, evEbitda: 19.8, dividendYield: 1.2,
    growth: 6.2, profitGrowth: 4.4, epsGrowth: 4.2,
    roe: 12.4, roce: 15.8, operatingMargin: 8.4, netMargin: 6.2,
    de: 0.08, interestCoverage: 22.4, fcf: 58,
    strengths: ['Telecom vertical leadership in IT services', 'New CEO-led turnaround gaining traction', 'Strong BPS/BPO capabilities'],
    risks: ['Margin recovery path still uncertain', 'Telecom client spending volatility', 'Premium P/E for current earnings quality'],
  },
  RELIANCE: {
    name: 'Reliance Industries', sector: 'Energy / Retail / Telecom', rating: 'A+',
    price: '₹2,910', mcap: '₹19.7L Cr', revenue: '₹8,97,000 Cr', profit: '₹67,000 Cr',
    pe: 26.8, pb: 2.2, evEbitda: 14.2, dividendYield: 0.4,
    growth: 18.2, profitGrowth: 14.1, epsGrowth: 15.2,
    roe: 11.2, roce: 9.4, operatingMargin: 12.4, netMargin: 7.5,
    de: 0.38, interestCoverage: 6.4, fcf: 45,
    strengths: ['Conglomerate moat across energy, retail, telecom', 'Jio dominant telecom position', 'Massive scale advantage in distribution'],
    risks: ['Debt-heavy balance sheet vs asset-light peers', 'Capital-intensive new energy transition bet', 'Regulatory exposure across multiple sectors'],
  },
  HDFCBANK: {
    name: 'HDFC Bank', sector: 'Banking', rating: 'A+',
    price: '₹1,674', mcap: '₹12.5L Cr', revenue: '₹2,31,000 Cr', profit: '₹60,000 Cr',
    pe: 18.1, pb: 2.8, evEbitda: null, dividendYield: 1.2,
    growth: 21.4, profitGrowth: 19.2, epsGrowth: 20.4,
    roe: 17.4, roce: 8.2, operatingMargin: 30.8, netMargin: 26.0,
    de: 7.80, interestCoverage: null, fcf: 78,
    strengths: ['Largest private bank by assets in India', 'Best-in-class asset quality and low NPA', 'Strong retail CASA franchise'],
    risks: ['Post-merger integration of HDFC Ltd complex', 'NIM compression from high-cost deposits', 'Credit card delinquency uptick'],
  },
  ICICIBANK: {
    name: 'ICICI Bank', sector: 'Banking', rating: 'A',
    price: '₹1,138', mcap: '₹8.0L Cr', revenue: '₹1,89,000 Cr', profit: '₹44,000 Cr',
    pe: 17.2, pb: 3.2, evEbitda: null, dividendYield: 0.8,
    growth: 19.8, profitGrowth: 23.4, epsGrowth: 24.2,
    roe: 18.2, roce: 7.9, operatingMargin: 28.4, netMargin: 23.2,
    de: 6.90, interestCoverage: null, fcf: 72,
    strengths: ['Best ROE improvement story in Indian banking', 'Strong digital banking transformation', 'Diversified and well-managed loan book'],
    risks: ['Corporate NPA legacy slow to fully resolve', 'SME segment risk in economic slowdown', 'Subsidiary valuations add complexity'],
  },
  KOTAKBANK: {
    name: 'Kotak Mahindra Bank', sector: 'Banking', rating: 'A',
    price: '₹1,842', mcap: '₹3.7L Cr', revenue: '₹98,000 Cr', profit: '₹16,500 Cr',
    pe: 19.4, pb: 3.8, evEbitda: null, dividendYield: 0.2,
    growth: 14.2, profitGrowth: 12.8, epsGrowth: 14.2,
    roe: 14.8, roce: 6.9, operatingMargin: 24.8, netMargin: 20.2,
    de: 5.20, interestCoverage: null, fcf: 65,
    strengths: ['Conservative lending culture and low NPA', 'Strong corporate banking franchise', 'Promoter-aligned management quality'],
    risks: ['Post-Uday Kotak succession clarity needed', 'Loan growth slower than HDFC/ICICI', 'Digital investment payback timeline uncertain'],
  },
  BAJFINANCE: {
    name: 'Bajaj Finance', sector: 'NBFC', rating: 'A',
    price: '₹7,240', mcap: '₹4.4L Cr', revenue: '₹54,000 Cr', profit: '₹16,000 Cr',
    pe: 34.2, pb: 7.8, evEbitda: null, dividendYield: 0.4,
    growth: 28.4, profitGrowth: 22.6, epsGrowth: 24.8,
    roe: 22.8, roce: 12.4, operatingMargin: 38.4, netMargin: 32.4,
    de: 3.80, interestCoverage: null, fcf: 38,
    strengths: ['Market leader in consumer and SME finance', 'Superior cross-sell and data-driven underwriting', 'Consistent 25%+ AUM growth track record'],
    risks: ['Premium valuation leaves no execution margin', 'Rising cost of funds compressing NIMs', 'Credit card business scaling risk'],
  },
  ITC: {
    name: 'ITC Limited', sector: 'FMCG / Tobacco', rating: 'A',
    price: '₹456', mcap: '₹5.7L Cr', revenue: '₹72,000 Cr', profit: '₹20,500 Cr',
    pe: 28.4, pb: 8.4, evEbitda: 22.4, dividendYield: 3.4,
    growth: 8.4, profitGrowth: 11.2, epsGrowth: 12.4,
    roe: 29.4, roce: 36.8, operatingMargin: 36.8, netMargin: 28.4,
    de: 0.01, interestCoverage: 142.4, fcf: 90,
    strengths: ['Cash cow tobacco funds FMCG scale-up', 'Near-zero debt with very high FCF yield', 'Hotels and agri businesses steadily scaling'],
    risks: ['Regulatory risk on cigarette volumes', 'FMCG margins trail HUL benchmark', 'Conglomerate structure creates valuation discount'],
  },
  HINDUNILVR: {
    name: 'Hindustan Unilever', sector: 'FMCG', rating: 'A+',
    price: '₹2,384', mcap: '₹5.6L Cr', revenue: '₹61,000 Cr', profit: '₹10,500 Cr',
    pe: 52.4, pb: 11.4, evEbitda: 42.4, dividendYield: 1.8,
    growth: 5.2, profitGrowth: 4.8, epsGrowth: 5.2,
    roe: 22.4, roce: 27.8, operatingMargin: 24.2, netMargin: 17.2,
    de: 0.02, interestCoverage: 212.4, fcf: 94,
    strengths: ['Unmatched rural distribution to 8M+ outlets', 'Iconic brand portfolio with multi-decade pricing power', 'Highest FCF conversion ratio in Indian FMCG'],
    risks: ['Volume growth structurally under pressure', 'Extreme valuation demands near-flawless execution', 'Rural consumption slowdown risk'],
  },
  MARUTI: {
    name: 'Maruti Suzuki India', sector: 'Automobiles', rating: 'A',
    price: '₹10,840', mcap: '₹3.2L Cr', revenue: '₹1,40,000 Cr', profit: '₹13,500 Cr',
    pe: 26.8, pb: 4.4, evEbitda: 18.4, dividendYield: 0.8,
    growth: 16.2, profitGrowth: 24.8, epsGrowth: 26.4,
    roe: 16.4, roce: 20.8, operatingMargin: 12.4, netMargin: 9.6,
    de: 0.00, interestCoverage: null, fcf: 72,
    strengths: ['~42% market share in Indian passenger vehicles', 'Extensive dealer and service network moat', 'Zero net debt, strong cash generation'],
    risks: ['Late to EV transition relative to global peers', 'Royalty outflows to Suzuki Japan', 'Rising competition from Tata Motors, Hyundai'],
  },
  SUNPHARMA: {
    name: 'Sun Pharmaceutical', sector: 'Pharmaceuticals', rating: 'A',
    price: '₹1,724', mcap: '₹4.1L Cr', revenue: '₹47,000 Cr', profit: '₹10,200 Cr',
    pe: 36.4, pb: 6.8, evEbitda: 24.4, dividendYield: 0.8,
    growth: 14.8, profitGrowth: 16.4, epsGrowth: 18.4,
    roe: 18.4, roce: 22.4, operatingMargin: 24.4, netMargin: 21.7,
    de: 0.08, interestCoverage: 48.4, fcf: 68,
    strengths: ['Largest Indian pharma by market cap', 'Specialty drug pipeline in US gaining traction', 'Strong branded generics in domestic market'],
    risks: ['US FDA compliance history has mixed episodes', 'Specialty product ramp-up timeline uncertain', 'US generics pricing pressure structural'],
  },
  ASIANPAINT: {
    name: 'Asian Paints', sector: 'Consumer / Paints', rating: 'A+',
    price: '₹2,840', mcap: '₹2.7L Cr', revenue: '₹34,000 Cr', profit: '₹5,200 Cr',
    pe: 62.4, pb: 21.4, evEbitda: 52.4, dividendYield: 0.8,
    growth: 6.8, profitGrowth: 4.2, epsGrowth: 4.8,
    roe: 34.8, roce: 44.2, operatingMargin: 18.4, netMargin: 15.3,
    de: 0.01, interestCoverage: 212.4, fcf: 88,
    strengths: ['55%+ market share in decorative paints', 'Unmatched distribution to 80,000+ dealers', 'Strong brand and premium pricing power'],
    risks: ['Extreme valuation demands flawless execution', 'Raw material inflation creates margin cycles', 'New competition from Grasim Birla Opus scaling up'],
  },
  BAJAJ: {
    name: 'Bajaj Auto', sector: 'Automobiles', rating: 'A',
    price: '₹8,640', mcap: '₹2.4L Cr', revenue: '₹44,000 Cr', profit: '₹8,400 Cr',
    pe: 28.4, pb: 8.4, evEbitda: 22.4, dividendYield: 1.6,
    growth: 14.2, profitGrowth: 18.4, epsGrowth: 20.2,
    roe: 28.4, roce: 36.2, operatingMargin: 21.4, netMargin: 19.1,
    de: 0.00, interestCoverage: null, fcf: 82,
    strengths: ['Strong two- and three-wheeler export franchise', 'Zero net debt, highly cash-generative', 'Premium Pulsar/Dominar brand positioning'],
    risks: ['EV transition in two-wheelers creating disruption', 'Dependence on international markets for growth', 'Mass segment less dominant than Hero MotoCorp'],
  },
  NESTLEIND: {
    name: 'Nestle India', sector: 'FMCG', rating: 'A+',
    price: '₹2,148', mcap: '₹2.1L Cr', revenue: '₹17,000 Cr', profit: '₹2,800 Cr',
    pe: 72.4, pb: 82.4, evEbitda: 52.4, dividendYield: 1.2,
    growth: 10.4, profitGrowth: 12.4, epsGrowth: 13.4,
    roe: 122.4, roce: 98.2, operatingMargin: 24.2, netMargin: 16.5,
    de: 0.00, interestCoverage: null, fcf: 92,
    strengths: ['Iconic Maggi and KitKat brands with decades of trust', 'Negative working capital business model', 'Highest ROE in Indian listed FMCG universe'],
    risks: ['Extreme 70× P/E valuation requires near-perfection', 'Single-category concentration vs HUL', 'Growth addressable market smaller than diversified FMCG'],
  },
}

const SECURITIES = Object.keys(COMPARE_DATA)

// ─── Dynamic fallback ──────────────────────────────────────────────────────────

function hashCode(s: string): number {
  let h = 0
  for (const c of s) h = Math.imul(31, h) + c.charCodeAt(0) | 0
  return Math.abs(h)
}

function mockStockData(symbol: string): StockData {
  const h = hashCode(symbol)
  const pe = 12 + (h % 38); const pb = parseFloat((1 + ((h >> 4) % 18) / 2).toFixed(1))
  const roe = 10 + ((h >> 4) % 44); const roce = Math.max(roe - 5, roe - 5 + ((h >> 8) % 14))
  const operatingMargin = 10 + ((h >> 10) % 32); const netMargin = Math.max(5, operatingMargin - 4 - ((h >> 14) % 8))
  const de = parseFloat(((h % 80) / 100 * 1.8).toFixed(2))
  const growth = 3 + ((h >> 12) % 28); const profitGrowth = 2 + ((h >> 20) % 26); const epsGrowth = profitGrowth + ((h >> 24) % 4)
  const fcf = 38 + ((h >> 16) % 57)
  const dividendYield = parseFloat(((h % 50) / 25).toFixed(1))
  const evEbitda = parseFloat((8 + (h % 40) / 2).toFixed(1))
  const ic = de < 0.1 ? null : parseFloat((4 + ((h >> 18) % 120)).toFixed(1))
  const ratings = ['B', 'B+', 'A-', 'A', 'A+']
  return {
    name: symbol, sector: 'Listed Security', rating: ratings[h % ratings.length],
    price: `₹${(200 + (h % 8200)).toLocaleString('en-IN')}`,
    mcap: `₹${(0.3 + ((h % 200) / 10)).toFixed(1)}L Cr`,
    revenue: `₹${(8000 + (h % 180000)).toLocaleString('en-IN')} Cr`,
    profit: `₹${(400 + (h % 28000)).toLocaleString('en-IN')} Cr`,
    pe, pb, evEbitda, dividendYield, growth, profitGrowth, epsGrowth,
    roe, roce, operatingMargin, netMargin, de, interestCoverage: ic, fcf,
    strengths: ['Established market position in its segment', 'Consistent operating performance', 'Improving capital allocation metrics'],
    risks: ['Market competition risk', 'Macro-economic sensitivity', 'Execution risk on growth plans'],
  }
}

function getData(symbol: string): StockData {
  return COMPARE_DATA[symbol] ?? mockStockData(symbol)
}

// ─── Radar (dynamic) ─────────────────────────────────────────────────────────

function buildRadarData(a: StockData, b: StockData) {
  function norm(v: number, lo: number, hi: number) {
    return Math.round(Math.min(100, Math.max(0, ((v - lo) / (hi - lo)) * 100)))
  }
  return [
    { metric: 'Profitability', A: norm(a.roe, 0, 55), B: norm(b.roe, 0, 55) },
    { metric: 'Growth',        A: norm(a.growth, 0, 35), B: norm(b.growth, 0, 35) },
    { metric: 'Margins',       A: norm(a.operatingMargin, 0, 45), B: norm(b.operatingMargin, 0, 45) },
    { metric: 'Valuation',     A: norm(65 - a.pe, -15, 53), B: norm(65 - b.pe, -15, 53) },
    { metric: 'Cash Flow',     A: a.fcf, B: b.fcf },
    { metric: 'Low Debt',      A: norm(2 - a.de, 0, 2), B: norm(2 - b.de, 0, 2) },
  ]
}

// ─── Metric groups definition ─────────────────────────────────────────────────

type ValResult = { num: number | null; str: string }
type WinDir = 'higher' | 'lower' | 'none'
type MetricDef = {
  label: string
  getVal: (d: StockData) => ValResult
  winDir: WinDir
  weight: number  // 0 = not used in weighted score
}
type GroupDef = { title: string; metrics: MetricDef[] }

const fmt = (n: number, decimals = 1) => Number.isInteger(n) ? n.toFixed(0) : n.toFixed(decimals)

const METRIC_GROUPS: GroupDef[] = [
  {
    title: 'VALUATION',
    metrics: [
      { label: 'P/E Ratio',      getVal: d => ({ num: d.pe,            str: `${fmt(d.pe)}×` }),       winDir: 'lower', weight: 1.5 },
      { label: 'P/B Ratio',      getVal: d => ({ num: d.pb,            str: d.pb != null ? `${fmt(d.pb)}×` : 'N/A' }),  winDir: 'lower', weight: 0.5 },
      { label: 'EV / EBITDA',    getVal: d => ({ num: d.evEbitda,      str: d.evEbitda != null ? `${fmt(d.evEbitda)}×` : 'N/A' }), winDir: 'lower', weight: 0.5 },
      { label: 'Dividend Yield', getVal: d => ({ num: d.dividendYield, str: d.dividendYield != null ? `${fmt(d.dividendYield)}%` : 'N/A' }), winDir: 'higher', weight: 0 },
    ],
  },
  {
    title: 'GROWTH',
    metrics: [
      { label: 'Revenue Growth (CAGR)', getVal: d => ({ num: d.growth,       str: `${fmt(d.growth)}%` }),       winDir: 'higher', weight: 2 },
      { label: 'Profit Growth (CAGR)',  getVal: d => ({ num: d.profitGrowth, str: `${fmt(d.profitGrowth)}%` }), winDir: 'higher', weight: 2 },
      { label: 'EPS Growth',            getVal: d => ({ num: d.epsGrowth,    str: `${fmt(d.epsGrowth)}%` }),    winDir: 'higher', weight: 1 },
    ],
  },
  {
    title: 'PROFITABILITY',
    metrics: [
      { label: 'ROE',              getVal: d => ({ num: d.roe,             str: `${fmt(d.roe)}%` }),             winDir: 'higher', weight: 3 },
      { label: 'ROCE',             getVal: d => ({ num: d.roce,            str: `${fmt(d.roce)}%` }),            winDir: 'higher', weight: 3 },
      { label: 'Operating Margin', getVal: d => ({ num: d.operatingMargin, str: `${fmt(d.operatingMargin)}%` }), winDir: 'higher', weight: 2.5 },
      { label: 'Net Profit Margin',getVal: d => ({ num: d.netMargin,       str: `${fmt(d.netMargin)}%` }),       winDir: 'higher', weight: 2 },
    ],
  },
  {
    title: 'FINANCIAL STRENGTH',
    metrics: [
      { label: 'Debt / Equity',      getVal: d => ({ num: d.de,               str: `${d.de}×` }),                                                           winDir: 'lower',  weight: 2 },
      { label: 'Interest Coverage',  getVal: d => ({ num: d.interestCoverage, str: d.interestCoverage != null ? `${fmt(d.interestCoverage)}×` : 'N/A' }),    winDir: 'higher', weight: 1 },
      { label: 'FCF Quality Score',  getVal: d => ({ num: d.fcf,              str: `${d.fcf} / 100` }),                                                       winDir: 'higher', weight: 2 },
    ],
  },
  {
    title: 'SCALE / BUSINESS',
    metrics: [
      { label: 'Current Price',  getVal: d => ({ num: null, str: d.price }),   winDir: 'none', weight: 0 },
      { label: 'Market Cap',     getVal: d => ({ num: null, str: d.mcap }),    winDir: 'none', weight: 0 },
      { label: 'Revenue',        getVal: d => ({ num: null, str: d.revenue }), winDir: 'none', weight: 0 },
      { label: 'Net Profit',     getVal: d => ({ num: null, str: d.profit }),  winDir: 'none', weight: 0 },
    ],
  },
  {
    title: 'DSP RESEARCH FACTORS',
    metrics: [
      { label: 'DSP Quality Rating', getVal: d => {
        const order: Record<string, number> = { B: 1, 'B+': 2, 'A-': 3, A: 4, 'A+': 5 }
        return { num: order[d.rating] ?? 3, str: d.rating }
      }, winDir: 'higher', weight: 2 },
      { label: 'Business Sector',    getVal: d => ({ num: null, str: d.sector }), winDir: 'none', weight: 0 },
    ],
  },
]

// ─── Weighted scoring for final verdict ───────────────────────────────────────

function computeScore(a: StockData, b: StockData) {
  let aScore = 0; let bScore = 0; let maxPossible = 0
  for (const group of METRIC_GROUPS) {
    for (const m of group.metrics) {
      if (m.weight === 0 || m.winDir === 'none') continue
      const av = m.getVal(a).num; const bv = m.getVal(b).num
      if (av == null || bv == null || av === bv) continue
      maxPossible += m.weight
      const aWins = m.winDir === 'higher' ? av > bv : av < bv
      if (aWins) aScore += m.weight; else bScore += m.weight
    }
  }
  return { aScore, bScore, maxPossible }
}

// ─── Generate dynamic why-reasons ────────────────────────────────────────────

function generateReasons(winner: StockData, loser: StockData, winSym: string, loseSym: string): string[] {
  const out: string[] = []
  if (winner.roe > loser.roe + 4)
    out.push(`Superior capital efficiency: ${winSym} delivers ROE of ${fmt(winner.roe)}% vs ${fmt(loser.roe)}%, compounding equity at a significantly higher rate.`)
  if (winner.roce > loser.roce + 4)
    out.push(`Higher return on capital employed (${fmt(winner.roce)}% vs ${fmt(loser.roce)}%), indicating a stronger and more durable business moat.`)
  if (winner.operatingMargin > loser.operatingMargin + 3)
    out.push(`Better operational efficiency with ${fmt(winner.operatingMargin)}% operating margin vs ${fmt(loser.operatingMargin)}%, reflecting stronger pricing power and cost discipline.`)
  if (winner.growth > loser.growth + 4)
    out.push(`Faster revenue growth (${fmt(winner.growth)}% CAGR vs ${fmt(loser.growth)}%), pointing to a stronger competitive trajectory and expanding addressable market.`)
  if (winner.profitGrowth > loser.profitGrowth + 4)
    out.push(`Stronger profit growth (${fmt(winner.profitGrowth)}% vs ${fmt(loser.profitGrowth)}%): earnings are compounding faster, improving intrinsic value at pace.`)
  if (winner.de < loser.de - 0.25 && loser.de > 0.25)
    out.push(`Cleaner balance sheet (D/E ${winner.de}× vs ${loser.de}×): lower financial leverage reduces risk and preserves strategic flexibility.`)
  if (winner.fcf > loser.fcf + 8)
    out.push(`Superior free cash flow quality (score ${winner.fcf} vs ${loser.fcf} / 100), indicating stronger ability to self-fund growth and return capital to shareholders.`)
  if (winner.pe < loser.pe - 5 && loser.pe > 0)
    out.push(`More attractive valuation at ${fmt(winner.pe)}× P/E vs ${fmt(loser.pe)}×, offering better risk-adjusted return potential at the current price.`)
  const ratingOrder: Record<string, number> = { B: 1, 'B+': 2, 'A-': 3, A: 4, 'A+': 5 }
  if ((ratingOrder[winner.rating] ?? 3) > (ratingOrder[loser.rating] ?? 3))
    out.push(`Higher DSP quality rating (${winner.rating} vs ${loser.rating}), reflecting a stronger fundamental profile across 40+ research metrics.`)
  if (out.length < 2) winner.strengths.slice(0, 3 - out.length).forEach(s => out.push(s + '.'))
  return out.slice(0, 5)
}

// ─── Key trade-off for one security ──────────────────────────────────────────

function getTradeoff(data: StockData, other: StockData, sym: string, otherSym: string) {
  let strength = data.strengths[0]
  let weakness = data.risks[0]
  if (data.roe > other.roe + 5)
    strength = `Superior capital efficiency (ROE ${fmt(data.roe)}% vs ${otherSym}'s ${fmt(other.roe)}%)`
  else if (data.growth > other.growth + 5)
    strength = `Faster growth trajectory (${fmt(data.growth)}% vs ${otherSym}'s ${fmt(other.growth)}% revenue CAGR)`
  else if (data.de < other.de - 0.3 && other.de > 0.3)
    strength = `Stronger balance sheet (D/E ${data.de}× vs ${otherSym}'s ${other.de}×)`
  else if (data.operatingMargin > other.operatingMargin + 4)
    strength = `Better operating margin (${fmt(data.operatingMargin)}% vs ${otherSym}'s ${fmt(other.operatingMargin)}%)`
  if (data.roe < other.roe - 5)
    weakness = `Lower capital efficiency (ROE ${fmt(data.roe)}% vs ${otherSym}'s ${fmt(other.roe)}%) may limit long-term compounding`
  else if (data.growth < other.growth - 5)
    weakness = `Slower growth (${fmt(data.growth)}% vs ${otherSym}'s ${fmt(other.growth)}% CAGR) may disappoint growth-oriented investors`
  else if (data.de > other.de + 0.3 && data.de > 0.3)
    weakness = `Higher leverage (D/E ${data.de}× vs ${otherSym}'s ${other.de}×) adds financial risk`
  else if (data.pe > other.pe + 6)
    weakness = `Premium valuation (P/E ${fmt(data.pe)}× vs ${otherSym}'s ${fmt(other.pe)}×) requires consistent execution to justify`
  return { strength, weakness }
}

// ─── Constants ───────────────────────────────────────────────────────────────

const A_COLOR = 'var(--c-revenue)'  // blue/cyan — Security 1
const B_COLOR = 'var(--c-profit)'   // green — Security 2

// ─── Sub-components ───────────────────────────────────────────────────────────

function RatingBadge({ r }: { r: string }) {
  const color = r === 'A+' ? 'var(--c-dsp)' : r.startsWith('A') ? 'var(--c-profit)' : 'var(--c-valuation)'
  return (
    <span style={{ fontSize: 13, color, fontFamily: 'var(--font-data)', background: `color-mix(in srgb, ${color} 14%, transparent)`, borderRadius: 8, padding: '4px 10px', fontWeight: 700, border: `1px solid color-mix(in srgb, ${color} 30%, transparent)` }}>
      {r}
    </span>
  )
}

function SecuritySelect({ value, onChange, label }: { value: string; onChange: (v: string) => void; label: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</span>
      <select value={value} onChange={e => onChange(e.target.value)}
        style={{ background: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', color: 'var(--foreground)', fontSize: 13, fontFamily: 'var(--font-data)', cursor: 'pointer', outline: 'none', minWidth: 120 }}>
        {SECURITIES.map(s => <option key={s} value={s} style={{ background: 'var(--card)' }}>{s}</option>)}
      </select>
    </div>
  )
}

// ─── Loading ──────────────────────────────────────────────────────────────────

const ANALYSIS_STEPS = ['Fetching market fundamentals', 'Computing quality scores', 'Running Buffett analysis', 'Generating comparative insights']

function CompareLoading({ secA, secB }: { secA: string; secB: string }) {
  const [progress, setProgress] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setProgress(p => Math.min(p + 1, ANALYSIS_STEPS.length - 1)), 550)
    return () => clearInterval(t)
  }, [])
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '28px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--c-dsp)', boxShadow: '0 0 8px var(--c-dsp)' }} />
        <span style={{ fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-body)', fontWeight: 500 }}>Analysing both securities simultaneously…</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {([{ sym: secA, color: A_COLOR }, { sym: secB, color: B_COLOR }]).map(({ sym, color }) => (
          <div key={sym} style={{ border: `1px solid color-mix(in srgb, ${color} 30%, transparent)`, borderRadius: 10, padding: '16px 18px', borderTop: `2px solid ${color}` }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--foreground)', fontFamily: 'var(--font-data)', marginBottom: 14 }}>{sym}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
              {ANALYSIS_STEPS.map((step, i) => {
                const done = i <= progress
                return (
                  <div key={step} style={{ display: 'flex', alignItems: 'center', gap: 10, opacity: done ? 1 : 0.3, transition: 'opacity 0.4s' }}>
                    <div style={{ width: 18, height: 18, borderRadius: '50%', flexShrink: 0, background: done ? `color-mix(in srgb, ${color} 20%, transparent)` : 'var(--muted)', border: `1.5px solid ${done ? color : 'var(--border)'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.3s' }}>
                      {done && <span style={{ fontSize: 9, color }}>✓</span>}
                    </div>
                    <span style={{ fontSize: 12, color: done ? 'var(--foreground)' : 'var(--muted-foreground)', fontFamily: 'var(--font-data)', transition: 'color 0.3s' }}>{step}</span>
                  </div>
                )
              })}
            </div>
            <div style={{ marginTop: 14, height: 3, background: 'var(--muted)', borderRadius: 99, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${((progress + 1) / ANALYSIS_STEPS.length) * 100}%`, background: color, borderRadius: 99, transition: 'width 0.5s ease' }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Comparison table row ─────────────────────────────────────────────────────

function MetricRow({ metric, a, b, secA, secB, rowIndex }: {
  metric: MetricDef; a: StockData; b: StockData; secA: string; secB: string; rowIndex: number
}) {
  const aResult = metric.getVal(a)
  const bResult = metric.getVal(b)
  const av = aResult.num; const bv = bResult.num

  let winner: 'a' | 'b' | null = null
  if (metric.winDir !== 'none' && av != null && bv != null && av !== bv) {
    winner = metric.winDir === 'higher' ? (av > bv ? 'a' : 'b') : (av < bv ? 'a' : 'b')
  }

  const rowBg = rowIndex % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)'

  return (
    <tr style={{ background: rowBg }}>
      <td style={{ padding: '10px 16px', fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', whiteSpace: 'nowrap', borderRight: '1px solid var(--border)' }}>
        {metric.label}
      </td>
      <td style={{ padding: '10px 18px', borderRight: '1px solid var(--border)' }}>
        <span style={{
          fontSize: 13, fontFamily: 'var(--font-data)',
          color: winner === 'a' ? A_COLOR : 'var(--foreground)',
          fontWeight: winner === 'a' ? 700 : 400,
          background: winner === 'a' ? `color-mix(in srgb, ${A_COLOR} 8%, transparent)` : 'transparent',
          borderRadius: 6, padding: winner === 'a' ? '2px 7px' : '2px 0',
          display: 'inline-block',
        }}>
          {aResult.str}
        </span>
      </td>
      <td style={{ padding: '10px 18px', borderRight: '1px solid var(--border)' }}>
        <span style={{
          fontSize: 13, fontFamily: 'var(--font-data)',
          color: winner === 'b' ? B_COLOR : 'var(--foreground)',
          fontWeight: winner === 'b' ? 700 : 400,
          background: winner === 'b' ? `color-mix(in srgb, ${B_COLOR} 8%, transparent)` : 'transparent',
          borderRadius: 6, padding: winner === 'b' ? '2px 7px' : '2px 0',
          display: 'inline-block',
        }}>
          {bResult.str}
        </span>
      </td>
      <td style={{ padding: '10px 14px' }}>
        {winner ? (
          <span style={{
            fontSize: 11, fontFamily: 'var(--font-data)', fontWeight: 600,
            color: winner === 'a' ? A_COLOR : B_COLOR,
            background: winner === 'a' ? `color-mix(in srgb, ${A_COLOR} 12%, transparent)` : `color-mix(in srgb, ${B_COLOR} 12%, transparent)`,
            border: `1px solid ${winner === 'a' ? `color-mix(in srgb, ${A_COLOR} 30%, transparent)` : `color-mix(in srgb, ${B_COLOR} 30%, transparent)`}`,
            borderRadius: 6, padding: '3px 8px', whiteSpace: 'nowrap',
          }}>
            {winner === 'a' ? secA : secB}
          </span>
        ) : (
          <span style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>—</span>
        )}
      </td>
    </tr>
  )
}

// ─── Comparison table ─────────────────────────────────────────────────────────

function ComparisonTable({ a, b, secA, secB }: { a: StockData; b: StockData; secA: string; secB: string }) {
  let rowIdx = 0
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 620 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid var(--border)' }}>
            <th style={{ padding: '14px 16px', fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', textAlign: 'left', width: 160, borderRight: '1px solid var(--border)' }}>
              METRIC
            </th>
            <th style={{ padding: '14px 18px', textAlign: 'left', borderRight: '1px solid var(--border)', minWidth: 160 }}>
              <div style={{ fontSize: 9, color: A_COLOR, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 3 }}>SECURITY 1</div>
              <div style={{ fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-data)', fontWeight: 700 }}>{secA}</div>
              <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', marginTop: 2 }}>{a.name}</div>
            </th>
            <th style={{ padding: '14px 18px', textAlign: 'left', borderRight: '1px solid var(--border)', minWidth: 160 }}>
              <div style={{ fontSize: 9, color: B_COLOR, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 3 }}>SECURITY 2</div>
              <div style={{ fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-data)', fontWeight: 700 }}>{secB}</div>
              <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', marginTop: 2 }}>{b.name}</div>
            </th>
            <th style={{ padding: '14px 14px', fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', textAlign: 'left', width: 100 }}>
              WINNER
            </th>
          </tr>
        </thead>
        <tbody>
          {METRIC_GROUPS.map(group => (
            <>
              <tr key={group.title}>
                <td colSpan={4} style={{ padding: '10px 16px 6px', fontSize: 10, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', background: 'rgba(124,106,247,0.06)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
                  {group.title}
                </td>
              </tr>
              {group.metrics.map(metric => {
                const ri = rowIdx++
                return <MetricRow key={metric.label} metric={metric} a={a} b={b} secA={secA} secB={secB} rowIndex={ri} />
              })}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Important Differences ────────────────────────────────────────────────────

function ImportantDifferences({ a, b, secA, secB }: { a: StockData; b: StockData; secA: string; secB: string }) {
  const diffs = [
    {
      cat: 'VALUATION',
      aObs: `P/E ${fmt(a.pe)}× — ${a.pe < b.pe ? `cheaper than ${secB}, offering a more attractive entry point` : a.pe > b.pe ? `at a premium to ${secB}, pricing in higher growth expectations` : `at parity with ${secB}`}.${a.pb != null ? ` P/B ${fmt(a.pb)}×.` : ''}`,
      bObs: `P/E ${fmt(b.pe)}× — ${b.pe < a.pe ? `cheaper than ${secA}, offering a more attractive entry point` : b.pe > a.pe ? `at a premium to ${secA}` : `at parity with ${secA}`}.${b.pb != null ? ` P/B ${fmt(b.pb)}×.` : ''}`,
    },
    {
      cat: 'PROFITABILITY',
      aObs: `ROE ${fmt(a.roe)}%, ROCE ${fmt(a.roce)}%, Operating Margin ${fmt(a.operatingMargin)}% — ${a.roe > b.roe ? `superior capital returns vs ${secB}` : a.roe < b.roe ? `trails ${secB} on capital efficiency` : `matched ${secB}`}.`,
      bObs: `ROE ${fmt(b.roe)}%, ROCE ${fmt(b.roce)}%, Operating Margin ${fmt(b.operatingMargin)}% — ${b.roe > a.roe ? `superior capital returns vs ${secA}` : b.roe < a.roe ? `trails ${secA} on capital efficiency` : `matched ${secA}`}.`,
    },
    {
      cat: 'GROWTH',
      aObs: `Revenue CAGR ${fmt(a.growth)}%, Profit growth ${fmt(a.profitGrowth)}% — ${a.growth > b.growth ? `growing faster than ${secB}` : a.growth < b.growth ? `growing more slowly than ${secB}` : `matched ${secB} in growth pace`}.`,
      bObs: `Revenue CAGR ${fmt(b.growth)}%, Profit growth ${fmt(b.profitGrowth)}% — ${b.growth > a.growth ? `growing faster than ${secA}` : b.growth < a.growth ? `growing more slowly than ${secA}` : `matched ${secA} in growth pace`}.`,
    },
    {
      cat: 'BALANCE SHEET',
      aObs: `D/E ${a.de}× — ${a.de < b.de ? `more conservatively financed than ${secB}` : a.de > b.de ? `carries more leverage than ${secB}` : `similar leverage to ${secB}`}; ${a.de < 0.05 ? 'virtually debt-free' : a.de < 0.4 ? 'low leverage' : a.de < 2 ? 'moderate leverage' : 'significant leverage'}. FCF score: ${a.fcf}/100.`,
      bObs: `D/E ${b.de}× — ${b.de < a.de ? `more conservatively financed than ${secA}` : b.de > a.de ? `carries more leverage than ${secA}` : `similar leverage to ${secA}`}; ${b.de < 0.05 ? 'virtually debt-free' : b.de < 0.4 ? 'low leverage' : b.de < 2 ? 'moderate leverage' : 'significant leverage'}. FCF score: ${b.fcf}/100.`,
    },
  ]

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'rgba(124,106,247,0.04)' }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-heading)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Important Differences</span>
      </div>
      <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {diffs.map(d => (
          <div key={d.cat}>
            <div style={{ fontSize: 10, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>{d.cat}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div style={{ background: `color-mix(in srgb, ${A_COLOR} 5%, var(--secondary))`, border: `1px solid color-mix(in srgb, ${A_COLOR} 15%, var(--border))`, borderRadius: 8, padding: '10px 12px' }}>
                <div style={{ fontSize: 9, color: A_COLOR, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 5 }}>SECURITY 1 · {secA}</div>
                <div style={{ fontSize: 12, color: 'var(--foreground)', fontFamily: 'var(--font-data)', lineHeight: 1.55 }}>{d.aObs}</div>
              </div>
              <div style={{ background: `color-mix(in srgb, ${B_COLOR} 5%, var(--secondary))`, border: `1px solid color-mix(in srgb, ${B_COLOR} 15%, var(--border))`, borderRadius: 8, padding: '10px 12px' }}>
                <div style={{ fontSize: 9, color: B_COLOR, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 5 }}>SECURITY 2 · {secB}</div>
                <div style={{ fontSize: 12, color: 'var(--foreground)', fontFamily: 'var(--font-data)', lineHeight: 1.55 }}>{d.bObs}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Final verdict ────────────────────────────────────────────────────────────

function FinalVerdict({ a, b, secA, secB }: { a: StockData; b: StockData; secA: string; secB: string }) {
  const { aScore, bScore, maxPossible } = computeScore(a, b)
  const margin = maxPossible > 0 ? Math.abs(aScore - bScore) / maxPossible : 0
  const isInsufficient = maxPossible < 4
  const isClose = margin < 0.12 && !isInsufficient

  let winner: 'a' | 'b' | null = null
  if (!isInsufficient) {
    if (aScore > bScore) winner = 'a'
    else if (bScore > aScore) winner = 'b'
  }

  const winSym = winner === 'a' ? secA : winner === 'b' ? secB : null
  const winData = winner === 'a' ? a : winner === 'b' ? b : null
  const loseSym = winner === 'a' ? secB : winner === 'b' ? secA : null
  const loseData = winner === 'a' ? b : winner === 'b' ? a : null
  const winColor = winner === 'a' ? A_COLOR : winner === 'b' ? B_COLOR : 'var(--c-dsp)'

  const reasons = winData && loseData && winSym && loseSym
    ? generateReasons(winData, loseData, winSym, loseSym)
    : []

  const toA = getTradeoff(a, b, secA, secB)
  const toB = getTradeoff(b, a, secB, secA)

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', background: 'linear-gradient(135deg, rgba(124,106,247,0.08) 0%, rgba(45,212,191,0.04) 100%)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 3, height: 22, background: 'linear-gradient(180deg, #7c6af7, #2dd4bf)', borderRadius: 99 }} />
        <div>
          <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>DSP Comparative Analysis</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-heading)', marginTop: 2 }}>FINAL COMPARISON — WHICH SECURITY IS BETTER?</div>
        </div>
      </div>

      <div style={{ padding: '24px' }}>
        {/* vs. card */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 60px 1fr', gap: 12, alignItems: 'center', marginBottom: 24 }}>
          {[{ sym: secA, data: a, color: A_COLOR, label: 'SECURITY 1' }, null, { sym: secB, data: b, color: B_COLOR, label: 'SECURITY 2' }].map((item, idx) => {
            if (!item) return <div key="vs" style={{ textAlign: 'center' }}><span style={{ fontSize: 16, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>VS</span></div>
            const isWinner = (idx === 0 && winner === 'a') || (idx === 2 && winner === 'b')
            return (
              <div key={item.sym} style={{ border: `1.5px solid ${isWinner ? item.color : 'var(--border)'}`, borderRadius: 12, padding: '16px 18px', background: isWinner ? `color-mix(in srgb, ${item.color} 5%, var(--secondary))` : 'var(--secondary)', position: 'relative', transition: 'all 0.2s' }}>
                {isWinner && <div style={{ position: 'absolute', top: -11, left: '50%', transform: 'translateX(-50%)', background: item.color, color: '#fff', fontSize: 9, fontFamily: 'var(--font-data)', fontWeight: 700, letterSpacing: '0.1em', padding: '3px 10px', borderRadius: 99 }}>STRONGER</div>}
                <div style={{ fontSize: 9, color: item.color, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>{item.label}</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{item.sym}</div>
                <div style={{ fontSize: 12, color: 'var(--muted-foreground)', marginTop: 3, fontFamily: 'var(--font-data)' }}>{item.data.name}</div>
                <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center' }}>
                  <RatingBadge r={item.data.rating} />
                  <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{item.data.sector}</span>
                </div>
              </div>
            )
          })}
        </div>

        {/* Verdict */}
        {isInsufficient ? (
          <div style={{ background: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 20px', marginBottom: 20, textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>INSUFFICIENT DATA FOR A RELIABLE OVERALL RESULT</div>
            <div style={{ fontSize: 13, color: 'var(--foreground)', marginTop: 6, fontFamily: 'var(--font-body)' }}>Not enough comparable data points are available to determine a meaningful winner.</div>
          </div>
        ) : isClose ? (
          <div style={{ background: `color-mix(in srgb, var(--c-valuation) 6%, var(--secondary))`, border: `1px solid color-mix(in srgb, var(--c-valuation) 20%, var(--border))`, borderRadius: 10, padding: '16px 20px', marginBottom: 20 }}>
            <div style={{ fontSize: 10, color: 'var(--c-valuation)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>OVERALL RESULT — CLOSE CALL</div>
            <div style={{ fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-body)', lineHeight: 1.6 }}>
              {winSym
                ? <><span style={{ color: winColor, fontWeight: 600 }}>{winSym}</span> has a slight edge (weighted score {Math.round(winner === 'a' ? aScore : bScore)} vs {Math.round(winner === 'a' ? bScore : aScore)}), but the margin is narrow. Both securities are competitive across key factors.</>
                : 'Both securities are evenly matched across the DSP analysis framework. No clear overall winner can be determined from the available data.'}
            </div>
          </div>
        ) : winSym && winData ? (
          <div style={{ background: `color-mix(in srgb, ${winColor} 6%, var(--secondary))`, border: `1px solid color-mix(in srgb, ${winColor} 25%, var(--border))`, borderLeft: `4px solid ${winColor}`, borderRadius: 10, padding: '18px 20px', marginBottom: 20 }}>
            <div style={{ fontSize: 10, color: winColor, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>OVERALL RESULT</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 6 }}>
              <span style={{ fontSize: 24, fontWeight: 800, color: winColor, fontFamily: 'var(--font-data)' }}>{winSym}</span>
              <span style={{ fontSize: 13, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{winData.name}</span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-body)' }}>
              Stronger overall according to the DSP analysis framework.{' '}
              <span style={{ color: 'var(--muted-foreground)' }}>
                (Weighted score: {secA} {Math.round(aScore)} — {secB} {Math.round(bScore)})
              </span>
            </div>
          </div>
        ) : (
          <div style={{ background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 20px', marginBottom: 20, textAlign: 'center' }}>
            <div style={{ fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-body)' }}>Both securities are equally matched. No single overall winner can be determined.</div>
          </div>
        )}

        {/* Why reasons */}
        {reasons.length > 0 && winSym && (
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>WHY {winSym}?</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {reasons.map((r, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                  <span style={{ fontSize: 14, color: winColor, flexShrink: 0, marginTop: -1 }}>•</span>
                  <span style={{ fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-data)', lineHeight: 1.55 }}>{r}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Key trade-offs */}
        <div>
          <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>KEY TRADE-OFFS</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { sym: secA, color: A_COLOR, to: toA, label: 'SECURITY 1' },
              { sym: secB, color: B_COLOR, to: toB, label: 'SECURITY 2' },
            ].map(item => (
              <div key={item.sym} style={{ border: `1px solid color-mix(in srgb, ${item.color} 20%, var(--border))`, borderRadius: 10, padding: '14px 16px', borderTop: `2px solid ${item.color}` }}>
                <div style={{ fontSize: 9, color: item.color, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>{item.label} · {item.sym}</div>
                <div style={{ display: 'flex', gap: 7, alignItems: 'flex-start', marginBottom: 7 }}>
                  <span style={{ fontSize: 14, color: 'var(--c-profit)', flexShrink: 0 }}>+</span>
                  <span style={{ fontSize: 12, color: 'var(--foreground)', fontFamily: 'var(--font-data)', lineHeight: 1.5 }}>{item.to.strength}</span>
                </div>
                <div style={{ display: 'flex', gap: 7, alignItems: 'flex-start' }}>
                  <span style={{ fontSize: 14, color: 'var(--c-risk)', flexShrink: 0 }}>−</span>
                  <span style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', lineHeight: 1.5 }}>{item.to.weakness}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Full compare result ──────────────────────────────────────────────────────

function CompareResult({ a, b, secA, secB, onReset }: { a: StockData; b: StockData; secA: string; secB: string; onReset: () => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Section header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 3, height: 20, background: 'var(--c-dsp)', borderRadius: 99 }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-heading)' }}>Comparative Analysis</span>
          <span style={{ fontSize: 11, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', background: 'rgba(124,106,247,0.12)', borderRadius: 6, padding: '2px 8px' }}>
            {secA} vs {secB}
          </span>
        </div>
        <button onClick={onReset} style={{ fontSize: 11, color: 'var(--muted-foreground)', background: 'none', border: '1px solid var(--border)', borderRadius: 7, padding: '4px 10px', cursor: 'pointer', fontFamily: 'var(--font-data)' }}>
          Clear
        </button>
      </div>

      {/* Primary: comparison table */}
      <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', background: 'rgba(124,106,247,0.04)' }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-heading)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Financial Comparison</span>
        </div>
        <ComparisonTable a={a} b={b} secA={secA} secB={secB} />
      </div>

      {/* Important differences */}
      <ImportantDifferences a={a} b={b} secA={secA} secB={secB} />

      {/* Final verdict */}
      <FinalVerdict a={a} b={b} secA={secA} secB={secB} />
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function SecurityCompare() {
  const [secA, setSecA] = useState('TCS')
  const [secB, setSecB] = useState('INFY')
  const [comparePhase, setComparePhase] = useState<ComparePhase>(null)
  const navigate = useNavigate()

  const a = getData(secA)
  const b = getData(secB)
  const sameSelected = secA === secB
  const radarData = buildRadarData(a, b)

  function handleSecAChange(v: string) { setSecA(v); setComparePhase(null) }
  function handleSecBChange(v: string) { setSecB(v); setComparePhase(null) }

  function startCompare() {
    if (sameSelected) return
    setComparePhase('loading')
    setTimeout(() => setComparePhase('done'), 2400)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Security Compare" subtitle="Side-by-side financial comparison" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Selector + actions */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '18px 22px', display: 'flex', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
          <SecuritySelect value={secA} onChange={handleSecAChange} label="Security 1" />
          <span style={{ fontSize: 20, color: 'var(--muted-foreground)', paddingBottom: 6 }}>⇌</span>
          <SecuritySelect value={secB} onChange={handleSecBChange} label="Security 2" />
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              onClick={() => navigate(`/analysis?symbol=${secA}`)}
              style={{ fontSize: 12, color: A_COLOR, background: `color-mix(in srgb, ${A_COLOR} 10%, transparent)`, border: `1px solid color-mix(in srgb, ${A_COLOR} 25%, transparent)`, borderRadius: 8, padding: '8px 14px', cursor: 'pointer', fontFamily: 'var(--font-body)', transition: 'all 0.15s', display: 'flex', alignItems: 'center', gap: 5 }}
              onMouseEnter={e => { e.currentTarget.style.background = `color-mix(in srgb, ${A_COLOR} 18%, transparent)`; e.currentTarget.style.borderColor = A_COLOR }}
              onMouseLeave={e => { e.currentTarget.style.background = `color-mix(in srgb, ${A_COLOR} 10%, transparent)`; e.currentTarget.style.borderColor = `color-mix(in srgb, ${A_COLOR} 25%, transparent)` }}
            >
              ↗ Research {secA}
            </button>
            <button
              onClick={() => navigate(`/analysis?symbol=${secB}`)}
              style={{ fontSize: 12, color: B_COLOR, background: `color-mix(in srgb, ${B_COLOR} 10%, transparent)`, border: `1px solid color-mix(in srgb, ${B_COLOR} 25%, transparent)`, borderRadius: 8, padding: '8px 14px', cursor: 'pointer', fontFamily: 'var(--font-body)', transition: 'all 0.15s', display: 'flex', alignItems: 'center', gap: 5 }}
              onMouseEnter={e => { e.currentTarget.style.background = `color-mix(in srgb, ${B_COLOR} 18%, transparent)`; e.currentTarget.style.borderColor = B_COLOR }}
              onMouseLeave={e => { e.currentTarget.style.background = `color-mix(in srgb, ${B_COLOR} 10%, transparent)`; e.currentTarget.style.borderColor = `color-mix(in srgb, ${B_COLOR} 25%, transparent)` }}
            >
              ↗ Research {secB}
            </button>
            <div style={{ width: 1, height: 28, background: 'var(--border)' }} />
            <button
              onClick={startCompare}
              disabled={sameSelected || comparePhase === 'loading'}
              title={sameSelected ? 'Select two different securities to compare' : undefined}
              style={{ fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-body)', color: sameSelected ? 'var(--muted-foreground)' : '#fff', background: sameSelected ? 'var(--muted)' : 'linear-gradient(135deg, #7c6af7 0%, #2dd4bf 100%)', border: 'none', borderRadius: 8, padding: '8px 18px', cursor: sameSelected || comparePhase === 'loading' ? 'not-allowed' : 'pointer', opacity: comparePhase === 'loading' ? 0.7 : 1, transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: 6, boxShadow: sameSelected ? 'none' : '0 2px 12px rgba(124,106,247,0.3)' }}
              onMouseEnter={e => { if (!sameSelected) e.currentTarget.style.opacity = '0.88' }}
              onMouseLeave={e => { e.currentTarget.style.opacity = comparePhase === 'loading' ? '0.7' : '1' }}
            >
              {comparePhase === 'loading' ? '⟳ Analysing…' : '⊗ Compare Both Securities'}
            </button>
          </div>
        </div>

        {/* Header cards — always visible */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 16, alignItems: 'start' }}>
          {[{ data: a, sym: secA, color: A_COLOR, lbl: 'SECURITY 1' }, null, { data: b, sym: secB, color: B_COLOR, lbl: 'SECURITY 2' }].map((item, idx) => {
            if (!item) return <div key="vs" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', paddingTop: 24 }}><span style={{ fontSize: 18, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>vs</span></div>
            return (
              <div key={idx} style={{ background: 'var(--card)', border: `1px solid color-mix(in srgb, ${item.color} 20%, var(--border))`, borderRadius: 12, padding: '20px', borderTop: `2px solid ${item.color}` }}>
                <div style={{ fontSize: 9, color: item.color, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>{item.lbl}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                  <div>
                    <div style={{ fontSize: 20, fontFamily: 'var(--font-data)', color: 'var(--foreground)', fontWeight: 700 }}>{item.sym}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted-foreground)', marginTop: 2 }}>{item.data.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--muted-foreground)', marginTop: 2, fontFamily: 'var(--font-data)' }}>{item.data.sector}</div>
                  </div>
                  <RatingBadge r={item.data.rating} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {([{ label: 'Price', value: item.data.price }, { label: 'Mkt Cap', value: item.data.mcap }, { label: 'Revenue', value: item.data.revenue }, { label: 'Profit', value: item.data.profit }, { label: 'P/E', value: `${fmt(item.data.pe)}×` }, { label: 'ROE', value: `${fmt(item.data.roe)}%` }]).map(kv => (
                    <div key={kv.label}>
                      <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 3 }}>{kv.label}</div>
                      <div style={{ fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-data)', fontWeight: 500 }}>{kv.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>

        {/* Quick radar — shown only when not in compare mode */}
        {!comparePhase && (
          <>
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '20px' }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)', marginBottom: 6 }}>Quality Radar</div>
              <div style={{ display: 'flex', gap: 14, marginBottom: 12 }}>
                {[{ sym: secA, color: A_COLOR }, { sym: secB, color: B_COLOR }].map(item => (
                  <div key={item.sym} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <div style={{ width: 10, height: 4, background: item.color, borderRadius: 99 }} />
                    <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{item.sym}</span>
                  </div>
                ))}
              </div>
              <div style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="var(--border)" />
                    <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} />
                    <Radar name={secA} dataKey="A" stroke={A_COLOR} fill={A_COLOR} fillOpacity={0.15} strokeWidth={2} />
                    <Radar name={secB} dataKey="B" stroke={B_COLOR} fill={B_COLOR} fillOpacity={0.15} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div style={{ textAlign: 'center', padding: '0 0 4px' }}>
              <button
                onClick={startCompare} disabled={sameSelected}
                style={{ fontSize: 13, color: 'var(--c-dsp)', background: 'rgba(124,106,247,0.08)', border: '1px dashed rgba(124,106,247,0.4)', borderRadius: 10, padding: '10px 24px', cursor: sameSelected ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-body)', transition: 'all 0.15s' }}
                onMouseEnter={e => { if (!sameSelected) e.currentTarget.style.background = 'rgba(124,106,247,0.14)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(124,106,247,0.08)' }}
              >
                Run full comparative analysis → Compare Both Securities
              </button>
            </div>
          </>
        )}

        {comparePhase === 'loading' && <CompareLoading secA={secA} secB={secB} />}
        {comparePhase === 'done' && <CompareResult a={a} b={b} secA={secA} secB={secB} onReset={() => setComparePhase(null)} />}

      </div>
    </div>
  )
}
