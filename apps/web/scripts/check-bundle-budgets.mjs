#!/usr/bin/env node
/**
 * EPIC-010 / GA-003 — advisory / hard static JS size budget check.
 *
 * Usage (after `npm run build`):
 *   npm run perf:budget
 *
 * Exits 0 when `.next` is missing (documents skip) unless --require-build.
 * Fails only when total static JS under .next/static exceeds hardMax.
 */

import { existsSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(__dirname, "..");
const nextStatic = path.join(webRoot, ".next", "static");

/** Keep in sync with src/lib/performance/performanceGates.ts */
const BUDGETS = {
  advisoryTotalStaticJsBytes: 3_500_000,
  hardMaxTotalStaticJsBytes: 6_000_000,
};

const requireBuild = process.argv.includes("--require-build");

function walkJs(dir, acc = []) {
  if (!existsSync(dir)) return acc;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walkJs(full, acc);
    else if (entry.isFile() && entry.name.endsWith(".js")) acc.push(full);
  }
  return acc;
}

if (!existsSync(nextStatic)) {
  const msg =
    "[perf:budget] No .next/static found — run `npm run build` first. Skipping budget gate.";
  if (requireBuild) {
    console.error(msg);
    process.exit(1);
  }
  console.warn(msg);
  process.exit(0);
}

const files = walkJs(nextStatic);
const total = files.reduce((sum, f) => sum + statSync(f).size, 0);
const kb = (total / 1024).toFixed(1);

console.log(
  `[perf:budget] static JS files=${files.length} total=${kb} KiB (advisory=${(BUDGETS.advisoryTotalStaticJsBytes / 1024).toFixed(0)} KiB, hard=${(BUDGETS.hardMaxTotalStaticJsBytes / 1024).toFixed(0)} KiB)`,
);

if (total > BUDGETS.hardMaxTotalStaticJsBytes) {
  console.error(
    `[perf:budget] FAIL — exceeded hardMaxTotalStaticJsBytes (${BUDGETS.hardMaxTotalStaticJsBytes}).`,
  );
  process.exit(1);
}

if (total > BUDGETS.advisoryTotalStaticJsBytes) {
  console.warn(
    "[perf:budget] WARN — above advisory budget; review ANALYZE=true report before Commercial GA.",
  );
} else {
  console.log("[perf:budget] PASS — within advisory + hard budgets.");
}

process.exit(0);
