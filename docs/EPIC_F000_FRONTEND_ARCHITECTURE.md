# EPIC-F000 — Frontend Architecture

## Principle

Thin client only. Browser consumes frozen `/api/v1`. No engines, scoring,
valuation, AI reasoning, or compliance logic in the browser.

```
Browser (apps/web)
  │  Next.js 15 App Router · TypeScript · Tailwind
  ▼
API Client (fetch → NEXT_PUBLIC_API_BASE_URL)
  │  JWT Bearer (legacy /auth + A009 /auth/rbac)
  ▼
Backend dsp_platform v1.0.0  (HTTP RC v1.0.0-rc1)
```

## Host application

**Extend** existing `apps/web` — do not bootstrap a parallel app.

| Layer | Location |
|---|---|
| Foundation freeze (F000) | `src/foundation/**` |
| App Router | `src/app/**` (legacy pages untouched) |
| Components | `src/components/**` |
| API / Auth | `src/lib/api`, `src/lib/auth` |
| Providers | `src/providers/**` |

## Technology decisions

See `src/foundation/technology.ts` and package.json `f000ApprovedStack`.

| Concern | Decision |
|---|---|
| Framework | Next.js 15 App Router |
| Language | TypeScript |
| Styling | Tailwind CSS 4 + PR1.2 CSS vars |
| UI kit | shadcn/ui **adopt in F001** (custom `components/ui` interim) |
| Icons | Lucide React (F001) |
| Client state | Zustand (F001) |
| Server state | TanStack Query (live) |
| Forms | RHF + Zod (F001) |
| Tables | TanStack Table (F001) |
| Charts | Apache ECharts (F001) |
| Theme | next-themes (F001) + existing ThemeProvider interim |
| Auth | JWT via existing backend APIs |

## Non-negotiables

- Backend v1.0.0 / API contracts unchanged
- Research Mode labels and trust surfaces preserved
- Accessible-first · responsive-first · enterprise-grade
- Missing data → **"Data unavailable."**

## Final architecture diagram

```
┌─────────────────────────────────────────────┐
│  (auth) shell     (app) shell   (admin)     │  ← route groups (F001+)
│  header/sidebar/footer specs frozen (F000)  │
├─────────────────────────────────────────────┤
│  foundations → primitives → patterns → domain│  ← component hierarchy
├─────────────────────────────────────────────┤
│  TanStack Query (server) · Zustand (UI)     │
├─────────────────────────────────────────────┤
│  fetch API client · JWT session             │
└─────────────────────────────────────────────┘
```
