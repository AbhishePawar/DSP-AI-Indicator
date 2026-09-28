import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

/** Next.js 16 flat config. FlatCompat cannot load these shareable configs. */
const eslintConfig = [
  { ignores: [".next/**", "out/**", "build/**", "coverage/**", "playwright-report/**"] },
  ...nextCoreWebVitals,
  ...nextTypescript,
];

export default eslintConfig;
