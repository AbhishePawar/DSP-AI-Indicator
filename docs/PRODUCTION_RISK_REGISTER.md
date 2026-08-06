# Production Risk Register — EPIC-P7.4

**Scope:** Operational / infrastructure risks for SaaS production.  
**Not in scope:** Investment advice, valuation model risk, or research content risk (see legal disclosures).

| ID | Description | Probability | Impact | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| OPS-01 | Single-region outage (AZ/region) | Medium | High | Document DR; backup off-host; future multi-AZ | Platform Ops | Open |
| OPS-02 | Postgres data loss / corruption | Low | Critical | Daily full + hourly incr dumps; sha256; restore drills | Platform Ops | Mitigated |
| OPS-03 | Alert fatigue / silent paging (placeholder webhooks) | High | High | Wire Alertmanager to PagerDuty/Slack before GA traffic | Platform Ops | Open |
| OPS-04 | Redis down breaks rate-limits / sessions | Medium | Medium | Exporter alerts; restart; rehydratable cache; Redis HA later | Platform Ops | Mitigated |
| OPS-05 | Disk fill (logs/backups) | Medium | High | Rotation policies; low-disk alert; retention cron | Platform Ops | Mitigated |
| OPS-06 | Certificate / ACME failure | Medium | High | Caddy monitoring; renew drills; DNS ownership checklist | Platform Ops | Open |
| OPS-07 | Secret leakage via env files | Medium | Critical | gitignore `.env.production`; secret manager CONDITION | Security | Open |
| OPS-08 | Multi-worker race without Redis-backed limits | Medium | High | Keep workers=1 until Redis limiter (P7.3) | Platform Ops | Mitigated |
| OPS-09 | Cold start / import latency (~13s façade) | Medium | Medium | Warm pools; avoid scale-to-zero for API | Platform Ops | Accepted |
| OPS-10 | cAdvisor privileged container risk | Low | Medium | Restrict host; prefer managed metrics later | Security | Accepted |
| OPS-11 | Grafana admin default password | High | High | Force `GRAFANA_ADMIN_PASSWORD` change in deploy checklist | Platform Ops | Open |
| OPS-12 | Incomplete restore drill evidence | Medium | High | Quarterly RTO clock on staging/prod-like | Platform Ops | Open |
| OPS-13 | Dependency CVE in base images | Medium | Medium | security.yml workflow; patch cadence | Security | Open |
| OPS-14 | Accidental analytical hotfix mid-incident | Low | Critical | Runbook forbids engine changes; rollback first | Engineering | Mitigated |
| OPS-15 | Support mailbox / status page gaps | Medium | Medium | P6.1 commercial conditions | Support | Open |

## Summary

| Status | Count |
|---|---|
| Mitigated | 5 |
| Accepted | 2 |
| Open | 8 |

Highest priority opens before unrestricted GA: **OPS-03**, **OPS-11**, **OPS-07**, **OPS-12**.
