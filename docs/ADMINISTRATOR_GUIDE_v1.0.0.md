# Administrator Guide — DSP Platform Web 1.0.0

## Deploy

```bash
# API
set DSP_ENABLE_SECURITY=true
uvicorn api_platform.api.app:app --host 0.0.0.0 --port 8000

# Web
cd apps/web
npm ci
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL
npm run build
npm run start
```

## Verify

1. `/health` API
2. `/launch` — quality gates PASS, recommendation GO PUBLIC
3. Smoke: login, analysis, portfolio, copilot, report export
4. `pytest` regression GREEN (1551)

## Freeze

See `VERSION_FREEZE_v1.0.0.md` and `apps/web/VERSION_MANIFEST.json`. Do not alter Research Mode or Feature Flag defaults without governance.

## Monitor

`/launch` · `/launch/performance` · `/launch/health` · `/beta` feedback queue (device-local)
