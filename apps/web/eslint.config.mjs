import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

/** EPIC-F000 — ESLint baseline (Next.js core-web-vitals). */
const eslintConfig = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    rules: {
      // The existing client components intentionally hydrate browser-only state in effects.
      "react-hooks/set-state-in-effect": "off",
      // The legacy UI contains stable callback patterns that the compiler rule rejects.
      "react-hooks/immutability": "off",
    },
  },
];

export default eslintConfig;
