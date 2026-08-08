#!/usr/bin/env node
/**
 * EPIC-010 / GA-003 — run production build with @next/bundle-analyzer enabled.
 */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const env = { ...process.env, ANALYZE: "true" };

const result = spawnSync("npx", ["next", "build"], {
  cwd: webRoot,
  env,
  stdio: "inherit",
  shell: true,
});

process.exit(result.status ?? 1);
