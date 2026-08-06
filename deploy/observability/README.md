# Observability stack (EPIC-017)

Extends EPIC-011A / P7.4 hooks. **Vendor-neutral**: OTel → collector → Prometheus / logs / optional Sentry.

## Canonical compose wiring

Already in `docker/docker-compose.production.yml`:

- Prometheus (`docker/prometheus.yml`, `docker/prometheus/alerts.yml`)
- Alertmanager (`docker/alertmanager.yml`)
- Grafana dashboards (`docker/grafana/`)
- postgres-exporter, redis-exporter, cAdvisor

This directory adds:

| Path | Purpose |
|---|---|
| `otel/otel-collector-config.yaml` | OTLP receiver → Prometheus / logging exporters |
| `prometheus/recording_rules.yml` | P95/P99 / cache / queue recording rules |
| `prometheus/production_alerts.yml` | Extended production alerts (latency, auth, rate-limit) |
| `grafana/dashboards/dsp-production-health.json` | Production health overview |

## Application hooks (existing, do not redesign)

- `production_platform.production.otel_tracing` — `OpenTelemetryTracingPort`, `try_build_otel_tracing`
- `production_platform.production.prometheus_metrics` — Prometheus client adapter
- `production_platform.production.json_logging` — structured JSON + correlation
- `production_platform.production.correlation` — `correlation_id` / request IDs
- API `GET /metrics`, `GET /health/live`, `GET /health/ready`

## Optional Sentry

Set `DSP_SENTRY_ENABLED=true` and `DSP_SENTRY_DSN=…` only when an adapter is wired. Default off — no vendor lock-in.
