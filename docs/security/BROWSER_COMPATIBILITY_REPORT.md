# BROWSER COMPATIBILITY REPORT — EPIC-019A

| Field | Value |
|---|---|
| Date | 2026-08-04 |
| Host | Windows 10.0.26200 |
| Suite | `apps/web/e2e/browser/smoke.spec.ts` |
| Prior | `docs/releases/BROWSER_CERTIFICATION.md` (EPIC-010) |

## Results

| Browser | Method | Paths | Result |
|---|---|---|---|
| Chromium (Playwright) | Engine smoke | `/`, `/login`, `/dashboard`, `/portfolio`, `/research` | **15/15 project PASS** (5 paths) |
| Firefox (Playwright Gecko) | Engine smoke | same | **PASS** (5/5) |
| WebKit (Playwright) | Engine smoke on Windows | same | **PASS** (5/5) — **not** macOS Safari.app |
| Microsoft Edge (system channel) | Playwright `msedge` against standalone server | `/`, `/login`, `/dashboard`, `/portfolio`, `/research` | **PASS** (5/5) |
| System Firefox (`C:\Program Files\Mozilla Firefox`) | Host install | — | **Not installed** (winget install blocked by approval gate) |
| Safari.app | macOS only | — | **External prerequisite** — use Playwright WebKit locally + physical Safari smoke on Mac |

**Aggregate Playwright browser smoke:** **20/20 PASS** (chromium + firefox + webkit + msedge).

## Genuine compatibility fixes applied

1. Stopped exporting `vitest-axe` / `runAxe` from `@/lib/a11y` barrel — prevented Next client `Module not found: 'module'` on research/portfolio routes.
2. Button `variant="default"` → `"primary"` in company-comparison (type-safe DS variants) — unblocked production build.
3. `enterpriseClient` `ApiErrorBody` completeness for strict TypeScript production build.

No browser-specific CSS hacks or UI redesign.

## Remaining external / ops

| Item | Status |
|---|---|
| Physical Safari on macOS | **Operational Prerequisite** |
| System Firefox install on Windows | Optional — Playwright Firefox already evidences Gecko |
| Edge channel CI on Linux | Install Edge or rely on Chromium + Windows Edge binary |

## Status vs EPIC-018 R-004

Engineering browser smoke for Chromium/Firefox/WebKit **CLOSED** with evidence. Claiming “Safari.app physical PASS” remains **forbidden** without macOS run.
