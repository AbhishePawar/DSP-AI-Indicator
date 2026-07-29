/**
 * P7.0 — Production infrastructure client smoke (docs, versions, security headers config).
 */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import {
  API_CONTRACT_TARGET,
  BACKEND_PLATFORM_TARGET,
  FRONTEND_FOUNDATION_EPIC,
  FRONTEND_FOUNDATION_STATUS,
  FRONTEND_FOUNDATION_VERSION,
} from "@/foundation/version";

const repoRoot = join(__dirname, "..", "..", "..", "..");

describe("P7.0 production infrastructure", () => {
  it("aligns production versions", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P8.0");
    expect(FRONTEND_FOUNDATION_STATUS).toBe("production");
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@2.0.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0");
  });

  it("ships Caddy HTTPS/HSTS and production compose", () => {
    const caddy = readFileSync(join(repoRoot, "docker", "Caddyfile"), "utf8");
    expect(caddy).toMatch(/Strict-Transport-Security/);
    expect(caddy).toMatch(/reverse_proxy api:8000/);
    expect(caddy).toMatch(/encode gzip/);

    const compose = readFileSync(
      join(repoRoot, "docker", "docker-compose.production.yml"),
      "utf8",
    );
    expect(compose).toMatch(/caddy:/);
    expect(compose).toMatch(/postgres:/);
    expect(compose).toMatch(/prometheus:/);
    expect(compose).toMatch(/dsp-api:.*1\.7\.2|DSP_IMAGE_TAG:-1\.7\.2/);
  });

  it("documents P7 deployment and certification", () => {
    const deploy = readFileSync(
      join(repoRoot, "docs", "P7_PRODUCTION_DEPLOYMENT.md"),
      "utf8",
    );
    const cert = readFileSync(
      join(repoRoot, "docs", "P7_PRODUCTION_CERTIFICATION.md"),
      "utf8",
    );
    expect(deploy).toMatch(/Let's Encrypt|Caddy|HTTPS/i);
    expect(cert).toMatch(/GO WITH CONDITIONS|GO \/ NO-GO|Production Readiness/i);
  });

  it("exposes deploy/backup/rollback scripts", () => {
    for (const name of [
      "deploy_production.sh",
      "rollback_production.sh",
      "backup_database.sh",
      "restore_database.sh",
    ]) {
      const body = readFileSync(join(repoRoot, "scripts", name), "utf8");
      expect(body.length).toBeGreaterThan(80);
    }
  });
});
