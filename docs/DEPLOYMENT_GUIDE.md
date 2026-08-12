# Deployment Guide (RC1 Milestone 10)

## Production checklist

1. Run `python scripts/validate_env.py --profile production` (no placeholder JWT secrets).
2. Confirm `GET /health/live` and `GET /health/ready` return healthy.
3. Confirm `GET /ops/version` reports expected `git_sha` / channel.
4. Confirm Prometheus scrapes `/metrics` (or `/ops/metrics?format=prometheus`).
5. Confirm Grafana dashboards provisioned (ops + RC1 production-ops).
6. Confirm backups scheduled (`scripts/ops/backup_postgres.sh` or BackupPort adapter).
7. Confirm CORS (`DSP_CORS_ORIGINS`) and security headers (API middleware + Caddy).
8. Confirm rate limits enabled for public edges.
9. Roll out via Helm/Kustomize with rolling update; watch readiness probes.
10. Run `scripts/perf/rc1_m10_load_scenarios.py` against staging before cutover.

## Scaling guide

- Horizontal: scale API Deployment replicas; sticky sessions not required for JWT APIs.
- Redis/cache: configure `DSP_REDIS_URL` for shared cache / rate-limit backends.
- Workers: use existing job queue / background ports — do not invent a second queue.
- Autoscaling: HPA on CPU/memory + request rate (see Helm values).

## Docker

- Backend: `docker/backend/Dockerfile` (multi-stage, HEALTHCHECK → `/health/ready`)
- Frontend: `docker/frontend/Dockerfile`
- Compose: `docker/docker-compose.prod.yml`, `deploy/docker/compose.production.yml`

## Kubernetes

- Helm: `deploy/helm/dsp/`
- Kustomize: `deploy/k8s/base` + overlays
- Probes: liveness `/health/live`, readiness `/health/ready`
- Secrets: `deploy/k8s/base/secrets.example.yaml` — never commit live secrets

## Monitoring guide

- Prometheus scrape `/metrics`
- Grafana: System Health, API Usage, Errors (existing + RC1 panel)
- Ops UI: `/ops` (enterprise ops + ProductionOpsPanel)

## Backup & recovery

See [BACKUP_RECOVERY.md](BACKUP_RECOVERY.md).
