# P1.3 — Production Monitoring & Reliability

Status: **COMPLETE** · Backend **`dsp_platform` v1.2.0** · Frontend **unchanged**

## Architecture

Operations-only enrichment of the HTTP surface (`api_platform`). No changes to
analyse / valuation / recommendation / AI Committee / business contracts.

```
Request
  → RequestContextMiddleware (X-Request-Id, latency, redacted access logs)
  → MetricsMiddleware / RateLimit / SecurityHeaders
  → Routes
  → /health*  (component + lifecycle model)
  → /metrics  (Prometheus text)
```

New module: `api_platform.api.monitoring` (redaction, severity, lifecycle, resources).

## Health Model

| Endpoint | Purpose | States |
|---|---|---|
| `GET /health` | Platform offline checks + components | `status`, `ready`, `platform_status`, `components` |
| `GET /health/live` | Liveness | `status: alive` / `stopping`; `lifecycle: startup\|ready\|degraded\|unhealthy\|shutting_down\|stopped` |
| `GET /health/ready` | Readiness for traffic | `ready`, `platform_status: ready\|degraded` → **200**; `unhealthy` \| `startup` \| shutdown → **503** |

`platform_status` (on both `/health` and `/health/ready`) is the same
`PlatformLifecycleState` value resolved by `resolve_platform_status()` —
additive field on `HealthResponse` (RC1: `test_monitoring_p13.py` fixed to
match this always-emitted contract). On `/health/ready` it is derived from
the soft-fail `accept` signal, not the strict platform-ready flag, so a
replica accepting traffic via the copilot soft-fail path reports
`degraded`, never `unhealthy`.

### Components (JSON)

- `application`
- `api`
- `authentication`
- `database` (skip/`Unavailable` when not configured)
- `storage` (skip/`Unavailable` when not configured)
- `research_service`
- `overall`
- `copilot` (missing → **degraded**, not unhealthy)

### Lifecycle

`startup` → `ready` / `degraded` / `unhealthy` → `shutting_down` → `stopped`

Set via FastAPI lifespan + synchronous ready mark in `create_app`.

## Logging Policy

Structured JSON lines via `ops_logger`:

- API requests, authentication, authorization failures
- Analysis / research / export path categories
- Unhandled exceptions
- System startup / shutdown

**Never logged:** passwords, JWTs, Bearer tokens, API keys, secrets (redacted to `[REDACTED]`).

Severity: `critical` | `error` | `warning` | `info` (`classify_error`).

Correlation: `X-Request-Id` / `correlation_id` on log events and error bodies.

## Metrics Catalogue

| Metric | Type | Meaning |
|---|---|---|
| `dsp_http_requests_total` | counter | HTTP requests |
| `dsp_http_errors_total` | counter | HTTP 5xx |
| `dsp_analysis_requests_total` | counter | Analyse/analyze paths |
| `dsp_analysis_failures_total` | counter | Analyse 4xx/5xx |
| `dsp_research_requests_total` | counter | Research paths |
| `dsp_export_requests_total` | counter | Export paths |
| `dsp_auth_failures_total` | counter | HTTP 401 |
| `dsp_authz_denials_total` | counter | HTTP 403 |
| `dsp_rate_limit_events_total` | counter | HTTP 429 |
| `dsp_system_restarts_total` | counter | App lifespan starts |
| `dsp_uptime_seconds` | gauge | Process uptime |
| `dsp_api_latency_ms_last` | gauge | Last request latency |
| `dsp_api_latency_ms_avg` | gauge | Mean latency |
| `dsp_analysis_duration_ms_last` | gauge | Last analyse latency |
| `dsp_research_duration_ms_last` | gauge | Last research latency |
| `dsp_export_duration_ms_last` | gauge | Last export latency |
| `dsp_build_info` | gauge | Build labels |

Scrape: `GET /metrics` (Prometheus text 0.0.4).

Resources on `/health/ready`: `resources` (uptime, memory/CPU best-effort).

## Recovery Plan

### Backup strategy (documented only)

| Asset | Strategy | Frequency | Retention |
|---|---|---|---|
| Postgres (if profile `infra`) | `pg_dump` / volume snapshot | Daily | ≥ 30 days |
| Redis | Optional RDB/AOF — ephemeral cache OK to lose | N/A | N/A |
| Local research archive / persistence files | Filesystem snapshot of configured storage path | Daily | ≥ 30 days |
| Secrets / env | Secret manager or sealed config — never in git | On change | Per org policy |
| Container images | Registry tags immutable | Per release | Keep last N prod tags |

### Restore procedure

1. Stop API (`docker compose stop api`) or drain traffic.
2. Restore DB from latest verified dump; verify `pg_isready`.
3. Restore persistence/storage volume if used.
4. Set `DSP_JWT_SECRET` and production env via `scripts/validate_env.py`.
5. Start API; wait for `/health/ready` → 200.
6. Smoke: `/health/live`, `/version`, authenticated `/api/v1/analyse` if required.

### Disaster recovery checklist

- [ ] Identify last known-good backup timestamp  
- [ ] Confirm secrets available (JWT, DB URL)  
- [ ] Restore data stores  
- [ ] `validate_env.py` production profile  
- [ ] Bring up API with `unless-stopped`  
- [ ] Confirm `/health/ready` and `/metrics`  
- [ ] Confirm auth login + one analyse  
- [ ] Review ops logs for `system_startup` / errors  

External backup SaaS is **not** implemented in this epic.

## Deployment Readiness

| Item | Status |
|---|---|
| Docker Compose healthcheck (`/health/ready`) | Present |
| Backend Dockerfile HEALTHCHECK | Aligned to `/health/ready` |
| Restart policy `unless-stopped` | Present |
| `scripts/validate_env.py` | Present |
| Graceful shutdown (`--timeout-graceful-shutdown`) | Present (`start-api.sh`) |
| FastAPI lifespan startup/shutdown logs | Present |
| Production JWT default rejected | Present (P1.2) |

## Operational Checklist

1. Enable `DSP_RATE_LIMIT_ENABLED` + HSTS in production.  
2. Scrape `/metrics` from Prometheus/Agent.  
3. Alert on `/health/ready` ≠ 200 for >2m.  
4. Alert on rising `dsp_http_errors_total` / auth failures.  
5. Rotate JWT secrets per org policy.  
6. Verify backups before major releases.  

## Testing

`packages/api_platform/tests/test_monitoring_p13.py`  
`packages/api_platform/tests/test_health_rc1.py` (compat)

## PASS / FAIL

**PASS** — Backend **v1.2.0**, frontend unchanged, analysis contracts unchanged.
