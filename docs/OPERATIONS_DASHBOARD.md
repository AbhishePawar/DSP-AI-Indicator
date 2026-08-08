# Operations Dashboard — EPIC-P7.4

**Versions:** Backend `1.7.4` · Frontend `2.0.4` · API `v1.0.0`  
**Stack:** Grafana (provisioned) ← Prometheus ← API `/metrics` + cAdvisor + postgres/redis exporters

## Access

| Surface | Default |
|---|---|
| Grafana UI | `http://<host>:${GRAFANA_HOST_PORT:-3001}` |
| Dashboard | **DSP Operations Dashboard** (`uid: dsp-operations-p74`) |
| Prometheus | internal `prometheus:9090` (do not expose publicly) |
| Alertmanager | internal `alertmanager:9093` |

Credentials: `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` from `.env.production` (change from defaults).

## Panels (required coverage)

| Panel | Source metric(s) |
|---|---|
| System Health | `up{job="dsp-api"}`, `pg_up`, `redis_up`, `dsp_uptime_seconds` |
| CPU | `rate(container_cpu_usage_seconds_total[…])` (cAdvisor) |
| Memory | `container_memory_working_set_bytes` |
| Disk | `container_fs_usage_bytes` |
| API Requests | `rate(dsp_http_requests_total[5m])` |
| Error Rate | `rate(dsp_http_errors_total[5m])` |
| Response Time | `dsp_api_latency_ms_last`, `dsp_api_latency_ms_avg` |
| Active Sessions / workload proxies | analysis/research/export request rates; auth & 429 rates |
| Background Jobs | `dsp_system_restarts_total` (+ future job gauges without engine changes) |

Provisioning files:

- `docker/grafana/dashboards/dsp-operations.json`
- `docker/grafana/provisioning/datasources/datasource.yml`
- `docker/grafana/provisioning/dashboards/dashboards.yml`

## Session note

JWT/session counts are not exposed as a dedicated Prometheus gauge in the frozen API contract. The dashboard uses operational proxies (auth failures, rate-limit events, analysis/research rates) until a future non-breaking metrics epic adds an explicit `dsp_active_sessions` gauge.

## Validation

1. `docker compose -f docker/docker-compose.production.yml up -d prometheus grafana`
2. Open Grafana → Dashboards → DSP → DSP Operations Dashboard
3. Confirm API `up==1` and latency panels populate after traffic
4. Confirm no analyse/business panels invent valuations or recommendations

## Non-negotiables

Dashboard queries are **observability only**. No analytical engines, recommendation, or API contract changes.
