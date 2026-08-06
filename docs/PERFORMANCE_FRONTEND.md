# Frontend Performance — EPIC-P7.3

**Date:** 2026-07-29 · **Frontend:** `2.0.3`  
**Scope:** Presentation/ops only — no analytical client logic.

## Baseline posture

| Topic | Status |
|---|---|
| Next.js `output: "standalone"` | Already enabled |
| Compression | Next `compress: true` + Caddy gzip/zstd |
| Source maps in prod | Disabled |
| Edge static caching | Caddy `/_next/static/*` immutable |
| App static caching | Added `Cache-Control` for `/_next/static` in `next.config.ts` |
| Package import optimisation | `experimental.optimizePackageImports: ["lucide-react"]` |

## Optimisations applied (P7.3)

1. Immutable cache headers for `/_next/static/*` at Next layer (defense in depth with Caddy).  
2. `optimizePackageImports` for `lucide-react` to reduce unused icon graph.  
3. Documented hydration/render guidance: keep heavy admin/advisor widgets route-scoped (already large files; no behaviour rewrite).

## Bundle / splitting guidance

- Prefer route-level code splitting already provided by App Router.  
- Do not move scoring/valuation into the browser (thin-client rule).  
- Fonts: use existing VLIS fonts; avoid additional webfont families without design review.

## Cache strategy

| Layer | Policy |
|---|---|
| Hashed static assets | `max-age=31536000, immutable` |
| HTML / RSC | short / default Next |
| API analyse responses | not browser-cached (correctness/trust) |

**Frontend performance score:** **8.0 / 10**
