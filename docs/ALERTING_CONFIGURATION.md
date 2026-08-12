# Alerting Configuration — EPIC-P7.4

**Files:** `docker/prometheus/alerts.yml` · `docker/alertmanager.yml` · `docker/prometheus.yml`

## Alert catalogue

| Alert | Condition | Severity | Primary runbook |
|---|---|---|---|
| `DspApiUnavailable` | `up{job="dsp-api"}==0` for 2m | critical | OPERATIONS_RUNBOOK § API unavailable |
| `DspHighLatency` | last >2s or avg >1.5s for 5m | warning | § High latency |
| `DspHighErrorRate` | error ratio >5% over 5m | critical | § High error rate |
| `DspDatabaseUnavailable` | `pg_up==0` or absent for 2m | critical | § Database failure |
| `DspRedisUnavailable` | `redis_up==0` or absent for 2m | critical | § Cache failure |
| `DspLowDiskSpace` | FS free <15% or container FS >85% for 15m | critical | § Low disk |
| `DspHighCpu` | container CPU >85% for 10m | warning | § High CPU |
| `DspHighMemory` | working set >90% limit for 10m | warning | § High memory |

## Routing

Alertmanager groups by `alertname`, `service`, `severity`.

| Receiver | Use |
|---|---|
| `dsp-ops-default` | warnings + general |
| `dsp-ops-critical` | critical (continues after default route) |

**CONDITION:** replace placeholder webhook URLs in `docker/alertmanager.yml` with Slack / PagerDuty / Opsgenie endpoints from the secret manager before live paging.

## Validation checklist

- [ ] Prometheus loads `rule_files: /etc/prometheus/alerts.yml` without config errors
- [ ] Alertmanager UI shows configured receivers
- [ ] Force-test: stop API briefly → `DspApiUnavailable` fires → restore → resolves
- [ ] Critical path pages on-call (after webhook wiring)

## Non-negotiables

Thresholds are operational. Do not encode valuation/recommendation logic into alert expressions.
