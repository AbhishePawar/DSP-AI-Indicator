# Production Runbook (EPIC-017)

Day-2 operations for DSP AI Indicator. Complements `docs/ops/RC1_OPS_HANDBOOK.md`.

## Production checklist (pre-change)

- [ ] Change ticket / maintenance window recorded
- [ ] Target env confirmed (staging vs production)
- [ ] Secrets present and not expired
- [ ] Previous image tags recorded (`.dsp_production_previous_tags` or registry)
- [ ] Backup taken if DB-touching (`scripts/ops/backup_postgres.sh`)
- [ ] Feature flags / closed-beta posture reviewed
- [ ] On-call notified

## Go-live

1. Validate env: `python scripts/validate_env.py production`
2. Deploy: `./scripts/deploy_production.sh` **or** `kubectl/helm` per Deployment Guide
3. Wait for Ready probes
4. Smoke: `python scripts/ops/production_smoke.py`
5. Watch Grafana 15–30 minutes (error rate, latency, Redis/Postgres up)
6. Mark change complete; link deploy SHA

## Maintenance

| Task | Cadence | Command / notes |
|---|---|---|
| Postgres logical backup | Daily | `scripts/ops/backup_postgres.sh` |
| Backup integrity | Weekly | Verify `.sha256`; restore to staging |
| Certificate renewal | Auto (Caddy/cert-manager) | Alert on expiry <14d |
| Dependency / image scan | Weekly / on release | `trivy`, `pip-audit`, `npm audit` |
| Disk / volume | Daily alert | Alert `DspDiskPressure` |
| Secret rotation | Quarterly or incident | See `deploy/docker/secrets.md` |

## Upgrade

1. Deploy to **staging** with new tags; run smoke + synthetic load.
2. Confirm analytical outputs unchanged (golden sample tickers).
3. Production: rolling / blue-green / canary per risk.
4. Keep previous tags for ≥72h.

```bash
# Compose image bump
# edit .env.production DSP_IMAGE_TAG / DSP_IMAGE_TAG_WEB
./scripts/deploy_production.sh
```

```bash
# Helm
helm upgrade dsp deploy/helm/dsp -f deploy/helm/dsp/values-production.yaml \
  --set api.image.tag=2.0.1 --set web.image.tag=2.0.1
```

## Rollback

**Compose:**

```bash
./scripts/rollback_production.sh
```

**Kubernetes:**

```bash
kubectl -n dsp rollout undo deployment/dsp-api
kubectl -n dsp rollout undo deployment/dsp-web
# or flip blue-green selector; or helm rollback dsp
```

Verify smoke + health after rollback. Escalate if DB migration was applied — EPIC-017 does not introduce schema redesign; if a future migration exists, restore from backup per DR guide.

## Incident playbook (summary)

| Symptom | First actions |
|---|---|
| API 5xx spike | Check `/health/ready`, Postgres, Redis; scale API; recent deploy? |
| Auth failures | JWT secret mismatch? Cookie Secure behind HTTP? CSRF? |
| High latency | DB slow queries, Redis ping, CPU throttling, upstream providers |
| Web down / API up | Web pods / Ingress path; CDN |
| Disk full | Purge old backups/logs; expand volume |

Full procedures: [Incident_Response.md](./Incident_Response.md).

## On-call guide

### Priority

| Sev | Definition | Response |
|---|---|---|
| SEV-1 | Platform unavailable or data integrity risk | Page immediately; war room |
| SEV-2 | Major degradation (latency/errors >SLO) | 15m ack |
| SEV-3 | Partial feature / single region | Business hours |
| SEV-4 | Cosmetic / docs | Backlog |

### Tooling

- Grafana: production health dashboard (`dsp-epic017-health`)
- Prometheus alerts → Alertmanager
- Logs: JSON with `correlation_id` / `request_id`
- Smoke: `scripts/ops/production_smoke.py`
- Certify offline: `python scripts/ops/certify_p7.py` (packaging)

### Handoff

Record: timeline, impact, customer-facing status, commits/tags, next actions.

## Contacts / ownership

Maintain a living roster outside git (PagerDuty / Opsgenie). Platform ops owns deploy artefacts; product eng owns engine regressions (out of EPIC-017 scope).
