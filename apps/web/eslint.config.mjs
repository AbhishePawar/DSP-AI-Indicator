import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

/**
 * EPIC-F000 — ESLint baseline (Next.js core-web-vitals).
 *
 * `eslint-config-next` 16 ships native flat-config exports, so we import
 * them directly instead of routing through `FlatCompat`. `FlatCompat` is
 * designed to adapt legacy `.eslintrc`-style shareable configs; wrapping an
 * already-flat plugin object (e.g. `eslint-plugin-react`) through it can
 * produce a circular reference and crash with
 * "TypeError: Converting circular structure to JSON".
 */
const eslintConfig = [...nextCoreWebVitals, ...nextTypescript];

export default eslintConfig;
