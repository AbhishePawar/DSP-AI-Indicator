import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import reactHooks from "eslint-plugin-react-hooks";

/** EPIC-F000 — ESLint baseline (Next.js core-web-vitals). */
const eslintConfig = [
  ...nextVitals,
  ...nextTypescript,
  {
    // React 19 compiler diagnostics are retained as warnings while legacy effect
    // initialization is migrated incrementally without changing runtime behavior.
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/purity": "warn",
    },
  },
];

export default eslintConfig;
