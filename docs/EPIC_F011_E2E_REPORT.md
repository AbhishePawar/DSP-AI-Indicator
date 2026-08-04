# EPIC-F011 — E2E Coverage Report

## Test Coverage

| Journey | Automated | Notes |
|---|---|---|
| Authentication & RBAC | Yes | Guards, nav filters, login form |
| Dashboard | Yes | Widget registry + route |
| Company Analysis | Yes | Section registry + analyse client |
| Portfolio | Yes | Protected route + empty honesty |
| Research | Yes | Sections + diff unavailable |
| Admin | Yes | A010 client + overview UI |
| Settings | Yes | About/version UI |
| Navigation & routing | Yes | Shell nav + breadcrumbs |
| API integration | Yes | `api` / `adminApi` / `rbacAuthApi` |
| Error handling | Yes | `ApiClientError` |
| Loading / empty | Yes | `resolveListState` |
| Responsive regression | Yes | F010 catalogues |
| Accessibility regression | Yes | Appearance datasets |
| Cross-browser baseline | Yes | URLSearchParams / AbortController / storage |
| Performance smoke | Yes | Critical module import budget |

Command:

```bash
cd apps/web && npm run test:e2e
```

## Issues Fixed

1. **jsdom `matchMedia` missing** — polyfilled in `vitest.setup.ts` so responsive hooks do not throw in CI (production-critical test reliability).
2. **jsdom `ResizeObserver` missing** — polyfilled so Radix-backed login controls render in journey tests.

## Files Updated / Created

- `apps/web/src/e2e/*`
- `apps/web/vitest.setup.ts`
- `apps/web/package.json` (`test:e2e`)
- Foundation **0.12.0** + docs

## Remaining Issues

1. Full Playwright/Cypress browser matrix not installed (manual Chrome/Edge/Firefox/Safari still recommended before F012 cut).
2. Full axe CI gate still pending (F010 carry-over).
3. Legacy `@/components/ui` surfaces outside institutional shell not in E2E scope.

## Final

**PASS**
