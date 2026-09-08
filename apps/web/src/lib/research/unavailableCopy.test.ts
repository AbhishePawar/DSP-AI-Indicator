import { describe, expect, it } from "vitest";

import {
  VALUATION_UNAVAILABLE_COPY,
  formatAnalyseUnavailableMessage,
} from "./unavailableCopy";

describe("unavailableCopy", () => {
  it("maps Data unavailable to the verified-data empty state", () => {
    expect(formatAnalyseUnavailableMessage("Data unavailable.")).toBe(
      VALUATION_UNAVAILABLE_COPY,
    );
  });

  it("leaves unrelated messages unchanged", () => {
    expect(formatAnalyseUnavailableMessage("Permission denied")).toBe(
      "Permission denied",
    );
  });
});
