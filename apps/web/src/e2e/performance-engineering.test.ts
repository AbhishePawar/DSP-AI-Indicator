/**
 * P8.0 — Performance engineering smoke (docs + scripts + artifacts).
 */
import { describe, expect, it } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

import {
  FRONTEND_FOUNDATION_EPIC,
  FRONTEND_FOUNDATION_VERSION,
  BACKEND_PLATFORM_TARGET,
  API_CONTRACT_TARGET,
} from "@/foundation/version";

const repoRoot = join(__dirname, "..", "..", "..", "..");

describe("P8.0 performance engineering", () => {
  it("aligns foundation to P8.0 / 2.0.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P8.0");
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@2.0.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0");
  });

  it("ships performance docs and artifacts", () => {
    for (const name of [
      "PERFORMANCE_BACKEND.md",
      "PERFORMANCE_FRONTEND.md",
      "DATABASE_PERFORMANCE.md",
      "P7_3_PERFORMANCE_REPORT.md",
    ]) {
      const body = readFileSync(join(repoRoot, "docs", name), "utf8");
      expect(body.length).toBeGreaterThan(200);
    }
    for (const name of [
      "api_benchmark.json",
      "load_test_results.json",
      "memory_snapshot.json",
    ]) {
      expect(existsSync(join(repoRoot, "docs", "perf", name))).toBe(true);
    }
  });

  it("ships perf scripts and certify_p7_3", () => {
    for (const rel of [
      ["scripts", "perf", "benchmark_api.py"],
      ["scripts", "perf", "load_test.py"],
      ["scripts", "perf", "memory_snapshot.py"],
      ["scripts", "ops", "certify_p7_3.py"],
    ]) {
      expect(readFileSync(join(repoRoot, ...rel), "utf8").length).toBeGreaterThan(80);
    }
  });
});
