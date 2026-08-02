/** @vitest-environment jsdom */
import { describe, expect, it } from "vitest";

import { asRiSectionId, asRiWindow, displayMetric } from "./index";

describe("research intelligence presentation helpers", () => {
  it("defaults section and window safely", () => {
    expect(asRiSectionId(null)).toBe("performance");
    expect(asRiSectionId("timeline")).toBe("timeline");
    expect(asRiWindow(null)).toBe(12);
    expect(asRiWindow("24")).toBe(24);
    expect(asRiWindow("99")).toBe(12);
  });

  it("never fabricates missing metrics", () => {
    expect(displayMetric(null)).toBe("Data unavailable.");
    expect(displayMetric(undefined)).toBe("Data unavailable.");
    expect(displayMetric("Data unavailable.")).toBe("Data unavailable.");
    expect(displayMetric(0.5)).toBe("50.0%");
  });
});
