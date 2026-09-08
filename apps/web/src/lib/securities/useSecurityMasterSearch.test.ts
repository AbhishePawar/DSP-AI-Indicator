import { describe, expect, it } from "vitest";

import {
  analysisHref,
  publicSearchMessage,
} from "@/lib/securities/useSecurityMasterSearch";

describe("security master search helpers", () => {
  it("builds an exact analysis identity URL", () => {
    expect(
      analysisHref({
        listing_id: "INE075A01022:XNSE",
        company_name: "Wipro Limited",
        trading_symbol: "WIPRO",
        exchange: "NSE",
        mic: "XNSE",
        isin: "INE075A01022",
        security_type: "common_equity",
        listing_status: "ACTIVE",
        eligibility_status: "ELIGIBLE",
        dsp_eligible: true,
        identity_ok: true,
      }),
    ).toBe("/analysis?symbol=WIPRO&exchange=NSE&isin=INE075A01022");
  });

  it("does not leak HTTP or infrastructure errors to ordinary users", () => {
    expect(publicSearchMessage("UNAVAILABLE", "HTTP 500", 500)).toBe(
      "Company search is temporarily unavailable.",
    );
    expect(publicSearchMessage("UNAVAILABLE", "Cloud Run timeout", 0)).toBe(
      "Company search is temporarily unavailable.",
    );
    expect(publicSearchMessage("NONE", "", 200)).toBe(
      "No supported security found.",
    );
    expect(publicSearchMessage("AMBIGUOUS", "", 200)).toBe(
      "Multiple securities found. Select the exchange.",
    );
    expect(publicSearchMessage("UNSUPPORTED", "x", 200)).toBe(
      "This security is not currently supported for DSP analysis.",
    );
  });
});
