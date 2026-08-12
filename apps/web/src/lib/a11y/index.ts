/** EPIC-F010 / EPIC-010 GA-003 — Accessibility & responsive validation helpers.
 *
 * EPIC-019A — do NOT re-export runAxe / vitest-axe from this barrel.
 * Production workspaces import useCollapsePanelsBelowLg from here; pulling
 * vitest-axe into the Next client graph causes Module not found: 'module'.
 * Tests import runAxe from `@/lib/a11y/runAxe` directly.
 */

export {
  CRITICAL_ROUTES,
  RESPONSIVE_VIEWPORTS,
  useCollapsePanelsBelowLg,
} from "./responsiveWorkspace";

export { A11Y_AUTOMATION_SCOPE } from "./scope";
