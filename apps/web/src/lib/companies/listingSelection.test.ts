import { describe, expect, it } from "vitest";

import {
  exchangeScopedQueryKey,
  listingQueryKey,
  quoteCurrencyForExchange,
  selectedExchangeFromListing,
  shouldFetchIndianListing,
} from "@/lib/companies/listingSelection";

describe("quoteCurrencyForExchange", () => {
  it("maps NSE to INR", () => {
    expect(quoteCurrencyForExchange("NSE")).toBe("INR");
  });

  it("maps BSE to INR", () => {
    expect(quoteCurrencyForExchange("BSE")).toBe("INR");
    expect(quoteCurrencyForExchange("bse")).toBe("INR");
  });

  it("maps NASDAQ to USD", () => {
    expect(quoteCurrencyForExchange("NASDAQ")).toBe("USD");
  });
});

describe("Indian listing selection helper", () => {
  it("does not apply BSE-first to NASDAQ catalogue names", () => {
    expect(shouldFetchIndianListing("NASDAQ")).toBe(false);
    expect(
      selectedExchangeFromListing({
        catalogueExchange: "NASDAQ",
        listing: { status: "SELECTED", exchange: "BSE" },
      }),
    ).toBe("NASDAQ");
  });

  it("uses SELECTED listing exchange for Indian catalogue names", () => {
    expect(shouldFetchIndianListing("NSE")).toBe(true);
    expect(
      selectedExchangeFromListing({
        catalogueExchange: "NSE",
        listing: { status: "SELECTED", exchange: "BSE", isin: "INE467B01029" },
      }),
    ).toBe("BSE");
  });

  it("does not invent an exchange when listing is not SELECTED", () => {
    expect(
      selectedExchangeFromListing({
        catalogueExchange: "NSE",
        listing: { status: "AMBIGUOUS" },
      }),
    ).toBeUndefined();
  });

  it("keeps explicit NSE rather than substituting catalogue", () => {
    expect(
      selectedExchangeFromListing({
        catalogueExchange: "NSE",
        explicitExchange: "NSE",
        listing: { status: "SELECTED", exchange: "NSE" },
      }),
    ).toBe("NSE");
  });

  it("puts selected exchange in React Query keys", () => {
    expect(listingQueryKey("TCS")).toEqual(["listing-select", "TCS", ""]);
    expect(listingQueryKey("TCS", "NSE")).toEqual(["listing-select", "TCS", "NSE"]);
    expect(
      exchangeScopedQueryKey(["company-analysis", "market"], "TCS", "BSE"),
    ).toEqual(["company-analysis", "market", "TCS", "BSE"]);
  });
});
