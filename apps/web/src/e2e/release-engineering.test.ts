/**
 * P8.0 — Release engineering smoke (docs + scripts).
 */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import {
  FRONTEND_FOUNDATION_EPIC,
  FRONTEND_FOUNDATION_VERSION,
} from "@/foundation/version";

const repoRoot = join(__dirname, "..", "..", "..", "..");

describe("P8.0 release engineering", () => {
  it("aligns foundation to P8.0 / 2.0.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P8.0");
  });

  it("ships audit and engineering docs", () => {
    for (const name of [
      "REPOSITORY_AUDIT.md",
      "DEPENDENCY_AUDIT.md",
      "CODE_QUALITY_REPORT.md",
      "DOCUMENTATION_AUDIT.md",
      "VERSION_GOVERNANCE_REPORT.md",
      "ENGINEERING_STATUS.md",
    ]) {
      const body = readFileSync(join(repoRoot, "docs", name), "utf8");
      expect(body.length).toBeGreaterThan(200);
    }
  });

  it("ships release scripts and workflows", () => {
    for (const rel of [
      ["scripts", "release", "validate_release.py"],
      ["scripts", "release", "create_release_notes.py"],
      ["scripts", "ops", "certify_p7_2.py"],
      [".github", "workflows", "release-engineering.yml"],
      [".github", "workflows", "security.yml"],
    ]) {
      expect(readFileSync(join(repoRoot, ...rel), "utf8").length).toBeGreaterThan(80);
    }
  });
});
