import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTypescript,
  // Existing external-store/session hydration predates React Compiler. Keep its
  // migration diagnostics visible without treating them as compiler adoption.
  { files: ["**/*.{js,jsx,mjs,ts,tsx,mts,cts}"], rules: { "react-hooks/set-state-in-effect": "warn" } },
  globalIgnores([".next/**", "out/**", "build/**", "coverage/**", "next-env.d.ts"]),
]);
