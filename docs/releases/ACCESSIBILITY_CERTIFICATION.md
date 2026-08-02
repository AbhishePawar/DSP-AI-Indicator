# ACCESSIBILITY CERTIFICATION — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Programme | EPIC-010 / GA-003 — Accessibility & Performance Automation |
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| Branch | `cursor/p6-1-commercial-readiness` |
| Date | 2026-08-02 |
| Mode | Quality tooling + documentation only — **no** UX redesign; **no** backend/API/engine changes |
| Prior artefacts | `RC3_FINAL_CERTIFICATION_REPORT.md` · `VISUAL_QA_MATRIX.md` · `BROWSER_CERTIFICATION.md` · Design System · Trust Standard |
| Commercial a11y decision | **PASS WITH CONDITIONS** (automation **established**) — **not** unrestricted Commercial public GA |

---

## 1. Executive Summary

Automated accessibility verification is now **established** in-repo on the existing Vitest + Testing Library + `eslint-plugin-jsx-a11y` (via `next/core-web-vitals`) stack, extended with **`vitest-axe` / axe-core** component scans and interaction contracts.

This epic **PASS** means: continuous a11y checks exist, documented scripts run, and the automated suite is green. It does **not** mean Commercial GA is unlocked, full WCAG 2.2 AA is field-proven on every route, or that axe CI has replaced human keyboard / screen-reader certification.

Aligns with RC3 **PASS WITH CONDITIONS**: closed-beta chrome remains acceptable; axe contrast/target-size and full-route browser axe remain residual conditions before unrestricted GA.

---

## 2. Automation Added

| Asset | Role |
|---|---|
| `apps/web` dep `vitest-axe` | axe-core matcher for Vitest |
| `apps/web/src/lib/a11y/runAxe.ts` | jsdom-safe axe runner (contrast/target-size disabled — see Limitations) |
| `apps/web/src/lib/a11y/a11y-automation.test.tsx` | Dialogs, Escape, ARIA live, empty/loading, reduced motion, touch conventions, axe scans |
| Existing `a11y-responsive.test.tsx` | Retained — viewports, critical routes, shell Escape drawer, appearance datasets |
| `npm run test:a11y` | Runs all `src/lib/a11y` tests |
| `npm run test:quality` | a11y + performance automation together |
| `.github/workflows/frontend.yml` | CI step **Accessibility automation** → `npm run test:a11y` |
| ESLint `next/core-web-vitals` | Continues to include `eslint-plugin-jsx-a11y` |

### Coverage mapped to epic asks

| Concern | Automation |
|---|---|
| Keyboard / focus order | Escape closes Modal + mobile nav dialog; focus trap code retained in `AppLayout` (prior EPIC-F010) |
| ARIA | Dialog `aria-modal` / labelled titles; EmptyState `role="status"`; LoadingOverlay `aria-live` + `aria-busy` |
| Dialogs | `Modal` + `ConfirmationDialog` axe + semantics tests |
| Reduced motion | Document `data-motion=reduce` via appearance settings; Skeleton `motion-reduce:animate-none` |
| Color contrast | **Not** asserted in jsdom axe — Lighthouse a11y category + Design System token intent (see PERFORMANCE / Lighthouse) |
| Touch targets | Source contract: shell Topbar/Sidebar `min-h-11` (≥44px convention) |
| Empty / loading states | EmptyState + LoadingOverlay + Skeleton contracts + axe |

---

## 3. Accessibility Results

| Check | Result |
|---|---|
| `npm run test:a11y` (F010 responsive + GA-003 automation) | **PASS** (executed in this epic) |
| Prior RC3 `a11y-responsive.test.tsx` (10/10) | **Retained / PASS** |
| axe-core on EmptyState / LoadingOverlay / ConfirmationDialog | **PASS** (jsdom-safe rule set) |
| Shell Escape / dialog landmark | **PASS** (existing + new Modal Escape) |
| Reduced motion / contrast preference datasets | **PASS** |
| Touch target convention (min-h-11) on shell chrome | **PASS** (source contract) |
| Full-route headed axe CI (Playwright + axe) | **Not present** — condition |
| Computed color-contrast gate in unit CI | **Not present** (jsdom limitation) — condition |
| Screen-reader smoke (NVDA / VoiceOver) on Analysis | **Not re-run** this epic — condition |

**A11y automation verdict:** **PASS WITH CONDITIONS** — automation established; Commercial GA a11y unlock still conditional on contrast/Lighthouse field scores, full-route axe, and SR smoke.

---

## 4. Known Limitations

1. jsdom cannot reliably compute contrast or target-size — those axe rules are disabled in `runAxe` by design.  
2. Component mounts are not full-route trees; landmark/`region` uniqueness is disabled to avoid false fails.  
3. No Playwright + axe end-to-end gate yet (RC3 residual).  
4. AUX / Advisor surfaces may still mix DS/`ui` patterns (hidden from primary palette).  
5. Skip-link coverage is guideline-level; not newly automated in this epic.  
6. Charts still rely on text alternatives / summaries — not axe-scanned as visual encodings.  
7. This certification does **not** authorize “WCAG AA certified for public Commercial GA” marketing language.

---

## 5. Recommendations

1. Add Playwright (or existing browser cert harness) + `@axe-core/playwright` on `/`, `/login`, `/dashboard`, `/analysis` once headed CI Chrome is budgeted.  
2. Promote Lighthouse accessibility assertions from `warn` → `error` only after stable production URLs and auth stubs exist.  
3. Keep Design System token AA review in Visual QA light/dark passes.  
4. Schedule one NVDA or VoiceOver smoke on Company Analysis before Commercial GA claim.  
5. Expand touch-target contracts beyond shell if compact density modes shrink controls below 44×44 CSS px.

---

## 6. How to run

```powershell
cd apps/web
npm ci
npm run test:a11y
# or
npm run test:quality
```

Lighthouse accessibility category (browser; optional):

```powershell
cd apps/web
npm run build
npm run start
# separate terminal
npm run lighthouse:ci
```

---

## 7. Alignment

| Reference | Posture |
|---|---|
| RC3 a11y | PASS WITH CONDITIONS — axe CI was open; this epic **establishes** vitest-axe + CI step (not full-route axe) |
| Browser cert | Chromium live; Firefox/Safari code-review — unchanged |
| Trust / Constitution | Thin client preserved; no scoring/recommendation in browser |
