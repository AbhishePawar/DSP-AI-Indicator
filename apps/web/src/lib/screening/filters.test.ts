import { describe, expect, it } from "vitest";

import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import {
  DEFAULT_SCREENING_FILTERS,
  applyScreeningFilters,
  applyScreeningPreset,
  getFiltersAppliedCount,
  getUniqueExchanges,
  getUniqueSectors,
} from "@/lib/screening/filters";

describe("screening filters", () => {
  it("returns all companies for default filters", () => {
    expect(
      applyScreeningFilters(COMPANY_CATALOGUE, DEFAULT_SCREENING_FILTERS),
    ).toHaveLength(COMPANY_CATALOGUE.length);
  });

  it("filters by search query", () => {
    const results = applyScreeningFilters(COMPANY_CATALOGUE, {
      ...DEFAULT_SCREENING_FILTERS,
      query: "msft",
    });
    expect(results).toHaveLength(1);
    expect(results[0]?.ticker).toBe("MSFT");
  });

  it("filters by numeric thresholds", () => {
    const results = applyScreeningFilters(COMPANY_CATALOGUE, {
      ...DEFAULT_SCREENING_FILTERS,
      minRoe: "40",
      maxDebtToEquity: "0.3",
    });
    expect(results.some((company) => company.ticker === "NVDA")).toBe(true);
    expect(results.some((company) => company.ticker === "AAPL")).toBe(false);
  });

  it("filters by sector and exchange", () => {
    const results = applyScreeningFilters(COMPANY_CATALOGUE, {
      ...DEFAULT_SCREENING_FILTERS,
      sector: "Financials",
      exchange: "NSE",
    });
    expect(results.map((company) => company.ticker)).toEqual([
      "HDFCBANK",
      "ICICIBANK",
    ]);
  });

  it("applies growth preset", () => {
    const preset = applyScreeningPreset("growth");
    expect(preset.minRevenueGrowth).toBe("12");
    expect(preset.style).toBe("growth");
  });

  it("counts applied filters", () => {
    expect(
      getFiltersAppliedCount({
        ...DEFAULT_SCREENING_FILTERS,
        query: "tech",
        sector: "Technology",
        dividend: "yes",
      }),
    ).toBe(3);
  });

  it("collects unique sectors and exchanges", () => {
    expect(getUniqueSectors(COMPANY_CATALOGUE)).toContain("Technology");
    expect(getUniqueExchanges(COMPANY_CATALOGUE)).toEqual(["NASDAQ", "NSE"]);
  });
});
