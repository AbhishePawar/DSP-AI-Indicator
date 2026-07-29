# P7.0 — Production Deployment Guide

**Epic:** EPIC-P7.0 — Production Infrastructure & Public Launch  
**Backend:** `dsp_platform` **1.7.0**  
**Frontend:** `dsp-web` **2.0.0**  
**API contract label:** **`v1.0.0`** (behaviour frozen from `v1.0.0-rc1`)  
**Scope:** Deployment & operations only — **no** analytical engine changes.

---

## Infrastructure diagram

```text
                    Internet
                       |
              [ :80 / :443 ]
                       |
                 +-----+-----+
                 |   Caddy   |  Let's Encrypt TLS, HSTS, gzip,
                 |   proxy   |  security headers, access logs
                 +--+--+--+--+
                    |  |
           /api/v1  |  |  UI + /api/health
           /health  |  |
           /metrics |  |
                    v  v
              +-----+  +-----+
              | API |  | Web |
              |:8000|  |:3000|
              +--+--+  +-----+
                 |
        +--------+--------+
        |                 |
   +----+----+       +----+----+
   |Postgres |       |  Redis  |
   |  :5432  |       |  :6379  |
   +---------+       +---------+

   Prometheus  <-- scrape --  API /metrics + cAdvisor (+ Caddy admin metrics)
```

---

## Prerequisites

- Linux host (or Docker Desktop) with Docker + Compose v2
- DNS A/AAAA records for `DSP_PUBLIC_DOMAIN` (and optional `DSP_API_DOMAIN`) pointing to the host
- Ports **80** and **443** open for ACME HTTP-01 / HTTPS
- Secrets available (JWT, admin password, Postgres password)

---

## Environment setup

1. Copy template (never commit secrets):

```bash
cp .env.production.example .env.production
```

2. Fill at minimum:

- `DSP_JWT_SECRET` (≥24 chars, not a template)
- `DSP_SEED_ADMIN_PASSWORD`
- `POSTGRES_PASSWORD` / matching `DSP_DATABASE_URL`
- `DSP_PUBLIC_DOMAIN`, `DSP_ACME_EMAIL`
- `DSP_CORS_ORIGINS=https://<public-domain>`
- `NEXT_PUBLIC_API_BASE_URL=https://<public-domain>/api/v1`

3. Validate:

```bash
set -a; source .env.production; set +a
python scripts/validate_env.py production
```

`.env.production` is gitignored. Only `.env.production.example` is committed.

---

## SSL setup (Let's Encrypt via Caddy)

Caddy (`docker/Caddyfile`) obtains and renews certificates automatically when:

- `DSP_AUTO_HTTPS=on` (default)
- `DSP_PUBLIC_DOMAIN` is a publicly resolvable hostname
- Port 80 is reachable from the internet (ACME challenge)

Certificates persist in the `caddy_data` volume.

**Local dry-run:** use `localhost` domains; Caddy may use internal/local TLS. Full public ACME requires a real domain.

Edge headers include:

- `Strict-Transport-Security`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- gzip/zstd compression
- long-cache for `/_next/static/*`

---

## Deployment guide

```bash
chmod +x scripts/*.sh scripts/ops/*.sh
./scripts/deploy_production.sh
```

What it does:

1. Validates production env  
2. Records previous image tags for rollback  
3. Builds images (`dsp-api:1.7.0`, `dsp-web:2.0.0`)  
4. Starts `docker/docker-compose.production.yml`  
5. Waits for API `/health/ready` and Web `/api/health`  
6. Optionally smokes external HTTPS  

Compose file: `docker/docker-compose.production.yml`  
Services: `proxy`, `api`, `web`, `postgres`, `redis`, `prometheus`, `cadvisor`

---

## Backup

```bash
./scripts/backup_database.sh
```

Creates `backups/dsp_pg_<UTC>.sql.gz` + `.sha256`.  
RPO target: ≤24h (schedule daily cron). See also `docs/ops/BACKUP_AND_RECOVERY.md`.

---

## Restore

```bash
DSP_RESTORE_CONFIRM=YES ./scripts/restore_database.sh backups/dsp_pg_YYYYMMDDTHHMMSSZ.sql.gz
```

Destructive. Verify `/health/ready` and run smoke afterwards.

---

## Rollback

```bash
./scripts/rollback_production.sh 1.6.0 2.0.0-rc
# or rely on DSP_PREVIOUS_IMAGE_TAG / DSP_PREVIOUS_IMAGE_TAG_WEB
```

Redeploys previous API/Web image tags and re-checks health.

---

## Monitoring

| Signal | Source |
|---|---|
| API health | `GET /health`, `/health/live`, `/health/ready` |
| API metrics | `GET /metrics` (Prometheus text) |
| CPU / RAM (containers) | cAdvisor → Prometheus |
| Availability | Proxy + compose healthchecks + restart policies |
| Error rate / latency | API metrics + Caddy JSON access logs |

Prometheus config: `docker/prometheus.yml`  
Retention: 15 days (compose default)

---

## Logging

| Layer | Mechanism |
|---|---|
| API | Structured JSON access logs + `X-Request-Id` (`RequestContextMiddleware`) |
| Caddy | JSON access logs under `caddy_logs` volume with roll size 20MiB |
| Containers | Docker `json-file` driver, max 20m × 5 files |

---

## Migration validation

P7 does **not** change analytical schemas. Pre-deploy:

1. `python scripts/validate_env.py production`  
2. `docker compose -f docker/docker-compose.production.yml config`  
3. Postgres healthcheck green after start  
4. Optional: `pg_isready` inside the postgres container  

---

## Troubleshooting

| Symptom | Action |
|---|---|
| ACME / certificate failure | Check DNS, port 80, `DSP_ACME_EMAIL`, Caddy logs |
| API not ready | `docker compose ... logs api`; check DB URL / Redis |
| CORS errors | Align `DSP_CORS_ORIGINS` with HTTPS public origin |
| 502 from Caddy | Confirm api/web healthy; inspect proxy logs |
| Backup too small | Ensure postgres is up and credentials match |

---

## Security checklist

- [x] HTTPS via Caddy / Let's Encrypt  
- [x] HSTS (edge + Next defense-in-depth)  
- [x] Security headers (nosniff, frame deny, referrer, permissions)  
- [x] CSP (Next)  
- [x] Rate limiting (`DSP_RATE_LIMIT_ENABLED`)  
- [x] Admin auth required in production compose  
- [x] Secrets not committed (`.env.production` gitignored)  

Secure cookies remain the responsibility of the auth stack (`security_platform`) when issuing session cookies over HTTPS.
