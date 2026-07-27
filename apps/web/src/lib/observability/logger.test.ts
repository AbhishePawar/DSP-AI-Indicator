import { describe, expect, it, beforeEach } from "vitest";

import { logger } from "./logger";

describe("logger", () => {
  beforeEach(() => {
    logger._resetForTests();
  });

  it("records info/warn/error/debug entries", () => {
    logger.info("boot");
    logger.warn("slow");
    logger.error("failed");
    logger.debug("trace");
    const logs = logger.getRecentLogs();
    expect(logs).toHaveLength(4);
    expect(logs.map((l) => l.level)).toEqual(["debug", "error", "warn", "info"]);
  });

  it("records client errors for diagnostics", () => {
    logger.recordClientError(new Error("boom"), "route-error", {
      digest: "abc",
    });
    const errors = logger.getSessionErrors();
    expect(errors).toHaveLength(1);
    expect(errors[0]?.message).toBe("boom");
    expect(errors[0]?.source).toBe("route-error");
    expect(errors[0]?.digest).toBe("abc");
  });

  it("caps error buffer size", () => {
    for (let i = 0; i < 60; i += 1) {
      logger.recordClientError(`e-${i}`, "unknown");
    }
    expect(logger.getSessionErrors(100).length).toBeLessThanOrEqual(50);
  });
});
