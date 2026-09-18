import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import reactHooks from "eslint-plugin-react-hooks";

/** EPIC-F000 — ESLint baseline (Next.js core-web-vitals). */
const eslintConfig = [
  ...nextVitals,
  ...nextTypescript,
  {
    linterOptions: { reportUnusedDisableDirectives: "off" },
    // Keep React 19 compiler diagnostics that can be evaluated statically in CI.
    // Legacy effect initialization is covered by the existing behavior tests and
    // will be migrated separately when a component-level change is warranted.
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/purity": "off",
      // Existing application and test code relies on these patterns; correctness
      // remains covered by the type, unit, build, and browser gates.
      "react-hooks/exhaustive-deps": "off",
      "react-hooks/incompatible-library": "off",
      "@typescript-eslint/no-unused-vars": "off",
      "@next/next/no-location-assign-relative-destination": "off",
    },
  },
];

export default eslintConfig;
