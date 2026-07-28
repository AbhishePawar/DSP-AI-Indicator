# Deployment Guide — DSP Web 1.0.0

## Prerequisites

- Frozen backend **v1.0.0-rc1** on `/api/v1`
- Node 20+ for web build
- Python venv for API + pytest

## API

```bash
set DSP_ENABLE_SECURITY=true
uvicorn api_platform.api.app:app --host 0.0.0.0 --port 8000
```

## Web

```bash
cd apps/web
npm ci
cp .env.example .env.local
npm run build
npm run start
```

## Verification

1. `/login` → seeded admin  
2. `/health` API status  
3. `/launch` — GO PUBLIC · quality gates PASS  
4. `/analysis` smoke  
5. `/portfolio` demo session  
6. Copilot open/close  
7. Report Markdown export  
8. `/docs` documentation hub  

## Headers

`next.config.ts` ships **enforced** CSP plus nosniff, frame deny, referrer, permissions policy. `productionBrowserSourceMaps=false`.

## Rollback

Redeploy previous web artifact `0.9.5`; API contracts unchanged.

## Enterprise infrastructure (PEP-002)

Optional Postgres + Redis for local/staging:

```bash
docker compose --profile infra up postgres redis
```

See [INFRASTRUCTURE_ARCHITECTURE.md](INFRASTRUCTURE_ARCHITECTURE.md),
[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md),
[LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md),
[PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md).

Default API/web compose still runs without external infra (in-memory ports).
