# DSP Web (`dsp-web` 2.5.0)

EPIC-003 Intelligence Workspace at `/intelligence` — consumes `/api/v1` only.

# DSP Web (L1.2)

Next.js thin client over frozen backend **v1.0.0-rc1** `/api/v1`.

**Version:** `2.0.0` — Epic V2.0 Sprint 1 Advisor Platform Foundation

See `docs/V2_SPRINT1_ADVISOR_FOUNDATION.md` through `docs/V2_SPRINT6_CLIENT_REVIEW_WORKFLOW.md`. Enable with `NEXT_PUBLIC_ADVISOR_DEMO=true`.


## Stack

- Next.js · React · TypeScript
- Tailwind CSS
- TanStack Query

## Setup

```bash
cd apps/web
npm install
cp .env.example .env.local
```

Start the API with security enabled:

```bash
# from repo root, with PYTHONPATH / venv active
set DSP_ENABLE_SECURITY=true
uvicorn api_platform.api.app:app --reload --port 8000
```

Then:

```bash
npm run dev
```

Open http://localhost:3000 — login as seeded user `admin`.

## Pages

| Route | Purpose |
|---|---|
| `/login` | Authentication → `POST /api/v1/auth/login` |
| `/dashboard` | Widget dashboard |
| `/analysis` | Company analysis → `POST /api/v1/analyze/company` |
| `/search` | Redirect → `/analysis` |
| `/compare` | Compare stub |
| `/portfolio` | Portfolio stub |
| `/copilot` | Copilot stub |
| `/reports` | Recent report ids |
| `/reports/[id]` | `GET /api/v1/report/{id}` |
| `/settings` | Theme preferences |
| `/health` | `GET /api/v1/health` |
| `/platform` | `GET /api/v1/platform` |

See `docs/L1_1_DASHBOARD_AND_NAVIGATION.md` for layout, widgets, and a11y.

## Rules

- No direct `dsp_platform` imports
- No valuation / recommendation / workflow business rules in the browser
- All analysis results come from the API envelope
