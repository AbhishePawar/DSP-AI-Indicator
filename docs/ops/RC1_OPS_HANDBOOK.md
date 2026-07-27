# DSP AI Indicator — RC1 Operations Handbook

**Release:** 1.0.0-rc1 · **Frontend:** 3.0.0-rc1 · **API Platform:** 0.2.0

This handbook consolidates deployment, architecture, environment, monitoring, incident response, backup, and release guidance for Release Candidate 1.

---

## 1. Deployment Guide

### Docker (recommended for RC1)

```bash
cp .env.example .env
# Edit .env with secrets and URLs

cd docker
docker compose up --build
```

Production override:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Manual

**API:**
```bash
pip install -e ".[dev]"
DSP_ENABLE_SECURITY=true uvicorn api_platform.api.app:app --host 0.0.0.0 --port 8000
```

**Web:**
```bash
cd apps/web && npm ci && npm run build && npm start
```

### Health verification

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Legacy platform health |
| `GET /health/live` | Liveness (process up) |
| `GET /health/ready` | Readiness (platform + providers) |
| `GET /metrics` | Prometheus scrape |
| `GET /api/health` (web) | Frontend health |

---

## 2. Architecture Guide

```
Browser → Next.js (apps/web) → /api/v1/* → api_platform → dsp_platform
                                              ↓
                                         llm_adapters (optional)
                                              ↓
                                         External LLM (backend only)
```

- **Thin client:** No scoring, valuation, or LLM in browser
- **Frozen domains:** copilot, valuation, recommendation, committee untouched in RC1
- **Containers:** `docker/backend`, `docker/frontend`, compose in `docker/`

---

## 3. Environment Reference

| Variable | Required (prod) | Description |
|----------|-----------------|-------------|
| `DSP_ENVIRONMENT` | Yes | `development` / `staging` / `production` |
| `DSP_JWT_SECRET` | Yes | JWT signing secret |
| `DSP_CORS_ORIGINS` | Yes | Comma-separated trusted origins |
| `DSP_ENABLE_SECURITY` | Yes | `true` in production |
| `DEFAULT_AI_PROVIDER` | No | `deterministic` default; `openai` when keyed |
| `OPENAI_API_KEY` | No | Backend LLM only |
| `NEXT_PUBLIC_API_BASE_URL` | Yes (web build) | API base URL |
| `NEXT_PUBLIC_AI_PROVIDER` | No | `deterministic` or `backend` |

Validate: `python scripts/validate_env.py`

Templates: `.env.example`, `.env.production.example`

---

## 4. Operations Runbook

### Startup
1. Validate environment (`scripts/validate_env.py`)
2. Start API → wait for `/health/ready` 200
3. Start web → wait for `/api/health` 200
4. Smoke: `GET /api/v1/version`, login, analyse sample ticker

### Shutdown
- API: SIGTERM → uvicorn graceful shutdown (30s default)
- Web: SIGTERM → Next.js process exit

### Rollback
1. Redeploy previous image tag
2. Verify `/health/ready`
3. Confirm frontend build version in `/api/health`

---

## 5. Monitoring Guide

- **Logs:** Structured via `RequestContextMiddleware` (`X-Request-Id`, `X-Response-Time-Ms`)
- **Metrics:** `GET /metrics` (Prometheus text format)
- **Tracing:** Placeholder ports in `production_platform` — wire OTel at deploy edge
- **Frontend diagnostics:** `/diagnostics` (authenticated)

### Key metrics
- `dsp_http_requests_total`
- `dsp_http_errors_total`
- `dsp_uptime_seconds`
- `dsp_build_info`

---

## 6. Incident Response

1. **Detect** — health/readiness failure, error rate spike, 5xx alerts
2. **Triage** — check `/health/ready` JSON for `llm`, `providers`, `checks`
3. **Mitigate** — scale containers, disable LLM (`DEFAULT_AI_PROVIDER=deterministic`)
4. **Communicate** — note deterministic fallback is automatic
5. **Post-incident** — update runbook, no engine hotfixes under RC1

---

## 7. Backup & Recovery

RC1 uses **ephemeral** API stores (`ReportStore`, `ContextStore`). User portfolio persistence is **browser localStorage** (per-user, per-device).

| Data | RC1 persistence | Recovery |
|------|-----------------|----------|
| Analysis results | Session / saved analyses (client) | Re-run analysis |
| Portfolio | localStorage | User export (future) |
| Auth tokens | sessionStorage/localStorage | Re-login |
| Server state | None durable | Redeploy |

---

## 8. Release Process

1. All CI workflows green (Python, Frontend, Docker)
2. Tag `v1.0.0-rc1` → triggers `release.yml`
3. Complete production checklist (below)
4. Deploy images `dsp-api:rc1`, `dsp-web:rc1`
5. Smoke test health endpoints
6. Await RC1 approval before GA

---

## 9. Release Notes (RC1)

### Added
- Docker multi-stage builds (API + Web)
- Docker Compose + production override
- `/health/live`, `/health/ready`, `/metrics`
- GitHub Actions: Frontend CI, Docker build, Release workflow
- Environment validation script
- Security headers + rate-limit hooks
- Operations documentation

### Unchanged
- Deterministic analysis pipeline
- Deterministic copilot behaviour
- AI provider logic
- API contracts (`/api/v1/analyse`, etc.)

---

## 10. Migration Guide

From manual dev setup to RC1 containers:

1. Copy `.env.example` → `.env`
2. Set `NEXT_PUBLIC_API_BASE_URL` to public API URL at **build time**
3. Set `DSP_CORS_ORIGINS` to web origin
4. Enable `DSP_ENABLE_SECURITY=true` for production
5. Use `NEXT_PUBLIC_AI_PROVIDER=backend` for server-side LLM routing

---

## 11. Version Compatibility Matrix

| Component | RC1 Version |
|-----------|-------------|
| Frontend | 3.0.0-rc1 |
| API Platform | 0.2.0 |
| DSP Platform | 0.7.x |
| Composition Pipeline | 1.0.0-epic-001 |
| Python | 3.11–3.12 |
| Node | 22.x |

---

## 12. Production Checklist

- [ ] `DSP_JWT_SECRET` rotated from dev default
- [ ] `DSP_CORS_ORIGINS` set to production domain only
- [ ] `DSP_ENABLE_SECURITY=true`
- [ ] TLS terminated at load balancer
- [ ] `/health/ready` wired to orchestrator
- [ ] `/metrics` scraped by Prometheus
- [ ] Secrets in vault (not `.env` in image)
- [ ] Dependency audit run (`pip audit`, `npm audit`)
- [ ] Frontend production build verified
- [ ] Docker images built and tagged
- [ ] Smoke tests pass
- [ ] Rollback procedure documented

---

## 13. Known Limitations (RC1)

- No durable server-side portfolio database
- Anthropic/Gemini adapters are stubs
- In-memory metrics (no external APM wired)
- Rate limiting is a hook — use edge gateway in production
- Context store for legacy `/copilot/chat` not persisted
- No billing/usage metering

---

**STOP — RC1 infrastructure complete. Awaiting RC1 approval.**
