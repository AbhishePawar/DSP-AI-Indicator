# Phase L1.0 — Web Application Foundation

**Status:** Implemented · Frontend shell only · No investment logic  

**App:** `apps/web` **0.1.0**  
**Backend:** Platform RC **v1.0.0-rc1** via `/api/v1` only  

The web application is a thin client over the frozen API Platform. All
analysis is requested from the backend; the browser never imports
`dsp_platform` and never computes valuation, recommendations, or workflow
rules.

---

## Stack

Next.js · React · TypeScript · Tailwind CSS · TanStack Query

---

## Implemented

- Application shell + global layout + theme (light/dark)
- Routing for Login, Dashboard, Company Search, Health, Platform
- Auth UI → `POST /api/v1/auth/login` (JWT stored locally)
- API client bound to `NEXT_PUBLIC_API_BASE_URL` (`/api/v1`)
- Error boundaries + loading states
- Environment configuration (`.env.example`)

---

## Run

```bash
# API (repo root, venv)
set DSP_ENABLE_SECURITY=true
uvicorn api_platform.api.app:app --reload --port 8000

# Web
cd apps/web
npm install
npm run dev
```

Login: seeded username `admin`.

---

## Non-goals (this phase)

No valuation calculations · no recommendation logic · no workflow execution
logic · no business rules in the browser · no mobile app.
