# Production Deployment Guide (EPIC-017)

**Status:** Production-deployable readiness improved (ops packaging).  
**Not claimed:** Commercial GA APPROVED.  
**Architecture freeze:** No valuation, REP-002, Buffett, Research Intelligence/OS, or Enterprise API behaviour changes.

## 1. Topology

```
Internet → TLS terminator (Caddy / Ingress)
              ├─ dsp-web (Next.js thin client)
              └─ dsp-api (/api/v1, /health/*, /metrics)
                     ├─ PostgreSQL (durable identity/enterprise state)
                     └─ Redis (cache, sessions, rate limits, locks, queues)
Observability → Prometheus → Grafana / Alertmanager
Optional       → OTel Collector → Prometheus / logs
```

## 2. Artefacts

| Layer | Path |
|---|---|
| Multi-stage Dockerfiles | `docker/backend/Dockerfile`, `docker/frontend/Dockerfile` |
| Compose (full prod + observability) | `docker/docker-compose.production.yml` |
| Compose deploy wrapper | `deploy/docker/compose.production.yml` |
| Kubernetes base + overlays | `deploy/k8s/` |
| Helm chart | `deploy/helm/dsp/` |
| Env templates | `.env.production.example`, `deploy/docker/env/staging.env.example` |
| Deploy script | `scripts/deploy_production.sh` |
| Rollback script | `scripts/rollback_production.sh` |

## 3. Environment separation

| Env | Config | Secrets |
|---|---|---|
| Local | `.env` / compose base | Dev defaults |
| Staging | `.env.staging` | Staging vault |
| Production | `.env.production` (gitignored) | KMS / Secrets Manager |

Non-secret knobs → ConfigMap (`deploy/k8s/base/configmap.yaml`).  
Secrets → Secret / ExternalSecrets (`deploy/docker/secrets.md`).

## 4. Docker Compose go-live

```bash
cp .env.production.example .env.production
# fill DSP_JWT_SECRET, POSTGRES_PASSWORD, DSP_CORS_ORIGINS, domains…

python scripts/validate_env.py production
./scripts/deploy_production.sh

DSP_SMOKE_API_BASE_URL=https://$DSP_PUBLIC_DOMAIN \
DSP_SMOKE_WEB_BASE_URL=https://$DSP_PUBLIC_DOMAIN \
python scripts/ops/production_smoke.py
```

Optional OTel:

```bash
docker compose --env-file .env.production \
  -f docker/docker-compose.production.yml \
  -f deploy/observability/compose.otel.override.yml up -d
```

## 5. Kubernetes go-live

```bash
# 1) Create namespace + vault-synced Secret dsp-secrets
kubectl apply -k deploy/k8s/overlays/staging   # validate first
kubectl apply -k deploy/k8s/overlays/production

# Helm alternative
helm upgrade --install dsp deploy/helm/dsp \
  -f deploy/helm/dsp/values-production.yaml \
  --set existingSecret=dsp-secrets
```

Rolling strategy: `maxUnavailable: 0`, `maxSurge: 1` with readiness on `/health/ready` and `/api/health`.

## 6. Blue-Green & Canary

### Rolling (default)

Image tag bump → Deployment rollout → readiness gates traffic.

### Blue-Green

See `deploy/k8s/overlays/blue-green/README.md`. Switch Service selector after green smoke.

### Canary

`deploy/k8s/overlays/canary/` deploys `dsp-api-canary`. Route 5–10% via Ingress canary annotations or mesh weight; promote on SLO green; abort by deleting canary Deployment.

## 7. Database (no schema redesign)

- Migrations / rollback / seed / backup / restore / PITR: `docs/operations/Disaster_Recovery.md` and `docs/ops/BACKUP_AND_RECOVERY.md`
- Scripts: `scripts/ops/backup_postgres.sh`, `scripts/ops/restore_postgres.sh`, `scripts/ops/validate_recovery.py`
- Prefer managed Postgres with continuous WAL archiving for PITR

## 8. Redis & queues (EPIC-011A ports)

Ports in `production_platform.production.interfaces`:

| Port | Production role |
|---|---|
| `CachePort` | Distributed cache |
| `SessionPort` | Session store |
| `RateLimitPort` / `RateLimiterPort` | API rate limits |
| `JobQueuePort` / `QueuePort` | Background jobs + DLQ/retry abstraction |
| `LockPort` | Distributed locks |

Wire via `DSP_REDIS_URL`. Set `DSP_REDIS_FALLBACK=false` in production. In-memory adapters remain for local/dev only.

## 9. Post-deploy verification

1. `/health/live` → 200  
2. `/health/ready` → 200 (or intentional 503 with honest component status)  
3. `/metrics` scrapable  
4. `production_smoke.py` PASS  
5. Grafana "DSP Production Health" panels populated  
6. Spot-check research analyse output identical to pre-deploy baseline (no engine changes expected)

## 10. Related docs

- [Production_Runbook.md](./Production_Runbook.md)
- [Monitoring_Guide.md](./Monitoring_Guide.md)
- [Disaster_Recovery.md](./Disaster_Recovery.md)
- [Incident_Response.md](./Incident_Response.md)
