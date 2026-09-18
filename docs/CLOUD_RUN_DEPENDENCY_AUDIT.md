# DSP-AI-Indicator Cloud Run Dependency Audit

**Audit mode:** Read-only dependency mapping; no infrastructure, production configuration, or application behavior was changed.
**Branch:** `v0/audit-repairs`
**Audit date:** 2026-09-18

## Scope and conclusion

The repository is not currently independent of Google Cloud Run. The direct production deployment path is Google Cloud Build building Docker images, pushing them to Google Artifact Registry, and deploying backend/frontend services to Cloud Run. The backend also uses Cloud SQL through a Cloud Run deployment flag and Google Secret Manager through Cloud Build secret mappings. The frontend receives a Cloud Run API URL as a build-time `NEXT_PUBLIC_API_BASE_URL` value.

Google OAuth is a separate optional application integration. It is not inherently a Cloud Run dependency, but its production secrets are currently mounted through Cloud Run/Secret Manager in the GCP deployment helper. Google Cloud SQL/Postgres is also a separate database dependency from Cloud Run itself; it must be re-provisioned or replaced before the backend can run independently.

No migration was performed in this audit. No Google Cloud resources were deleted, and `main` was not modified.

## Current architecture

```text
User
  -> Cloud Run frontend: dsp-ai-indicator-web (:3000)
  -> Cloud Run backend: dsp-ai-indicator (:8000, /api/v1)
  -> Cloud SQL PostgreSQL (Cloud Run --add-cloudsql-instances)
  -> Google Secret Manager secrets injected by Cloud Run
  -> Upstox / Resend / optional Google OAuth / other external services
```

Local development runs the same web/API split through `scripts/start-web.sh` and `scripts/start-api.sh`. CI/CD contains both independent Docker/Kubernetes/Helm definitions and the active Google Cloud Build deployment path.

## Dependency table

| File | Cloud Run/GCP Reference | Type | Runtime Impact | Replacement | Action |
|---|---|---|---|---|---|
| `cloudbuild.yaml:1-3` | Cloud Build builds API image, pushes to Artifact Registry, deploys Cloud Run | Direct Cloud Run + Cloud Build + Artifact Registry | Production deployment-critical | Independent image build/push and API deploy target, e.g. Kubernetes/Helm, VM, ECS, Fly.io, Render, or another container host | Replace in migration; do not delete yet |
| `cloudbuild.yaml:46-50` | `gcr.io/google.com/cloudsdktool/cloud-sdk`, `gcloud run deploy` | CI/CD only, direct Cloud Run | No local runtime impact; production deploy-critical | Target platform CLI/API or generic container deployment job | Replace workflow step |
| `cloudbuild.yaml:50-66` | Cloud Run env vars, Cloud Run URL in CORS, Secret Manager mappings | Deployment/runtime configuration | Backend runtime depends on supplied secrets and canonical origins | Target platform secret/env injection; independent API origin | Replace mappings and origins |
| `cloudbuild.yaml:66` | `--add-cloudsql-instances=...:dsp-postgres` | Cloud SQL attachment; GCP-specific runtime | Backend database connectivity is deployment-critical | Independent managed Postgres or self-hosted Postgres; standard `DATABASE_URL`/`DSP_DATABASE_URL` | Re-provision DB, then replace flag |
| `cloudbuild-frontend.yaml:1-3` | Cloud Build -> Artifact Registry -> Cloud Run frontend | Direct Cloud Run + Cloud Build + Artifact Registry | Frontend production deployment-critical | Independent frontend host or container deployment | Replace in migration |
| `cloudbuild-frontend.yaml:7-22` | `gcloud builds submit`, GCP project, `_API_BASE_URL` set to `run.app` | CI/CD/build-time; frontend API coupling | Build output embeds Cloud Run backend origin | Independent API DNS/URL supplied by host build environment | Replace substitution |
| `cloudbuild-frontend.yaml:30-32` | `gcr.io/cloud-builders/gcloud` | CI/CD only | No app runtime impact | Target CI runner or standard Docker tooling | Replace step image |
| `cloudbuild-frontend.yaml:103-110` | `gcloud run deploy`, `--allow-unauthenticated` | CI/CD only, direct Cloud Run | Frontend availability/deployment behavior | Target host deployment and access policy | Replace step |
| `scripts/deploy-google-email-auth.sh:2-43` | Cloud Shell helper, `gcloud builds submit`, Secret Manager, `gcloud run services update`, `run.app` URL | GCP-specific deployment script | Production deployment and optional Google OAuth wiring | New independent deployment script; use target platform secret store and API URL | Retire/replace after migration; preserve until cutover |
| `scripts/start-api.sh:8-10` | Comment says Cloud Run injects `PORT`; port fallback supports Cloud Run convention | Cloud Run-specific startup compatibility | Low; generic `PORT` support is portable and useful | Keep `PORT` support; remove Cloud Run-specific comment/assumption only if desired | Review, likely retain behavior |
| `tests/test_cloud_run_deployment_readiness.py:1-52` | Tests Cloud Run `PORT`, Cloud Build, region, Secret Manager wiring | Test-only / CI quality gate | Does not affect runtime, but enforces current deployment architecture | Replace with target deployment readiness tests | Rewrite when migration begins; do not change during audit |
| `packages/auth/src/auth/rate_limit.py:3-4` | Explains process-local rate-limit failure across Cloud Run instances | Documentation/comment; architectural rationale | Code itself uses shared persistence; no direct GCP call | Reword to multi-instance/container deployment generally | Optional cleanup after migration |
| `packages/auth/src/auth/otp_challenges.py:3-4` | Cloud Run-specific multi-instance rationale | Documentation/comment | No direct runtime provider dependency | Reword to horizontally scaled instances | Optional cleanup |
| `packages/auth/src/auth/oauth_challenges.py:3-4` | Cloud Run-specific persistence rationale | Documentation/comment | OAuth challenge persistence remains required independent of host | Reword to horizontally scaled deployment | Optional cleanup |
| `packages/auth/src/auth/mfa_pending.py:5-6` | Cloud Run instance A/B rationale | Documentation/comment | Shared store remains required for any multi-instance host | Reword generically | Optional cleanup |
| `packages/auth/src/auth/devices.py:166` | “shared across Cloud Run instances” | Documentation/comment | Persistence behavior is host-independent | Reword to shared application instances | Optional cleanup |
| `packages/auth/src/auth/device_store.py:3-4` | Cloud Run-specific persistence rationale | Documentation/comment | No direct GCP dependency | Reword generically | Optional cleanup |
| `packages/auth/src/auth/mfa.py:246` | JWT must verify across Cloud Run instances | Documentation/comment | Shared JWT secret remains required independent of host | Reword to horizontally scaled instances | Optional cleanup |
| `packages/auth/src/auth/lockout.py:4` | Cloud Run instance concurrency rationale | Documentation/comment | Atomic shared counter remains required | Reword generically | Optional cleanup |
| `packages/persistence/src/persistence/postgres_storage.py:1,51` | Shared storage across Cloud Run instances | Documentation/comment | Postgres requirement remains, provider does not | Reword generically | Optional cleanup |
| `packages/production_platform/src/production_platform/adapters/postgres.py:189` | Cloud Run failure wording | Documentation/comment | Driver/DSN behavior is host-independent | Reword generic deployment failure | Optional cleanup |
| `packages/production_platform/tests/test_postgres_required_production.py:3` | Cloud Run regression wording | Test documentation | Test behavior is provider-independent | Reword test description | Optional cleanup |
| `packages/api_platform/tests/test_production_auth_domain.py:13,42-45` | Hardcoded Cloud Run frontend origin and cloudbuild assertion | Test-only; current deployment contract | Enforces current Cloud Run URL/CORS contract | Replace with canonical independent frontend/API origins | Rewrite with migration |
| `.env.example:27` | Local API URL `127.0.0.1`, not Cloud Run | Local development | No GCP runtime dependency | Keep local URL; production should inject independent API origin | No migration required |
| `.env.example:75-77,122-124` | Google OAuth client variables and redirect settings | Optional Google OAuth application dependency | Only active when credentials/provider enabled | Keep if Google OAuth is required; use independent secret store and redirect origin | Separate decision; do not remove automatically |
| `.env.production.example` and deployment env templates | Production origins/secrets may be platform-neutral or GCP-specific depending on value | Configuration | Must be checked during cutover for `run.app` values | Independent hostnames and secret injection | Update only after target domains are chosen |
| `.github/workflows/docker.yml` | Docker build workflow; not inherently GCP | CI/CD container build | No Cloud Run dependency unless registry/deploy step added | Keep and point at independent registry/host | Distinguish from Cloud Build; no removal required |
| `deploy/k8s/**`, `deploy/helm/**` | Kubernetes/Helm deployment definitions | Independent alternative deployment path | Provides a viable non-Cloud-Run target, subject to validation | Use as target architecture or adapt to chosen platform | Inspect/validate during migration |

## Classification of Google-related dependencies

### A. Cloud Run dependencies

Direct Cloud Run dependencies found:

- `cloudbuild.yaml` deploys the backend with `gcloud run deploy`.
- `cloudbuild-frontend.yaml` deploys the frontend with `gcloud run deploy`.
- `scripts/deploy-google-email-auth.sh` updates a Cloud Run service and calls a Cloud Run `run.app` URL.
- `cloudbuild-frontend.yaml` bakes the backend `run.app` URL into the frontend.
- `cloudbuild.yaml` includes the frontend Cloud Run URL in `DSP_CORS_ORIGINS`.
- `scripts/start-api.sh` supports the Cloud Run-injected `PORT` convention, although the behavior is portable.
- Cloud Run-specific deployment readiness tests and architecture comments document multi-instance Cloud Run behavior.

### B. Other Google Cloud dependencies

These are not Cloud Run itself but are coupled to the current GCP deployment:

- **Cloud Build:** `cloudbuild.yaml`, `cloudbuild-frontend.yaml`, and `scripts/deploy-google-email-auth.sh` use Cloud Build and Google builder images.
- **Artifact Registry:** both Cloud Build manifests push images to `${_REGION}-docker.pkg.dev/...`.
- **Cloud SQL:** `cloudbuild.yaml` uses `--add-cloudsql-instances` for the production Postgres instance.
- **Secret Manager:** Cloud Build/Cloud Run secret mappings inject database, auth, Resend, Upstox, Gemini, and optional Google OAuth credentials.
- **Google service identity:** Cloud Build and Cloud Run necessarily require GCP service identities/permissions to build, push, deploy, attach Cloud SQL, and read secrets, even where an explicit service-account file is not committed.

No direct `GOOGLE_APPLICATION_CREDENTIALS` or committed service-account private key was found in the inspected source/configuration. GCP identity is implicit in the Cloud Build/Cloud Run execution environment.

### C. Google OAuth dependency

Google OAuth is an optional application authentication provider, distinct from Cloud Run:

- `DSP_GOOGLE_CLIENT_ID`, `DSP_GOOGLE_CLIENT_SECRET`, and OAuth redirect variables are declared in environment templates.
- Auth code supports provider status and callback flows independently of the hosting platform.
- The current GCP helper provisions Google OAuth secrets through Secret Manager and mounts them into Cloud Run, which is a deployment coupling rather than an OAuth protocol requirement.

Recommendation: retain Google OAuth only if product requirements need it. Move credentials to the replacement platform’s secret manager and update redirect URIs to the independent frontend/API domains.

### D. Google API dependency

No broad direct use of Google APIs or `google.cloud` SDK calls was found in the application runtime. The GCP-specific commands are deployment tooling (`gcloud`) and builder images. Gemini-related configuration appears as an AI credential mapping in Cloud Build; confirm provider usage before removing it, because Gemini may be a Google API dependency even when Cloud Run is removed.

### E. Unrelated Google functionality

The following should not be removed merely because Cloud Run is being removed:

- Optional Google OAuth provider code and configuration, if still product-required.
- Any Gemini/Google AI provider implementation that is actively used by the application.
- Generic `PORT` environment handling in `scripts/start-api.sh`; this is portable container behavior.
- Shared Postgres/session/rate-limit logic justified by horizontal scaling; it remains necessary on Kubernetes, VMs, and other independent hosts.

## Frontend API dependency

The frontend is not inherently Cloud Run-bound in local development: `.env.example` points to `http://127.0.0.1:8000/api/v1`. Production is Cloud Run-bound through `cloudbuild-frontend.yaml:_API_BASE_URL`, which is baked into `NEXT_PUBLIC_API_BASE_URL` during the Next.js image build. The replacement must provide an independent stable API origin, for example `https://api.dspaiindicator.com/api/v1`, and inject it at build time or use a runtime configuration endpoint.

The backend also currently names the canonical frontend and Cloud Run frontend origins in `DSP_FRONTEND_URL` and `DSP_CORS_ORIGINS`. These must be replaced together to avoid login redirects, OAuth callbacks, browser CORS failures, and webhook/origin mismatches.

## Backend dependencies

The backend container is broadly portable: it starts with Uvicorn, listens on a configurable host/port, and uses external persistence/providers. The non-portable production wiring is outside the application process:

- Cloud Run deployment command and port flag.
- Cloud SQL attachment flag and GCP-specific database instance.
- Secret Manager mappings for database/auth/provider credentials.
- Cloud Run-specific environment and origin values.

The replacement backend must preserve a shared Postgres database, shared auth secrets, provider credentials, health/readiness behavior, and horizontal-scaling-safe persistence.

## CI/CD dependencies

The active GCP CI/CD path is:

1. Cloud Build runs Docker builder images.
2. Images are pushed to Artifact Registry.
3. Cloud SDK runs `gcloud run deploy`.
4. Backend attaches Cloud SQL and reads Secret Manager values.
5. Frontend is built with a Cloud Run API URL and deployed to a second Cloud Run service.

The repository also contains GitHub Actions and Kubernetes/Helm definitions. Those are not automatically independent merely because they exist; each must be tested as the replacement pipeline. The migration should select one authoritative pipeline and disable the GCP deployment workflows only after the new path is proven.

## Files that must change during migration

- `cloudbuild.yaml` — replace or retire backend Cloud Build/Cloud Run deployment.
- `cloudbuild-frontend.yaml` — replace or retire frontend Cloud Build/Cloud Run deployment and `_API_BASE_URL`.
- `scripts/deploy-google-email-auth.sh` — replace with independent deployment and secret configuration.
- `.github/workflows/*` deployment workflow(s) — select and configure authoritative independent CI/CD.
- Production environment templates/configs containing `run.app`, Cloud SQL instance names, Secret Manager mappings, or GCP project identifiers.
- Frontend production API configuration/build arguments.
- CORS, frontend origin, OAuth redirect URI, and webhook configuration for the new domains.
- Cloud Run-specific readiness tests and test fixtures.
- Documentation and runbooks that instruct operators to use `gcloud`, Cloud Build, Cloud Run, Artifact Registry, Cloud SQL, or Secret Manager.

## Files that should not change in the first migration pass

- Core research/analysis domain logic.
- Provider-neutral API contracts.
- Auth/session persistence behavior, except for origin and secret injection configuration.
- Generic Dockerfiles, `scripts/start-api.sh` runtime behavior, and local development scripts unless a concrete portability defect is found.
- Kubernetes/Helm manifests until they are selected as the target and reviewed; they may be the migration destination.
- Google OAuth runtime code unless product explicitly removes Google OAuth.
- Google/Gemini API code unless a separate provider-removal decision is made.
- Google Cloud resources themselves; this audit intentionally performs no deletion.

## Risks of removing Cloud Run

- **High:** moving or replacing the Cloud SQL database without preserving data, SSL, pooling, migrations, and backup/restore procedures.
- **High:** changing API/frontend origins can break CORS, cookies, OAuth callbacks, webhooks, cached build-time URLs, and browser clients.
- **High:** losing Secret Manager mappings can cause startup failure or unsafe fallback behavior for auth/database/provider credentials.
- **High:** changing horizontal scaling semantics can reintroduce process-local state bugs in OTP, MFA, lockout, device trust, and rate limiting.
- **Medium:** replacing Cloud Build/Artifact Registry can change image provenance, SBOM/signing, caching, tag semantics, and rollback procedures.
- **Medium:** Kubernetes/Helm definitions may be incomplete or drift from the currently deployed Cloud Run configuration.
- **Medium:** health/readiness and graceful shutdown behavior may differ between Cloud Run and the target host.
- **Low/medium:** removing Cloud Run wording from tests/comments too early can erase useful regression context before equivalent target tests exist.

## Proposed independent architecture

```text
User
  -> Independent web host / CDN (custom frontend origin)
  -> Independent API server or Kubernetes service (custom API origin)
  -> Managed PostgreSQL outside GCP Cloud SQL, or independently hosted PostgreSQL
  -> Target platform secret manager / encrypted CI variables
  -> Existing external services: Upstox, Resend, optional Google OAuth, optional Gemini
```

A container-based target is recommended because the existing Dockerfiles and Kubernetes/Helm assets reduce application change. The target should provide:

- Separate web and API services or an equivalent reverse-proxy arrangement.
- Stable HTTPS web/API origins.
- Managed Postgres with pooling, backups, TLS, and migration support.
- Secret injection without committed credentials.
- Container health/readiness checks and graceful shutdown.
- CI image build, registry push, deployment, rollback, and provenance/SBOM checks.
- Explicit CORS, cookie, OAuth redirect, webhook, and API base URL configuration.

## Migration plan

1. **Freeze and inventory:** preserve the current GCP deployment and capture service revisions, image digests, database connection details, secrets inventory, domains, CORS, OAuth redirect URIs, webhooks, scheduled jobs, and rollback commands.
2. **Choose target:** select the independent web/API host and Postgres provider; decide whether existing Kubernetes/Helm is the target or another container platform.
3. **Provision parallel infrastructure:** create independent Postgres, secret storage, registry, web/API services, DNS/TLS, monitoring, backups, and restore verification.
4. **Port configuration:** replace Cloud Run URL/build substitutions, Cloud SQL attachment, Secret Manager mappings, GCP project/region settings, CORS origins, OAuth callbacks, and webhook URLs with target equivalents.
5. **Port CI/CD:** build/push/deploy the same Docker images through the target pipeline; retain immutable SHA tags, health checks, rollback, SBOM, and security gates.
6. **Validate in parallel:** run unit/integration tests, database migration/restore tests, authenticated auth flows, provider evidence, frontend/API smoke, browser checks, load/soak checks, and failure/rollback drills.
7. **Canary cutover:** route a controlled audience to the independent stack, compare health, latency, error rates, auth, data, and provider behavior.
8. **DNS cutover and observe:** switch production traffic only after the canary passes; retain GCP rollback capacity during the observation window.
9. **Decommission later:** after retention, rollback, backup, and compliance requirements are satisfied, separately remove Cloud Run, Cloud Build, Artifact Registry, Cloud SQL, Secret Manager, and service-account resources. This is explicitly outside this audit.

## Final finding

Cloud Run removal is feasible without a broad application rewrite, but it is not a documentation-only change. The minimum safe migration must replace the two Cloud Build manifests, GCP deployment helper, frontend build-time API origin, backend production secret/database wiring, origin configuration, CI/CD authority, and Cloud Run-specific readiness tests. Google OAuth and any Gemini/Google API usage should be assessed separately and retained unless independently removed by product decision.

No migration changes were made in this audit.
