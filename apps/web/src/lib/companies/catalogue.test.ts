import { describe, expect, it } from "vitest";

import {
  COMPANY_CATALOGUE,
  getCatalogueStats,
  getFeaturedCompanies,
  searchCatalogue,
} from "@/lib/companies/catalogue";

describe("company catalogue", () => {
  it("has 16 featured companies", () => {
    expect(getFeaturedCompanies()).toHaveLength(16);
  });

  it("searchCatalogue filters by name", () => {
    const results = searchCatalogue("apple");
    expect(results.length).toBe(1);
    expect(results[0]?.ticker).toBe("AAPL");
  });

  it("searchCatalogue filters by ticker", () => {
    const results = searchCatalogue("NVDA");
    expect(results.length).toBe(1);
    expect(results[0]?.name).toBe("NVIDIA");
  });

  it("searchCatalogue returns all for empty query", () => {
    expect(searchCatalogue("")).toHaveLength(COMPANY_CATALOGUE.length);
  });

  it("searchCatalogue returns empty for no match", () => {
    expect(searchCatalogue("zzzzz")).toHaveLength(0);
  });

  it("getCatalogueStats returns correct counts", () => {
    const stats = getCatalogueStats();
    expect(stats.total).toBe(16);
    expect(stats.researchAvailable).toBe(16);
    expect(stats.featured).toBe(16);
    expect(stats.recentlyAnalysed).toBe(0);
  });
});
