/** Company catalogue — local static data for the directory. No API dependency. */

export type CompanyEntry = {
  name: string;
  ticker: string;
  exchange: string;
  sector: string;
  industry: string;
  marketCap: string;
  marketCapBucket: "large" | "mid" | "small";
  researchAvailable: boolean;
  featured: boolean;
  screening: {
    roe: number;
    roce: number;
    debtToEquity: number;
    revenueGrowth: number;
    profitGrowth: number;
    dividend: boolean;
    style: "growth" | "value" | "blend";
    quality: "high" | "medium";
  };
};

export const COMPANY_CATALOGUE: CompanyEntry[] = [
  { name: "Apple", ticker: "AAPL", exchange: "NASDAQ", sector: "Technology", industry: "Consumer Electronics", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 1.55, roce: 0.52, debtToEquity: 1.75, revenueGrowth: 0.06, profitGrowth: 0.08, dividend: true, style: "blend", quality: "high" } },
  { name: "Microsoft", ticker: "MSFT", exchange: "NASDAQ", sector: "Technology", industry: "Software", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.33, roce: 0.29, debtToEquity: 0.38, revenueGrowth: 0.15, profitGrowth: 0.19, dividend: true, style: "growth", quality: "high" } },
  { name: "Alphabet", ticker: "GOOGL", exchange: "NASDAQ", sector: "Technology", industry: "Internet Services", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.28, roce: 0.24, debtToEquity: 0.10, revenueGrowth: 0.13, profitGrowth: 0.17, dividend: false, style: "growth", quality: "high" } },
  { name: "Amazon", ticker: "AMZN", exchange: "NASDAQ", sector: "Consumer Discretionary", industry: "E-Commerce", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.18, roce: 0.14, debtToEquity: 0.52, revenueGrowth: 0.12, profitGrowth: 0.22, dividend: false, style: "growth", quality: "medium" } },
  { name: "Meta", ticker: "META", exchange: "NASDAQ", sector: "Technology", industry: "Social Media", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.30, roce: 0.27, debtToEquity: 0.14, revenueGrowth: 0.16, profitGrowth: 0.21, dividend: true, style: "growth", quality: "high" } },
  { name: "NVIDIA", ticker: "NVDA", exchange: "NASDAQ", sector: "Technology", industry: "Semiconductors", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.68, roce: 0.61, debtToEquity: 0.19, revenueGrowth: 0.55, profitGrowth: 0.72, dividend: true, style: "growth", quality: "high" } },
  { name: "Tesla", ticker: "TSLA", exchange: "NASDAQ", sector: "Consumer Discretionary", industry: "Electric Vehicles", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.21, roce: 0.18, debtToEquity: 0.12, revenueGrowth: 0.11, profitGrowth: 0.09, dividend: false, style: "growth", quality: "medium" } },
  { name: "Reliance Industries", ticker: "RELIANCE", exchange: "NSE", sector: "Energy", industry: "Conglomerate", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.10, roce: 0.12, debtToEquity: 0.48, revenueGrowth: 0.08, profitGrowth: 0.07, dividend: true, style: "value", quality: "medium" } },
  { name: "TCS", ticker: "TCS", exchange: "NSE", sector: "Technology", industry: "IT Services", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.46, roce: 0.58, debtToEquity: 0.08, revenueGrowth: 0.09, profitGrowth: 0.10, dividend: true, style: "blend", quality: "high" } },
  { name: "Infosys", ticker: "INFY", exchange: "NSE", sector: "Technology", industry: "IT Services", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.31, roce: 0.35, debtToEquity: 0.07, revenueGrowth: 0.08, profitGrowth: 0.09, dividend: true, style: "blend", quality: "high" } },
  { name: "HDFC Bank", ticker: "HDFCBANK", exchange: "NSE", sector: "Financials", industry: "Banking", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.17, roce: 0.11, debtToEquity: 6.10, revenueGrowth: 0.14, profitGrowth: 0.15, dividend: true, style: "blend", quality: "high" } },
  { name: "ICICI Bank", ticker: "ICICIBANK", exchange: "NSE", sector: "Financials", industry: "Banking", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.18, roce: 0.12, debtToEquity: 5.90, revenueGrowth: 0.16, profitGrowth: 0.18, dividend: true, style: "growth", quality: "high" } },
  { name: "Asian Paints", ticker: "ASIANPAINT", exchange: "NSE", sector: "Materials", industry: "Paints", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.24, roce: 0.29, debtToEquity: 0.18, revenueGrowth: 0.11, profitGrowth: 0.12, dividend: true, style: "blend", quality: "high" } },
  { name: "Titan", ticker: "TITAN", exchange: "NSE", sector: "Consumer Discretionary", industry: "Jewellery & Watches", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.31, roce: 0.27, debtToEquity: 0.44, revenueGrowth: 0.18, profitGrowth: 0.20, dividend: true, style: "growth", quality: "high" } },
  { name: "Nestle India", ticker: "NESTLEIND", exchange: "NSE", sector: "Consumer Staples", industry: "FMCG", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.79, roce: 0.66, debtToEquity: 0.24, revenueGrowth: 0.10, profitGrowth: 0.11, dividend: true, style: "blend", quality: "high" } },
  { name: "HUL", ticker: "HINDUNILVR", exchange: "NSE", sector: "Consumer Staples", industry: "FMCG", marketCap: "Large Cap", marketCapBucket: "large", researchAvailable: true, featured: true, screening: { roe: 0.21, roce: 0.30, debtToEquity: 0.04, revenueGrowth: 0.09, profitGrowth: 0.08, dividend: true, style: "value", quality: "high" } },
];

export function searchCatalogue(query: string): CompanyEntry[] {
  const q = query.trim().toLowerCase();
  if (!q) return COMPANY_CATALOGUE;
  return COMPANY_CATALOGUE.filter(
    (c) =>
      c.name.toLowerCase().includes(q) ||
      c.ticker.toLowerCase().includes(q),
  );
}

export function getFeaturedCompanies(): CompanyEntry[] {
  return COMPANY_CATALOGUE.filter((c) => c.featured);
}

export function getCatalogueStats() {
  return {
    total: COMPANY_CATALOGUE.length,
    researchAvailable: COMPANY_CATALOGUE.filter((c) => c.researchAvailable).length,
    featured: COMPANY_CATALOGUE.filter((c) => c.featured).length,
    recentlyAnalysed: 0,
  };
}
