# Operations Runbook — EPIC-P7.4

Master index for production operations. Deep-dives remain under `docs/ops/runbooks/`.

**Versions:** `dsp_platform 1.7.4` · `dsp-web 2.0.4` · API `v1.0.0`

---

## Deployment

1. Fill `.env.production` from `.env.production.example` (never commit secrets).
2. `python scripts/validate_env.py --profile production`
3. `./scripts/deploy_production.sh`
4. Confirm Grafana **DSP Operations Dashboard** green; `/health/ready` 200.
5. `python scripts/ops/production_smoke.py`

Detail: [DEPLOYMENT.md](./ops/runbooks/DEPLOYMENT.md) · [P7_PRODUCTION_DEPLOYMENT.md](./P7_PRODUCTION_DEPLOYMENT.md)

---

## Rollback

```bash
export DSP_PREVIOUS_IMAGE_TAG=1.7.3
export DSP_PREVIOUS_IMAGE_TAG_WEB=2.0.3
./scripts/rollback_production.sh
```

Verify health + smoke. Do **not** change analytical code mid-incident.

Detail: [ROLLBACK.md](./ops/runbooks/ROLLBACK.md)

---

## Incident Response

Detect → Acknowledge → Triage → Contain → Mitigate → Communicate → Resolve → Postmortem.

Severity S1–S4 per commercial support doc. Capture request IDs (`X-Request-Id`), never research payloads.

Detail: [INCIDENT_RESPONSE.md](./ops/runbooks/INCIDENT_RESPONSE.md)

---

## Security Incident

Isolate → Preserve evidence → Rotate secrets → Notify → Remediate → Postmortem.

Detail: [SECURITY_INCIDENT.md](./ops/runbooks/SECURITY_INCIDENT.md)

---

## Database Failure {#database-failure}

1. Confirm `DspDatabaseUnavailable` / `pg_up`.
2. Check postgres container logs; disk space; credentials.
3. If corrupt: restore per [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md).
4. Validate with `validate_recovery.py`.

---

## Cache Failure {#cache-failure}

1. Confirm Redis exporter / `redis_up`.
2. Restart Redis; if AOF corrupt, restore empty cache (safe — cache is rehydratable).
3. If `DSP_REDIS_FALLBACK=true`, confirm degraded mode documented; prefer restoring Redis for rate-limits.

---

## Service Restart {#service-restart}

```bash
docker compose -f docker/docker-compose.production.yml restart api
# or: web | postgres | redis | proxy | prometheus | grafana
```

Wait for healthchecks; watch Grafana latency/error panels.

---

## Planned Maintenance

1. Announce window; set status.
2. Take fresh full backup.
3. Drain / maintenance page if available.
4. Apply change (compose up / image pull).
5. Validate recovery + smoke.
6. Clear status; note duration.

---

## Alert playbooks (quick)

### API unavailable {#api-unavailable}

Check `api` container, Caddy upstream, `/health/live`. Restart API; rollback if deploy-related.

### High latency {#high-latency}

Check CPU/memory panels, DB locks, rate limits. Scale vertically first; do not multi-worker without Redis-backed limits (P7.3 condition).

### High error rate {#high-error-rate}

Correlate `/metrics` error counters with logs by `request_id`. Prefer rollback over hot analytical patches.

### Low disk {#low-disk}

Purge old backups/logs per retention; expand volume; never delete unverified sole backups.

### High CPU / High memory {#high-cpu} {#high-memory}

Identify hot container via cAdvisor; restart if leak suspected; capture memory snapshot script output for ops ticket.

---

## Related runbooks

| Topic | Path |
|---|---|
| Service outage | `docs/ops/runbooks/SERVICE_OUTAGE.md` |
| Backup/recovery | `docs/ops/runbooks/BACKUP_RECOVERY.md` |
| Alerting | `docs/ALERTING_CONFIGURATION.md` |
| Logging | `docs/LOGGING_REPORT.md` |
