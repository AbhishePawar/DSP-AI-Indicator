# Release Notes — Web 1.0.0

**Epic:** EPIC-F012 — Frontend Production Release  
**Date:** 2026-07-28  
**Promoted from:** Foundation **0.12.0** (F011 E2E) / host channel **3.0.0-rc1**  
**Frontend:** **v1.0.0** · Foundation **F012** `production_release`  
**Backend:** `dsp_platform@1.0.0` (frozen) · API **`v1.0.0-rc1`** (frozen)

## Highlights

- First **aligned** stable public web release: package, foundation, env, and manifest all **1.0.0**
- Institutional workspaces shipped under F002–F009: Dashboard, Analysis, Portfolio, Research, Admin, Settings
- F010 responsive & accessibility gate retained
- F011 end-to-end journey suite retained (`npm run test:e2e`)
- Production logger: `debug` / `info` suppressed when `NODE_ENV === "production"`
- CSP enforced; production browser source maps disabled; `poweredByHeader` off; standalone output

## Foundation trail (F000–F012)

| Epic | Version | Focus |
|---|---|---|
| F000 | — | Architecture freeze |
| F001 | 0.2.x | Design system |
| F002–F009 | 0.3–0.10 | Workspaces (Dashboard → Settings) |
| F010 | 0.11.0 | Responsive / a11y |
| F011 | 0.12.0 | E2E testing |
| **F012** | **1.0.0** | **Production release** |

## Trust

No changes to Decision Engine, Research Mode semantics, KG, Copilot generation, Portfolio calculations, Reports, Valuation engines, Compliance unlocks, or API contracts. Thin client only — presentation over frozen `/api/v1`.

## Quality gates

| Gate | Result |
|------|--------|
| Critical bugs | PASS (release-only; no new product code paths) |
| Regression | PASS (foundation + E2E suites) |
| Accessibility | PASS (F010 retained) |
| Performance | PASS (F011 smoke + production build flags) |
| Security | PASS (headers + no debug console in prod) |
| Dependency audit | Reviewed — 3 high transitive (Next/postcss/sharp); force-fix rejected (breaks Next). Track Next upgrade. |

## Known limitations

- Default API URL remains local (`127.0.0.1:8000`) unless `NEXT_PUBLIC_API_BASE_URL` is set for deploy
- Some admin/research feeds may show **Data unavailable.** when backend optional modules are offline — intentional honesty
- External telemetry exporter not wired (logger buffer only)
- `/profile` remains freeze-map identity surface; primary prefs live under `/settings`

## Next

**Frontend Production Certification**
