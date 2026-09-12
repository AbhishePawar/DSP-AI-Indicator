import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/** Python packages must never be imported from the web app. */
const FORBIDDEN_PYTHON_PACKAGES = [
  "dsp_platform",
  "valuation",
  "economic_moat",
  "management_quality",
  "financial_strength",
  "earnings_quality",
  "growth_quality",
  "business_quality_aggregator",
  "investment_recommendation",
  "investment_committee",
  "financial",
  "api_platform",
  "business_quality",
  "ai_committee",
  "recommendation",
];

/**
 * Local TypeScript investment-engine trees retired in EPIC-015.
 * Must not reappear under apps/web/src/lib.
 */
const FORBIDDEN_ENGINE_DIRS = [
  "moat",
  "valuation",
  "management",
  "earnings",
] as const;

/** Filename patterns that indicate browser-side investment scoring. */
const FORBIDDEN_FILENAME_RE =
  /(Engine|Scoring|Aggregation)\.tsx?$/i;

/** Allowlist dirs may contain presentation helpers only. */
const LIB_ALLOWLIST = new Set([
  "a11y",
  "admin-console",
  "advisor",
  "ai",
  "analysis",
  "api",
  "auth",
  "beta",
  "buffett-indicator",
  "institutional-rating",
  "companies",
  "company-analysis",
  "copilot",
  "dashboard",
  "institutional-dashboard",
  "intelligence",
  "launch",
  "market",
  "observability",
  "perf",
  "persistence",
  "portfolio",
  "portfolio-intelligence",
  "rc",
  "research",
  "research-workspace",
  "report-transparency",
  "explainability",
  "valuation-transparency",
  "screening",
  "settings",
  "shell",
  "saas",
  "enterprise",
  "commercial",
  "dashboards",
  "ops",
  "control-center",
  "trust",
]);

const CALC_SMELL_RE =
  /\b(computeFcff|WACC|terminalValue|weightedScore|METRIC_WEIGHTS|OverallMoat|OverallEarnings|OverallManagement)\b/;

function walk(dir: string, out: string[] = []): string[] {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name === ".next") continue;
      walk(full, out);
    } else if (/\.(ts|tsx|js|jsx)$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

describe("frontend architecture — thin client", () => {
  const webRoot = path.resolve(__dirname, "../..");
  const libRoot = path.resolve(__dirname);

  it("does not import backend Python packages", () => {
    const files = walk(webRoot);
    const violations: string[] = [];
    const importRe =
      /(?:from|import)\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)/g;

    for (const file of files) {
      const text = fs.readFileSync(file, "utf8");
      let match: RegExpExecArray | null;
      importRe.lastIndex = 0;
      while ((match = importRe.exec(text))) {
        const spec = match[1] || match[2] || "";
        const top = spec.split("/")[0];
        if (FORBIDDEN_PYTHON_PACKAGES.includes(top)) {
          violations.push(`${path.relative(webRoot, file)}: ${spec}`);
        }
      }
    }

    expect(violations).toEqual([]);
  });

  it("does not contain retired investment-engine directories under lib", () => {
    const present = FORBIDDEN_ENGINE_DIRS.filter((name) =>
      fs.existsSync(path.join(libRoot, name)),
    );
    expect(present).toEqual([]);
  });

  it("lib top-level dirs stay within presentation allowlist", () => {
    const dirs = fs
      .readdirSync(libRoot, { withFileTypes: true })
      .filter((e) => e.isDirectory())
      .map((e) => e.name)
      .filter((name) => !name.startsWith("."));
    const unexpected = dirs.filter((d) => !LIB_ALLOWLIST.has(d));
    expect(unexpected).toEqual([]);
  });

  it("forbids Engine/Scoring/Aggregation filenames under lib", () => {
    const files = walk(libRoot);
    const violations = files
      .filter((f) => FORBIDDEN_FILENAME_RE.test(path.basename(f)))
      .map((f) => path.relative(libRoot, f));
    expect(violations).toEqual([]);
  });

  it("forbids investment-calculation smell in lib sources", () => {
    const files = walk(libRoot).filter(
      (f) => !f.endsWith(".test.ts") && !f.endsWith(".test.tsx"),
    );
    const violations: string[] = [];
    for (const file of files) {
      const text = fs.readFileSync(file, "utf8");
      if (CALC_SMELL_RE.test(text)) {
        violations.push(path.relative(libRoot, file));
      }
    }
    expect(violations).toEqual([]);
  });
});
