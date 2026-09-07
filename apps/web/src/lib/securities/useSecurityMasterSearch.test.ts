import { describe, expect, it } from "vitest";

import { analysisHref } from "@/lib/securities/useSecurityMasterSearch";

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
    ).toBe(
      "/analysis?symbol=WIPRO&exchange=NSE&isin=INE075A01022",
    );
  });
});
