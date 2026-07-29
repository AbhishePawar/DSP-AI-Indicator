/**
 * P8.0 — Operations / observability / DR smoke (docs + configs + scripts).
 */
import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import {
  API_CONTRACT_TARGET,
  BACKEND_PLATFORM_TARGET,
  FRONTEND_FOUNDATION_EPIC,
  FRONTEND_FOUNDATION_VERSION,
} from "@/foundation/version";

const repoRoot = join(__dirname, "..", "..", "..", "..");

describe("P8.0 operations engineering", () => {
  it("aligns foundation to P8.0 / 2.0.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P8.0");
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@2.0.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0");
  });

  it("ships operations docs", () => {
    for (const name of [
      "OPERATIONS_DASHBOARD.md",
      "ALERTING_CONFIGURATION.md",
      "DISASTER_RECOVERY.md",
      "OPERATIONS_RUNBOOK.md",
      "LOGGING_REPORT.md",
      "OPERATIONAL_READINESS.md",
      "PRODUCTION_RISK_REGISTER.md",
      "P7_4_OPERATIONS_REPORT.md",
    ]) {
      const body = readFileSync(join(repoRoot, "docs", name), "utf8");
      expect(body.length).toBeGreaterThan(200);
    }
  });

  it("ships monitoring and alerting configs", () => {
    expect(existsSync(join(repoRoot, "docker", "prometheus", "alerts.yml"))).toBe(
      true,
    );
    expect(existsSync(join(repoRoot, "docker", "alertmanager.yml"))).toBe(true);
    expect(
      existsSync(
        join(repoRoot, "docker", "grafana", "dashboards", "dsp-operations.json"),
      ),
    ).toBe(true);
    const alerts = readFileSync(
      join(repoRoot, "docker", "prometheus", "alerts.yml"),
      "utf8",
    );
    expect(alerts).toContain("DspApiUnavailable");
    expect(alerts).toContain("DspDatabaseUnavailable");
  });

  it("ships certify_p7_4 and recovery validation", () => {
    for (const rel of [
      ["scripts", "ops", "certify_p7_4.py"],
      ["scripts", "ops", "validate_recovery.py"],
      ["scripts", "ops", "backup_postgres_incremental.sh"],
    ]) {
      expect(readFileSync(join(repoRoot, ...rel), "utf8").length).toBeGreaterThan(80);
    }
  });
});
