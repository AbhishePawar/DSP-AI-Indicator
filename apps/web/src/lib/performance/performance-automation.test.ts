/**
 * EPIC-010 / GA-003 — Performance automation (code-splitting / lazy / skeletons).
 * Quality-only source contracts — no UX redesign, no engine changes.
 */
import { describe, expect, it } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";

import {
  BUNDLE_BUDGETS,
  FLAGSHIP_DYNAMIC_ROUTES,
  LAZY_WORKSPACE_MODULES,
  PERFORMANCE_AUTOMATION_SCOPE,
} from "./performanceGates";

const webRoot = path.resolve(__dirname, "../../..");

function readSrc(rel: string): string {
  const abs = path.join(webRoot, rel);
  expect(existsSync(abs), `missing ${rel}`).toBe(true);
  return readFileSync(abs, "utf8");
}

describe("EPIC-010 / GA-003 performance automation catalogue", () => {
  it("documents automated performance coverage scope", () => {
    expect([...PERFORMANCE_AUTOMATION_SCOPE]).toEqual([
      "route-dynamic-imports",
      "workspace-react-lazy",
      "skeleton-loading-fallbacks",
      "bundle-analyzer-script",
      "lighthouse-ci-config",
      "static-js-size-budget",
    ]);
  });

  it("publishes advisory and hard static JS budgets", () => {
    expect(BUNDLE_BUDGETS.documentedSharedFirstLoadKb).toBe(103);
    expect(BUNDLE_BUDGETS.hardMaxTotalStaticJsBytes).toBeGreaterThan(
      BUNDLE_BUDGETS.advisoryTotalStaticJsBytes,
    );
  });
});

describe("EPIC-010 flagship route code splitting", () => {
  it.each([...FLAGSHIP_DYNAMIC_ROUTES])(
    "%s uses next/dynamic with loading skeleton",
    (rel) => {
      const src = readSrc(rel);
      expect(src).toMatch(/next\/dynamic/);
      expect(src).toMatch(/dynamic\s*\(/);
      expect(src).toMatch(/loading\s*:/);
      expect(src).toMatch(/Skeleton|WorkspaceSkeleton/);
    },
  );
});

describe("EPIC-010 workspace React.lazy modules", () => {
  it.each([...LAZY_WORKSPACE_MODULES])(
    "%s uses React.lazy dynamic import",
    (rel) => {
      const src = readSrc(rel);
      expect(src).toMatch(/\blazy\s*\(/);
      expect(src).toMatch(/import\s*\(/);
      expect(src).toMatch(/Suspense|WorkspaceSkeleton|Skeleton/);
    },
  );
});

describe("EPIC-010 analyzer + lighthouse tooling present", () => {
  it("wires ANALYZE-capable next.config and lighthouse config", () => {
    const nextConfig = readSrc("next.config.ts");
    expect(nextConfig).toMatch(/@next\/bundle-analyzer/);
    expect(nextConfig).toMatch(/ANALYZE/);
    expect(existsSync(path.join(webRoot, "lighthouserc.cjs"))).toBe(true);
    expect(existsSync(path.join(webRoot, "scripts/check-bundle-budgets.mjs"))).toBe(
      true,
    );
  });
});
