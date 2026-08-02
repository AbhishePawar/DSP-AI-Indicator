# Deploy — Docker (EPIC-017)

Canonical multi-stage images and compose files live under [`docker/`](../../docker/). This directory provides **production entrypoints**, env separation, and secrets abstraction without duplicating Dockerfiles.

## Canonical artefacts (do not fork)

| Artefact | Path |
|---|---|
| API multi-stage Dockerfile | `docker/backend/Dockerfile` |
| Web multi-stage Dockerfile | `docker/frontend/Dockerfile` |
| Local / staging compose | `docker/docker-compose.yml` |
| Prod resource override | `docker/docker-compose.prod.yml` |
| Full production stack (+ observability) | `docker/docker-compose.production.yml` |
| TLS reverse proxy | `docker/Caddyfile` |

## Quick start

```bash
# From repo root
cp .env.production.example .env.production   # fill secrets — never commit
cp deploy/docker/env/staging.env.example .env.staging

# Full production stack (API, web, postgres, redis, prometheus, grafana, caddy)
./scripts/deploy_production.sh

# Or compose directly
docker compose --env-file .env.production -f docker/docker-compose.production.yml up -d --build
```

## Env separation

| File | Purpose |
|---|---|
| `.env.example` | Local developer defaults |
| `.env.staging` (from `deploy/docker/env/staging.env.example`) | Staging / pre-prod |
| `.env.production` (from `.env.production.example`) | Production — gitignored |
| `deploy/docker/secrets/.gitkeep` | Placeholder; real secrets via KMS / sealed-secrets / ExternalSecrets |

See [secrets.md](./secrets.md).

## Rolling deploy (Compose)

Compose recreates containers on image tag change. Prefer:

1. Build/push new tags (`DSP_IMAGE_TAG`, `DSP_IMAGE_TAG_WEB`).
2. `docker compose ... up -d` (recreates unhealthy → healthy via healthchecks).
3. Smoke: `python scripts/ops/production_smoke.py`.
4. On failure: `./scripts/rollback_production.sh`.

For Kubernetes rolling / blue-green / canary see `deploy/k8s/` and `docs/operations/Production_Deployment_Guide.md`.
