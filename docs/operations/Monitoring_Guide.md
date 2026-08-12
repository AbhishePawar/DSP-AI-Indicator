# Monitoring Guide (EPIC-017)

Extends P7.4 / EPIC-011A observability. Vendor-neutral first; optional Sentry adapter.

## Architecture

```
API (metrics + JSON logs + correlation)
  → Prometheus scrape /metrics
  → (optional) OTel Collector OTLP
Grafana ← Prometheus
Alertmanager ← Prometheus rules
```

Compose stack: `docker/docker-compose.production.yml`  
Extras: `deploy/observability/`

## Golden signals

| Signal | Source | Target (guidance) |
|---|---|---|
| API latency P95 | `dsp:api_latency_p95_ms` / `dsp_api_latency_ms_*` | < 1500 ms (ops paths) |
| API latency P99 | `dsp:api_latency_p99_ms` | < 3000 ms |
| Error ratio | `dsp:api_error_ratio_5m` | < 5% |
| DB up / latency | `pg_up`, exporter stats | up=1; investigate slow queries |
| Cache hit ratio | `dsp:redis_hit_ratio` | investigate if < 0.5 sustained |
| Queue depth | `dsp:queue_depth` / job metrics | alert > 1000 |
| Memory / CPU | cAdvisor / k8s metrics | < 85% sustained |
| Disk | node / volume metrics | > 15% free |
| Auth failures | `dsp_auth_failures_total` | spike alert |
| Rate-limit violations | `dsp_rate_limit_violations_total` | spike alert |
| WebSocket / sessions | session gauges when exposed | trend vs baseline |

> Research/valuation path latency is **not** redesigned here; monitor separately if product SLOs require it.

## Endpoints

| Endpoint | Use |
|---|---|
| `GET /health/live` | Liveness |
| `GET /health/ready` | Readiness (dependencies) |
| `GET /health` | Aggregated component health |
| `GET /metrics` | Prometheus text |
| `GET /api/health` (web) | Frontend health |

## Structured logging & correlation

- JSON logging via `production_platform.production.json_logging`
- Correlation: `correlation_id` / request ID middleware (`ops_middleware`, exception handlers)
- Propagate `X-Request-ID` where clients supply it

## Dashboards

1. Existing: `docker/grafana/dashboards/dsp-operations.json`
2. EPIC-017: `deploy/observability/grafana/dashboards/dsp-production-health.json` (uid `dsp-epic017-health`)

Import path or bind via Grafana provisioning volume.

## Alerts

| File | Scope |
|---|---|
| `docker/prometheus/alerts.yml` | Availability, basic latency/errors, resources |
| `deploy/observability/prometheus/production_alerts.yml` | P95/P99, auth, rate-limit, cache, queue, disk |
| `deploy/observability/prometheus/recording_rules.yml` | SLI recording |

## OpenTelemetry

1. Deploy collector: `deploy/observability/compose.otel.override.yml`
2. Set `DSP_OTEL_ENABLED=true`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`
3. App adapter: `try_build_otel_tracing` (no vendor SDK lock-in in business code)

## Optional Sentry

```
DSP_SENTRY_ENABLED=false   # default
DSP_SENTRY_DSN=
```

Enable only with an adapter that maps exceptions → Sentry without coupling engines to the vendor.

## Rate limits & auth

- Middleware: `RateLimitHookMiddleware` — Redis `RateLimitPort` when infra attached
- Auth failure counters should appear in metrics/audit; investigate credential stuffing vs misconfig

## Cache & queues

- Redis exporter job `redis` in `docker/prometheus.yml`
- Queue abstraction: `JobQueuePort` with retry/DLQ in `production_platform.production.job_queue`
- Depth metric name may be `dsp_job_queue_depth` when wired; alert uses `or vector(0)` safely

## Runbooks linkage

Alert annotations point to [Incident_Response.md](./Incident_Response.md) and this guide's sections (`#cache`, `#queues`, `#rate-limits`).
