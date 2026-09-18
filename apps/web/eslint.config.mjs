import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

/** EPIC-F000 — ESLint baseline (Next.js core-web-vitals). */
const eslintConfig = [...nextVitals, ...nextTypescript];

export default eslintConfig;
