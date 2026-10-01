# DSP-AI-Indicator — Figma Frontend Surgical Integration

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
