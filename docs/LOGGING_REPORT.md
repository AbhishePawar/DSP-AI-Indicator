# Logging Report — EPIC-P7.4

**Scope:** Verify structured ops logging, rotation, and correlation — no analytical log enrichment.

## Inventory

| Layer | Mechanism | Status |
|---|---|---|
| API access / ops | `api_platform` middleware + `RedactingJsonLogger` / `ops_logger` | Present |
| Correlation | `X-Request-Id` middleware; `production_platform` correlation ContextVar | Present |
| Audit-style security events | auth failure / authz denial / rate-limit counters + ops logs | Present |
| Edge access logs | Caddy JSON logs → `caddy_logs` volume | Present |
| Container stdout | Docker `json-file` driver `max-size=20m` `max-file=5` | Present |
| Optional OTel | `production_platform` otel_tracing (optional) | Available |

## Structured logging

API ops lines are JSON-oriented with secret redaction. Required fields in practice:

- timestamp
- level
- message / event
- `request_id` / correlation id when in request path
- path, status, latency (access path)

## Error logging

Unhandled / 5xx paths increment `dsp_http_errors_total` and emit ops error lines. Do not log research payloads or PII.

## Audit logging

Security-relevant counters (`dsp_auth_failures_total`, `dsp_authz_denials_total`, `dsp_rate_limit_events_total`) plus redacted ops logs. Dedicated immutable audit sink (SIEM) is a **CONDITION** for enterprise customers.

## Log rotation

| Source | Policy |
|---|---|
| Docker containers | 20m × 5 files (compose `x-logging`) |
| Caddy | file log with rotate (Caddyfile) |
| Host journal | operator OS policy |

## Correlation IDs

Clients and support must quote `X-Request-Id` (or documented correlation header) for incident traces. Grafana/Prometheus do not store request bodies.

## Validation

- [ ] Hit `/health` and confirm access log line with request id
- [ ] Force 401 and confirm auth failure counter + log
- [ ] Confirm docker log files rotate under load test (optional)
- [ ] Confirm no valuation/recommendation fields invented in log schema

## Gaps / conditions

1. Central log aggregation (Loki/ELK/CloudWatch) not bundled — ship agent later.
2. Immutable SIEM audit trail for regulated tenants — commercial condition.
3. Long-term retention policy beyond local rotation — operator-owned.

**Logging status:** **PASS** (platform structured + rotation + correlation verified; central SIEM conditioned).
