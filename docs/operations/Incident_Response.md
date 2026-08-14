# Incident Response (EPIC-017)

## Severity

| Sev | Examples |
|---|---|
| SEV-1 | Total outage; confirmed data loss/corruption; widespread auth break |
| SEV-2 | Elevated 5xx / latency past SLO; Redis/DB flapping; deploy regression |
| SEV-3 | Single-tenant / secondary feature; non-critical exporter down |
| SEV-4 | Docs, dashboard polish |

## Roles

- **Incident Commander (IC):** Coordinates; owns timeline
- **Ops lead:** Deploy / infra / DB restore
- **Eng lead:** App diagnosis (no engine redesign mid-incident)
- **Comms:** Status updates to stakeholders

## Lifecycle

1. **Detect** — Alert, user report, smoke fail  
2. **Triage** — Sev, blast radius, recent changes  
3. **Mitigate** — Rollback, scale, feature flag, traffic shift  
4. **Recover** — Restore services; verify health/smoke  
5. **Follow-up** — Postmortem within 5 business days  

## Playbooks

### API unavailable {#api-unavailable}

1. `kubectl get pods -n dsp` / `docker compose ps`
2. Hit `/health/live` vs `/health/ready`
3. Check Postgres + Redis exporters
4. Review last deploy; `rollout undo` / `rollback_production.sh`
5. Scale API if CPU throttled and dependencies healthy

### High latency {#high-latency}

1. Grafana latency panels; identify route if labelled
2. Postgres: connections, long transactions
3. Redis: `PING` latency, eviction
4. Upstream market-data providers (honest timeouts — CV-001)
5. Do **not** optimise engines without evidence (EPIC-017 policy)

### Auth failures {#auth-failures}

1. Confirm `DSP_JWT_SECRET` unchanged across replicas
2. Cookie `Secure` / HTTPS terminator misconfig
3. CSRF token mismatch after domain change
4. Rate-limit false positives vs attack — check `dsp_rate_limit_violations_total`

### Database failure {#database-failure}

1. Failover managed primary if available
2. Else restore per [Disaster_Recovery.md](./Disaster_Recovery.md)
3. Keep API degraded responses honest (`Unable to calculate.` / unavailable) — no fabricated numbers

### Cache failure {#cache-failure}

1. If `DSP_REDIS_FALLBACK=true` (non-prod): memory fallback may mask issues  
2. Prod: restore Redis; expect session/rate-limit reset  
3. Do not disable security to "fix" cache

### Disk {#disk}

1. Identify volume (backups, logs, Postgres)
2. Purge aged backups beyond retention
3. Expand PVC / disk; restart if needed

### High error rate {#high-error-rate}

1. Correlate with deploy SHA / canary
2. Rollback if introduced by release
3. Check dependency health components in `/health`

## Communications template

```
INCIDENT: <title>
SEV: <1-4>
IMPACT: <who/what>
STATUS: Investigating | Mitigating | Monitoring | Resolved
NEXT UPDATE: <time>
```

## Postmortem (blameless)

- Timeline (UTC + IST)
- Contributing factors
- What went well / poorly
- Action items with owners (prefer ops packaging, tests, alerts)
- Explicit note if any CV/RS risk was involved
