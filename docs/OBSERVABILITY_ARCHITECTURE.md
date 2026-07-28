# Observability Architecture (PEP-003)

| Field | Value |
|---|---|
| **Package** | `production_platform` **0.3.0** |
| **Authority** | PEP-000 §8 · ADR-PEP-0009 · PEP-002 ports |

## Ports

| Port | Purpose |
|---|---|
| `LoggingPort` | Structured logs |
| `MetricsPort` | Counters / gauges / timings |
| `TracingPort` | Spans + annotations |
| `AuditEventPort` | Append-oriented audit pipeline |
| `HealthPort` | Liveness / readiness / health |

## Reference adapters

- `InMemoryLoggingPort` / `JsonLoggingPort` / `FanoutLoggingPort`
- `InMemoryMetricsPort` + `PrometheusTextRenderer`
- `InMemoryTracingPort`
- `InMemoryAuditEventPort` / `LoggingAuditEventPort` / `FanoutAuditEventPort`
- `HealthManager` (implements `HealthPort`)

## Optional vendors (lazy)

- `OpenTelemetryTracingPort` — `[otel]`
- `prometheus_client` MetricsPort — `[prometheus]`

## Correlation

`correlation_context` / `X-Request-Id` compatible opaque ids via `new_request_id()`.

## CERT-In

`ObservabilitySettings.cert_in_log_retention_days` must be ≥ **180**. Durable shipping is an ops concern; structure is ready for SIEM/Loki collectors.

## Composition

```python
from production_platform import ObservabilityBundle, ProductionBundle

obs = ObservabilityBundle.create()
bundle = ProductionBundle.create(with_observability=True)
print(bundle.render_prometheus())
```
