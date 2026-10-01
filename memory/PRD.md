# DSP-AI-Indicator — Figma Full-Stack Integration

## Current authoritative requirements (continuation)
- LATEST visual authority is the live site https://cel-bacon-55476680.figma.site/ supplied explicitly by the user. Fetched rendered HTML and inspected desktop screenshot; Fraunces heading font verified directly. ZIP source remains implementation reference. Do not reproduce its demo user, fabricated coverage metrics, or financial fixtures.
- Latest uploaded ZIP extracted at `.figma_latest` has 76 files; all 55 design/source files match `.figma_ref` byte-for-byte. User explicitly says most design is implemented: differences-only changes, no whole-app rebuild, no repeated work.
- Delta audit: `UI_DELTA_AUDIT.md`. Current batch replaces incompatible home sidebar with reference marketing hero/header/depth selector, updates directory search/filter/grid, adds real-history Research Hub while preserving detailed workspace, restores analysis detail navigation by reusing existing backend-fed sections, and corrects Fraunces headings. Batch not yet validated; see test_reports/ui_delta.
- User authorized frontend AND backend changes; preserve DSP deterministic research methodology, financial calculations, evidence/source hierarchy and final-result authority without alteration.
- Figma ZIP remains UI/UX authority; existing repository remains business logic authority. All 21 requested screens must be covered (reference router actually has 27 named paths, including an alias).
- Real data only. Clear loading/error/unavailable states, never substitute fabricated financials, scores, citations or verification results. No internal prompts/provider disputes exposed to ordinary clients.
- Latest request: remove dependencies on Upstox, FMP, etc. User replied “ok” to clarification; stated implementation assumption is commercial financial-vendor removal while retaining official disclosures and source-neutral interfaces. See `DATA_SOURCES.md` for exact scope.
- Current branch: `feature/figma-frontend-integration`; use platform GitHub save for publication.

## Continuation implemented
- Restored Python API on 8001 via `backend/server.py`, importing the original FastAPI application with monorepo packages taking precedence over colliding installed package names.
- Corrected frontend base path from `/dspapi/v1` to `/api/v1`. Real health, cookie auth, market/fundamental APIs reachable through preview.
- Supervisor serves Next production build from `apps/web` on 3000. Backend watches monorepo packages. External screenshot hydration works.
- One application shell/sidebar for dashboard, analysis and other app routes. 220px sidebar, 48px topbar, permission-filtered legacy tools, mobile drawer/collapse/command palette preserved. Unused ResearchShell removed; unrelated advisor shell retained.
- Dashboard no longer duplicates marketing landing. Added actual device watchlist with add/remove/persistence, API-backed quote/health requests, real search history, explicit unavailable indices/signals.
- Company analysis sends identity-only ticker/exchange/company to existing server-authoritative `/analyse`; no frontend-injected financial statement or valuation fields. Request type now correctly permits server-side source resolution; statement-builder return types remain strict.
- Figma-aligned analysis loading/error/form states; disclaimer acknowledgement now dispatches queued action before closing clears it (fixes required second click).
- Inter replaces accidental Fraunces display font; JetBrains Mono retained. Landing no longer fabricates recent searches or AP account identity; real search history/account links used.
- Removed dead passwordless legacy login fallback; enterprise/RBAC auth preserved. Login and disclaimer automation identifiers added.
- ESLint 9 native Next flat config repaired; CLI is `eslint .` because Next 16 removed `next lint`. CI lint restored; Node-compatible jest-dom pinned and yarn lock added. Legacy React Compiler set-state-in-effect diagnostics remain WARNINGS, not suppressed. Other actual lint errors fixed.
- Commercial vendor runtime decommission: removed quote/statement FMP branches and validation bypass, commercial registry auto-registration, Yahoo legacy default wiring, commercial control-center defaults, vendor secret requests in example env/CI/ops. Official SEC/NSE/BSE and source-neutral authenticated HTTP paths retained. Historical standalone vendor implementation classes remain but are not selected by runtime defaults.
- Core DSP methodology/calculation/pipeline packages untouched.

## Testing checkpoint
- `test_reports/iteration_1.json`: 73/77 focused backend regressions plus 9/9 live API; shell/login/watchlist/identity-only analysis browser flows passed. Four obsolete vendor tests and UX issues were identified.
- Subsequent fixes: disclaimer ordering, real landing history/account, Inter display, login testids, removed obsolete login fallback, updated boot-boundary tests to neutral HTTP. Retest required after vendor-removal changes.
- Production build passed before latest fixes; latest build/lint logs `/tmp/dsp-build-2.log`, `/tmp/dsp-lint-2.log`. Earlier lint: 0 errors, 110 warnings. Do not claim full screen parity or full-suite success from this checkpoint.

## Remaining work / acceptance blockers
- P0: Verified official/source-neutral quote and statement feeds are NOT connected. Preview unavailable states are genuine. Do not ask for FMP/Upstox keys after the latest user decision.
- P0: `/research/company` remains deliberately architecture-gated; do not bypass it with an LLM. Existing `/analyse` canonical pipeline remains authoritative.
- P0: Existing A008 auth/application persistence uses in-memory ports; not production durable. Preview credentials in `test_credentials.md`; external OAuth/SMS/email delivery unconfigured.
- P0: Remove/replace pre-existing advisor demo datasets and company-directory fabricated screening metadata before final no-mock acceptance. These were discovered, not introduced here.
- P1: Full per-screen pixel/interaction parity and real-data acceptance remain. `FIGMA_PARITY.md` maps every reference route. Compare/portfolio/research hub/institutional/canvas/intelligence/copilot/profile/admin/control-center/diagnostics/coupons/public/auth screen interiors require further work.
- P1: Full source-provider removal regression tests; update any tests that still expect commercial default factories without weakening evidence/calculation safeguards.
- P2: Resolve remaining legacy lint warnings; consider syncing device watchlists to authenticated durable storage once that exists.
- No claim of production readiness or completed 21-screen implementation.

## Historical prior-session notes (superseded where they conflict above)

## Original problem statement
Surgically migrate the existing `AbhishePawar/DSP-AI-Indicator` repo's frontend to the
supplied Figma frontend (ZIP) as the authoritative UI/UX target — WITHOUT rebuilding,
without replacing the backend, preserving all existing backend/API/auth/business logic,
and connecting real data (no mock production data). All 21 Figma pages in scope. Adopt the
Figma token system app-wide. Push via Emergent GitHub integration.

## Architecture (as found)
- Monorepo: Python backend packages (`packages/*`, FastAPI `api_platform`) + Next.js 16 web app in `apps/web`.
- `apps/web`: React 19, Tailwind v4, shadcn-style DS (`src/components/ds`), tanstack query/table,
  echarts, zustand. ~28 App Router routes. Mature API client at `src/lib/api/client.ts` (`/api/v1`).
- Existing own design system (warm beige / Sora). Figma ZIP = dark + purple `#7c6af7`, Inter/Fraunces/JetBrains Mono.

## User choices
- All 21 pages. Frontend-only migration (preserve API contracts, backend not run live in preview).
- Adopt Figma token set app-wide. Push via Emergent GitHub integration.

## Done (2026-06 / this session) — branch `feature/figma-frontend-integration`
- **Build fix (critical):** restored 4 files emptied by a bad merge on `main` — `apps/web/package.json`,
  `src/app/analysis/page.tsx`, `CompanyAnalysisWorkspace.tsx`, `MarketingLanding.tsx`. App now builds.
- **Figma design tokens app-wide:** remapped existing semantic CSS vars (`--bg/--fg/--surface/--border/
  --accent/--muted/--accent-soft`...) to the Figma dark palette, added shadcn/Figma alias tokens
  (`--card/--primary/--muted-foreground`...), financial colors, spacing scale, and Figma utility classes
  (`.dsp-card/.section-label/.stat-value`) in `globals.css`. Entire app (all routes + shell) now renders
  in the Figma visual language.
- Fonts: Sora→Inter (body), added JetBrains Mono (`--font-data`), kept Fraunces (display). Default theme = dark.
- Hardened auth session restore (AbortController timeout + guaranteed terminal state) so the app never
  hangs on "Restoring session…" when the API is slow/unreachable.
- Relaxed CSP gated behind `DSP_RELAX_CSP` (preview/E2E only); real production keeps strict nonce/strict-dynamic.
- Preserved: backend, all `/api/v1` API client contracts, auth/cookie-session, routing, RBAC nav,
  business logic, real backend-driven empty/loading/error states (no mock data).
- Verified via headless Chromium through the preview proxy: landing, login, dashboard, analysis, compare,
  companies, pricing, profile all render in Figma style with real content/empty states; routing works.
- Production `next build` passes (full TypeScript type-check).

## Known limitations / notes
- Backend NOT run live in preview (user choice): browser `/api/v1` calls resolve to clean empty/error states.
- Emergent **screenshot tool** browser shows the SSR "Restoring session" state (environment quirk); the app
  renders fully in normal browsers (verified with headless Chromium against the same preview URL).
- The existing permission-aware shell/sidebar was preserved and re-skinned (surgical principle), not replaced
  by the ZIP's static sidebar; the research routes (landing/dashboard/analysis) use the Figma-exact shell.
- ESLint has a pre-existing eslint9/eslintrc config bug in the repo (unrelated to this work).

## Backlog / next tasks
- P1: Per-page pixel parity pass against each of the 21 Figma ZIP screens where the existing page diverges.
- P1: Run the real Python backend on :8001 for true end-to-end data in preview.
- P2: Fix repo ESLint flat-config, re-enable `next lint` in CI.
- P2: Reconcile the two shell variants (ResearchShell vs AppShell) into one if desired.
