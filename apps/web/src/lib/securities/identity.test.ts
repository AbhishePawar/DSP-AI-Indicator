import { describe, expect, it } from "vitest";

import {
  analysisPath,
  hasExactListingIdentity,
  identityFromSearchParams,
} from "./identity";

describe("security identity helpers", () => {
  it("builds analysis URL with ISIN and MIC", () => {
    expect(
      analysisPath({
        ticker: "INFY",
        exchange: "NSE",
        isin: "INE009A01021",
        mic: "XNSE",
      }),
    ).toBe(
      "/analysis?symbol=INFY&exchange=NSE&isin=INE009A01021&mic=XNSE",
    );
  });

  it("requires exact listing identity", () => {
    expect(
      hasExactListingIdentity({
        ticker: "INFY",
        exchange: "",
        isin: "INE009A01021",
        mic: "XNSE",
      }),
    ).toBe(false);
    expect(
      hasExactListingIdentity({
        ticker: "INFY",
        exchange: "NSE",
        isin: "INE009A01021",
        mic: "XNSE",
      }),
    ).toBe(true);
  });

  it("reads identity from search params", () => {
    const params = new URLSearchParams(
      "symbol=INFY&exchange=NSE&isin=INE009A01021&mic=XNSE",
    );
    expect(identityFromSearchParams(params)).toEqual({
      ticker: "INFY",
      exchange: "NSE",
      isin: "INE009A01021",
      mic: "XNSE",
    });
  });

  it("P1-09 fixture workspace URL includes ticker and exchange", () => {
    expect(analysisPath({ ticker: "DSPFIX", exchange: "NYSE" })).toBe(
      "/analysis?symbol=DSPFIX&exchange=NYSE",
    );
    const tickerOnly = identityFromSearchParams(
      new URLSearchParams("symbol=DSPFIX"),
    );
    expect(tickerOnly.exchange).toBe("");
    expect(hasExactListingIdentity(tickerOnly)).toBe(false);
  });
});
