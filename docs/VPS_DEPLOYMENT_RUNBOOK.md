# VPS deployment runbook

## Target architecture

```text
Browser → Caddy (HTTPS) → Next.js web
                     └──→ FastAPI (/api/v1) → Neon PostgreSQL (TLS)
```

- Deployment entrypoint: `scripts/deploy_production.sh`
- Compose profile: `docker/docker-compose.vps.yml`
- Database: external Neon PostgreSQL via `DSP_DATABASE_URL`; no local PostgreSQL container.
- Redis: intentionally not started in the initial VPS profile. The app uses its configured fallback adapters when Redis is unset; these may be process-local and can reset after a restart. Treat this as a known limitation until a durable Redis service is explicitly approved.
- Object storage: local persistent Docker volume; no S3/GCS/Azure service is required by this profile.
- AI providers: Gemini and OpenAI direct server-side APIs. Keep their keys out of `NEXT_PUBLIC_*` variables.
- This profile does not require Vercel, Vercel AI Gateway, or Google Cloud deployment services. Existing Google-hosted production and DNS should remain untouched until the VPS passes acceptance.

## 1. VPS prerequisites

1. Install a supported Docker Engine and Docker Compose v2.
2. Ensure the VPS has enough RAM/CPU headroom for the API (Compose limit 2 CPU / 2 GB), web (1 CPU / 1 GB), Caddy, Docker and the operating system.
3. Allow inbound TCP 80 and 443. Restrict SSH to trusted IPs; do not expose PostgreSQL or Redis ports.
4. Point the intended application hostname's DNS A/AAAA record to the VPS only when ready for acceptance testing. Keep the existing production DNS unchanged before that point.

## 2. Prepare Neon

1. Create a production database/project in the intended region.
2. Copy its PostgreSQL connection string and URL-encode any special characters in the username/password.
3. Use TLS, for example `sslmode=require`. Never commit the real connection string.
4. Confirm the VPS can reach the Neon hostname over outbound TCP 5432.

## 3. Configure secrets

From the repository root on the VPS:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Edit `.env.production` and replace every placeholder, including:

- `DSP_PUBLIC_DOMAIN`: real hostname only (no scheme).
- `DSP_ACME_EMAIL`: monitored email for certificate expiry/ACME notices.
- `DSP_DATABASE_URL`: real Neon URL with TLS.
- `DSP_JWT_SECRET`: strong random value, at least 32 characters.
- `DSP_SEED_ADMIN_PASSWORD`: unique strong password.
- `OPENAI_API_KEY_5` and/or `GEMINI_API_KEY`: valid server-side provider keys.
- `DSP_CORS_ORIGINS`: exact HTTPS origin(s), no wildcard.
- `DSP_IMAGE_TAG` and `DSP_IMAGE_TAG_WEB`: unique immutable release tags.

Keep `DSP_REDIS_URL` empty and `DSP_REDIS_FALLBACK=true` for the agreed no-Redis initial profile. The resulting fallback is a deliberate limitation, not equivalent to durable shared Redis state.

For the first install, previous image tags may be empty. Before every upgrade, set `DSP_PREVIOUS_IMAGE_TAG` and `DSP_PREVIOUS_IMAGE_TAG_WEB` to the known-good tags currently deployed; use new tags for the incoming build.

## 4. Validate and deploy

```bash
python scripts/validate_env.py production
docker compose --env-file .env.production -f docker/docker-compose.vps.yml config --quiet
bash -n scripts/deploy_production.sh scripts/rollback_production.sh
./scripts/deploy_production.sh
```

The deploy script builds the API/web images, starts Caddy/API/web, fails if either service does not become healthy, checks API health/metrics, and performs an HTTPS smoke check when required. It must not be reported as successful unless the command exits with code 0.

## 5. Acceptance checks

```bash
curl -fsS "https://$DSP_PUBLIC_DOMAIN/health/ready"
curl -fsS "https://$DSP_PUBLIC_DOMAIN/api/health"
```

Also verify manually:

- Login/session restore and logout.
- Google OAuth callback if configured; preserve the exact deployed hostname and callback URI.
- A company analysis request using the ticker-only client contract.
- Direct Gemini and OpenAI provider calls from the backend, without exposing keys in browser requests or build output.
- Data-source availability and truthful unavailable-data messaging.
- Database backup and a restore drill using the existing backup/restore scripts.
- Caddy certificate issuance and renewal.
- Logs contain no credentials or raw provider keys.

## 6. Rollback

For an existing deployment, supply the known-good image tags recorded before the upgrade:

```bash
./scripts/rollback_production.sh <previous-api-tag> <previous-web-tag>
```

Verify API and web health after rollback. Do not switch DNS or decommission the old deployment until acceptance checks pass and a backup/restore drill is successful.

## Release blockers

- A real Neon URL and real public hostname are mandatory; the checked-in template intentionally fails production validation.
- Do not bypass failed frontend tests or security checks to force a release.
- The GitHub merge is not a VPS deployment. Run this procedure on the VPS and retain the command output as the deployment record.
