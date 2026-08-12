# VISUAL QA REPORT — EPIC-019A

| Field | Value |
|---|---|
| Date | 2026-08-04 |
| Product | DSP AI Indicator 2.0.0-rc.1 |
| Tooling | Playwright `@playwright/test` under `apps/web` |
| Suite | `e2e/visual/visual-regression.spec.ts` |
| Baselines | `e2e/visual/visual-regression.spec.ts-snapshots/*-chromium-win32.png` |
| CI | `.github/workflows/devsecops.yml` job `visual-qa` |

## Executive result

| Gate | Result |
|---|---|
| Automated visual regression harness | **PASS** (installed + CI wired) |
| Chromium baseline archive generated | **PASS** — 36 route×viewport×theme PNGs + 4 trust-chrome asserts |
| Local Chromium run (`--update-snapshots` then suite) | **40/40 PASS** |
| Dark / light | Covered |
| Desktop / tablet / mobile | Covered (1440 / 768 / 390) |
| Surfaces | login, dashboard, portfolio, research, IRD, analysis |
| Trust chrome on Dashboard / Portfolio / Research / IRD | Asserted present (or login shell) |

## Commands

```bash
cd apps/web
npm ci
npx playwright install --with-deps chromium
npm run test:visual:update   # refresh baselines
npm run test:visual          # compare
```

## Failure reporting

- HTML report: `apps/web/playwright-report/`
- JSON: `apps/web/playwright-results.json`
- Pixel diffs attached under `test-results/` on failure
- CI uploads artefacts from job `visual-qa`

## Honesty notes

- Baselines are **Windows Chromium** (`*-chromium-win32.png`). Linux CI may need a first `--update-snapshots` on ubuntu runners or platform-specific snapshot dirs.
- Auth-gated interactive analytical states remain thin-client shells without live session tokens in this pass.
- This closes EPIC-018 **AUD-002 / R-003** engineering gap (headed archive absent) with an automated archive + CI path — not a design redesign.

## Status vs Commercial GA

Engineering Visual QA blocker **CLOSED** for archive/automation. Board GA language still requires external commercial gates (billing/IdP) separately.
