# PERFORMANCE CERTIFICATION — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Programme | EPIC-010 / GA-003 — Accessibility & Performance Automation |
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| Branch | `cursor/p6-1-commercial-readiness` |
| Date | 2026-08-02 |
| Mode | Quality tooling + documentation only — **no** UX redesign; **no** backend/API/engine changes |
| Prior artefacts | `RC3_FINAL_CERTIFICATION_REPORT.md` · `BROWSER_CERTIFICATION.md` · Design System |
| Commercial performance decision | **PASS WITH CONDITIONS** (automation **established**) — **not** unrestricted Commercial public GA |

---

## 1. Executive Summary

Automated performance verification is now **established** for the thin-client Next.js app: bundle analyzer wiring, static JS size budget script, Vitest contracts for route-level `next/dynamic` + workspace `React.lazy` + skeleton fallbacks, and a production-ready Lighthouse CI config with documented LCP/CLS/INP advisory thresholds.

This epic **PASS** means tooling and contracts run and stay green — **not** that field Core Web Vitals are certified for public Commercial GA, or that Lighthouse scores were re-measured on a stable production host in this environment.

Aligns with RC3 **PASS WITH CONDITIONS** (~103 kB shared First Load JS reported; Lighthouse CI budgets previously unpublished).

---

## 2. Automation Added

| Asset | Role |
|---|---|
| `@next/bundle-analyzer` (devDependency) | Webpack analyzer when `ANALYZE=true` |
| `apps/web/next.config.ts` | `withBundleAnalyzer` wrapper (no behaviour change when ANALYZE unset) |
| `npm run analyze` → `scripts/run-analyze.mjs` | Production build + analyzer report |
| `apps/web/lighthouserc.cjs` | LHCI collect/assert config (Performance / A11y / Best Practices / SEO) |
| `npm run lighthouse:ci` | `npx @lhci/cli@0.14.0 autorun` (Chrome required) |
| `scripts/check-bundle-budgets.mjs` | Advisory + hard static `.next/static/**/*.js` budgets |
| `npm run perf:budget` | Runs budget script (skips if no build; CI uses `--require-build`) |
| `src/lib/performance/performanceGates.ts` | Catalogue + budget constants |
| `src/lib/performance/performance-automation.test.ts` | Code-splitting / lazy / tooling presence contracts |
| `npm run test:perf` / `test:quality` | Vitest performance automation |
| `.github/workflows/frontend.yml` | **Performance automation** + post-build **Bundle size budget** |

### Lighthouse approach (honest)

| Category | Assert mode | Baseline intent |
|---|---|---|
| Performance | `warn` ≥ 0.70 | Desktop collect; host/auth variance expected |
| Accessibility | `warn` ≥ 0.90 | Complements vitest-axe; includes contrast |
| Best Practices | `warn` ≥ 0.85 | CSP / HTTPS posture depends on deploy URL |
| SEO | `warn` ≥ 0.80 | Marketing/login primarily; app shell secondary |
| LCP | `warn` ≤ 4000 ms | Readiness documentation — not GA unlock |
| CLS | `warn` ≤ 0.15 | Skeletons / reserved space help; field TBD |
| INP | `warn` ≤ 300 ms | Advisory; needs interactive headed run |

Assertions are **warn** (not hard fail) so CI can adopt LHCI later without flaking on auth-gated routes. Commercial GA still needs a published run against a real URL.

---

## 3. Performance Results

### 3.1 Code splitting / lazy / skeletons (automated)

| Surface | Mechanism | Automation |
|---|---|---|
| `/analysis`, `/portfolio`, `/research`, institutional reports/dashboard, `/settings` | `next/dynamic` + `loading` skeleton | **PASS** (`test:perf`) |
| Portfolio Intelligence modules | `React.lazy` + dynamic `import()` | **PASS** |
| Research Workspace sections | `React.lazy` | **PASS** |
| Institutional Reports modules | `React.lazy` | **PASS** |
| Skeleton / polite loading | DS Skeleton `aria-hidden` + WorkspaceSkeleton fallbacks | Present (a11y + perf contracts) |

### 3.2 Bundle review (tooling + document findings)

| Finding | Severity | Notes |
|---|---|---|
| Shared First Load JS ~**103 kB** (RC3 production build) | Baseline | Documented in `BUNDLE_BUDGETS.documentedSharedFirstLoadKb` |
| `echarts` / `echarts-for-react` | Expected heavy | Kept behind dynamic/lazy workspaces — do **not** eagerly import on marketing shell |
| `lucide-react` | Mitigated | `optimizePackageImports: ["lucide-react"]` already in next.config |
| Duplicate UI stacks (`components/ds` vs `components/ui`) | Residual | AUX/advisor may still pull older `ui`; primary journey prefers DS — no redesign this epic |
| Unused imports / dead code | Not fully tree-shaken audited | Run `npm run analyze` for webpack treemap before GA claim |
| Analyzer script previously a stub echo | **Fixed** | Real `ANALYZE=true` build path |

**No product redesign** performed for bundle size. Only analyzer wiring + budgets + contracts.

### 3.3 Size budgets

| Budget | Value | Gate |
|---|---|---|
| Advisory total static JS under `.next/static` | 3.5 MiB | Warn |
| Hard max total static JS | 6.0 MiB | Fail in CI after build |
| Documented shared First Load | ~103 kB | Documentation baseline (Next route table) |

### 3.4 Lighthouse execution this environment

| Item | Status |
|---|---|
| Config `lighthouserc.cjs` | **Present** |
| Script `npm run lighthouse:ci` | **Present** |
| Full LHCI autorun this pass | **Not required / may be skipped** if no stable `next start` + Chrome session for multi-URL collect — document command above |
| Field LCP/CLS/INP | **Not re-measured** — use LHCI when server is up |

**Performance automation verdict:** **PASS WITH CONDITIONS** — automation established; field CWV / LHCI green on production URL remains a Commercial GA condition.

---

## 4. Known Limitations

1. `perf:budget` sums **all** `.next/static` JS (not Next “First Load shared” alone) — coarser than route tables; use analyzer for deep dives.  
2. Lighthouse asserts are **warn**-level; CI does not yet run LHCI by default (Chrome + running server cost).  
3. Auth-gated analytical modules (loaded holdings / report panels) need authenticated collect for true LCP/INP.  
4. Advisor tree still has many `next/dynamic` routes — good for splitting, but increases chunk count; not collapsed this epic.  
5. OneDrive / incremental `.next` quirks (RC3) can skew local builds — prefer clean `npm run build`.  
6. This certification does **not** authorize “Core Web Vitals certified for public Commercial GA” without a published LHCI/field run.

---

## 5. Recommendations

1. Run `npm run analyze` before each RC cut; attach treemap notes for echarts / cmdk / radix weight.  
2. Add optional GitHub Actions job `lighthouse` (needs server + Chrome) once staging URL exists; keep asserts warn until stable.  
3. Prefer DS imports over dual `ui` on primary journey to reduce duplicate primitive weight.  
4. Keep heavy chart modules behind existing lazy boundaries — never import echarts from marketing layout.  
5. After first LHCI run, record actual Performance/A11y/BP/SEO scores in a dated appendix here.

---

## 6. How to run

```powershell
cd apps/web
npm ci
npm run test:perf
npm run build
npm run perf:budget -- --require-build

# Bundle analyzer (opens / writes HTML report)
npm run analyze

# Lighthouse CI (server must listen on :3000)
npm run start
# separate terminal
npm run lighthouse:ci
```

---

## 7. Alignment

| Reference | Posture |
|---|---|
| RC3 performance | PASS WITH CONDITIONS — Lighthouse budgets were unpublished; this epic **publishes config + scripts** |
| Thin client | Preserved — no client valuation/scoring |
| Accessibility cert | Companion doc — contrast via Lighthouse, structure via vitest-axe |
