import type { CompanyEntry } from "@/lib/companies/catalogue";

export type ScreeningFilters = {
  query: string;
  minRoe: string;
  minRoce: string;
  maxDebtToEquity: string;
  minRevenueGrowth: string;
  minProfitGrowth: string;
  marketCap: "all" | "large" | "mid" | "small";
  sector: string;
  exchange: string;
  researchAvailable: "all" | "yes" | "no";
  dividend: "all" | "yes" | "no";
  style: "all" | "growth" | "value" | "blend";
};

export type ScreeningPreset =
  | "high-quality"
  | "low-debt"
  | "large-cap"
  | "technology"
  | "financial-services"
  | "consumer"
  | "dividend"
  | "growth"
  | "value";

export const DEFAULT_SCREENING_FILTERS: ScreeningFilters = {
  query: "",
  minRoe: "",
  minRoce: "",
  maxDebtToEquity: "",
  minRevenueGrowth: "",
  minProfitGrowth: "",
  marketCap: "all",
  sector: "all",
  exchange: "all",
  researchAvailable: "all",
  dividend: "all",
  style: "all",
};

export const SCREENING_PRESETS: Array<{
  id: ScreeningPreset;
  label: string;
}> = [
  { id: "high-quality", label: "High Quality" },
  { id: "low-debt", label: "Low Debt" },
  { id: "large-cap", label: "Large Cap" },
  { id: "technology", label: "Technology" },
  { id: "financial-services", label: "Financial Services" },
  { id: "consumer", label: "Consumer" },
  { id: "dividend", label: "Dividend" },
  { id: "growth", label: "Growth" },
  { id: "value", label: "Value" },
];

function toNumber(value: string): number | null {
  if (value.trim() === "") return null;
  const next = Number(value);
  return Number.isFinite(next) ? next : null;
}

function matchesText(company: CompanyEntry, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return (
    company.name.toLowerCase().includes(q) ||
    company.ticker.toLowerCase().includes(q)
  );
}

export function applyScreeningFilters(
  companies: CompanyEntry[],
  filters: ScreeningFilters,
): CompanyEntry[] {
  const minRoe = toNumber(filters.minRoe);
  const minRoce = toNumber(filters.minRoce);
  const maxDebtToEquity = toNumber(filters.maxDebtToEquity);
  const minRevenueGrowth = toNumber(filters.minRevenueGrowth);
  const minProfitGrowth = toNumber(filters.minProfitGrowth);

  return companies.filter((company) => {
    if (!matchesText(company, filters.query)) return false;
    if (minRoe !== null && company.screening.roe < minRoe / 100) return false;
    if (minRoce !== null && company.screening.roce < minRoce / 100) return false;
    if (
      maxDebtToEquity !== null &&
      company.screening.debtToEquity > maxDebtToEquity
    ) {
      return false;
    }
    if (
      minRevenueGrowth !== null &&
      company.screening.revenueGrowth < minRevenueGrowth / 100
    ) {
      return false;
    }
    if (
      minProfitGrowth !== null &&
      company.screening.profitGrowth < minProfitGrowth / 100
    ) {
      return false;
    }
    if (
      filters.marketCap !== "all" &&
      company.marketCapBucket !== filters.marketCap
    ) {
      return false;
    }
    if (filters.sector !== "all" && company.sector !== filters.sector) return false;
    if (filters.exchange !== "all" && company.exchange !== filters.exchange) {
      return false;
    }
    if (
      filters.researchAvailable === "yes" &&
      company.researchAvailable !== true
    ) {
      return false;
    }
    if (
      filters.researchAvailable === "no" &&
      company.researchAvailable !== false
    ) {
      return false;
    }
    if (filters.dividend === "yes" && !company.screening.dividend) return false;
    if (filters.dividend === "no" && company.screening.dividend) return false;
    if (filters.style !== "all" && company.screening.style !== filters.style) {
      return false;
    }
    return true;
  });
}

export function getFiltersAppliedCount(filters: ScreeningFilters): number {
  return Object.entries(filters).reduce((count, [key, value]) => {
    if (key === "query") return value ? count + 1 : count;
    if (value === "" || value === "all") return count;
    return count + 1;
  }, 0);
}

export function getUniqueSectors(companies: CompanyEntry[]): string[] {
  return [...new Set(companies.map((company) => company.sector))].sort();
}

export function getUniqueExchanges(companies: CompanyEntry[]): string[] {
  return [...new Set(companies.map((company) => company.exchange))].sort();
}

export function applyScreeningPreset(
  preset: ScreeningPreset,
  current: ScreeningFilters = DEFAULT_SCREENING_FILTERS,
): ScreeningFilters {
  const next = { ...current };
  switch (preset) {
    case "high-quality":
      return { ...next, minRoe: "20", minRoce: "20", researchAvailable: "yes" };
    case "low-debt":
      return { ...next, maxDebtToEquity: "0.5" };
    case "large-cap":
      return { ...next, marketCap: "large" };
    case "technology":
      return { ...next, sector: "Technology" };
    case "financial-services":
      return { ...next, sector: "Financials" };
    case "consumer":
      return { ...next, sector: "Consumer Staples" };
    case "dividend":
      return { ...next, dividend: "yes" };
    case "growth":
      return {
        ...next,
        minRevenueGrowth: "12",
        minProfitGrowth: "12",
        style: "growth",
      };
    case "value":
      return { ...next, style: "value", maxDebtToEquity: "0.6" };
  }
}
