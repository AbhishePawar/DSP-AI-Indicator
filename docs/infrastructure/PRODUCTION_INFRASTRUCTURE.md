# Production Infrastructure (EPIC-011A)

| Field | Value |
|---|---|
| **Status** | Foundation implemented |
| **Epic** | EPIC-011A — Production Infrastructure Modernization |
| **Packages** | `production_platform` · `platform_runtime` · `api_platform` (bootstrap) |
| **Authority** | [INFRASTRUCTURE_ARCHITECTURE.md](../INFRASTRUCTURE_ARCHITECTURE.md) · [CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md) · PEP-002 / PEP-003 / PEP-004.1 |
| **Report** | [EPIC_011A_IMPLEMENTATION_REPORT.md](../reviews/EPIC_011A_IMPLEMENTATION_REPORT.md) |

---

## Architecture

Hexagonal **ports & adapters**. Business / research / valuation packages never import Postgres, Redis, or vendor SDKs.

```text
api_platform (HTTP)
    │  importlib bootstrap (boundary-safe)
    ▼
production_platform
    ├─ ProductionConfiguration / runtime validation
    ├─ InfrastructureBundle  ← composition root (adapter selection ONLY here)
    ├─ ProductionBundle      ← health / metrics / tracing / diagnostics
    └─ ObservabilityBundle   ← optional OTEL / Prometheus / JSON logs
            │
platform_runtime.EnterprisePlatform
    └─ infra + security + compliance (enterprise compose)
```

Investment engines, research APIs, and analytical contracts are **out of scope** and unchanged.

---

## Runtime dependencies

| Dependency | Required in production? | Adapter | Degradation |
|---|---|---|---|
| PostgreSQL | **Yes** | `PostgresDatabasePort` (`psycopg`) | Startup fails if unavailable |
| Redis | Optional (recommended) | Redis cache / rate / lock / session | Memory adapters when `DSP_REDIS_FALLBACK=true` (default) |
| Object storage | Optional | memory / local / S3-compatible | Memory default |
| OpenTelemetry | Optional | lazy SDK | In-memory tracing |
| Prometheus client | Optional | lazy SDK | Text renderer / in-memory metrics |

Extras: `pip install 'production-platform[infra]'` (postgres+redis+s3) and optionally `[observability]`.

---

## Persistence status

| Layer | Production adapter | Status |
|---|---|---|
| `production_platform.DatabasePort` | `PostgresDatabasePort` | **Wired** via `InfrastructureBundle.from_environment` / `build_runtime_infrastructure` |
| Security identity SQL repos | Uses `DatabasePort` | **Wired** when `SecurityBundle.create_with_infrastructure` is used |
| EPIC-A008 `persistence.StorageProviderPort` | `InMemoryStorageProvider` only | **Gap** — no Postgres storage provider; repository contracts unchanged |
| Research archive store | `InMemoryArchiveStore` | **Gap** — remains process-local |
| Workspace store | `InMemoryWorkspaceStore` | **Gap** — remains process-local |
| API report/context stores | Process-local | Intentional ephemeral |

**Rule:** replace only where production adapters already exist. Do not invent A008 Postgres storage in this epic.

---

## Caching / Redis

When `DSP_REDIS_URL` is set and the `redis` package can connect:

| Port | Redis adapter |
|---|---|
| `CachePort` | `RedisCachePort` (+ optional `FallbackCachePort` → memory) |
| `RateLimitPort` | `RedisRateLimitPort` (API middleware uses this when attached) |
| `LockPort` | `RedisLockPort` |
| `SessionPort` | `RedisSessionPort` |

If Redis is down and `DSP_REDIS_FALLBACK=true` (default): memory adapters; health reports `degraded` / `skip`, traffic continues.

If `DSP_REDIS_FALLBACK=false`: startup / readiness fails with `RedisUnavailableError`.

---

## Configuration

Load: `load_configuration_from_environ()` → `ProductionConfiguration`.

Validate: `validate_runtime_environment()` / `ConfigurationManager.validate()` / `build_runtime_infrastructure()`.

Application version: `resolve_application_version()` — `DSP_APP_VERSION` / `DSP_SERVICE_VERSION` → repo `VERSION` file → `1.0.0`.  
Package versions (e.g. `production_platform.__version__` = `0.3.0`) remain independent.

### Required runtime variables

| Variable | Profiles | Purpose |
|---|---|---|
| `DSP_ENVIRONMENT` | all | `development` \| `test` \| `staging` \| `production` |
| `DSP_REGION` | **production** | Non-`local` deploy region (e.g. `ap-south-1`) |
| `DSP_DATABASE_URL` | **production** | PostgreSQL DSN (`DATABASE_URL` alias accepted) |
| `DSP_JWT_SECRET` | production + security | Non-default JWT secret when security enabled |

### Recommended / optional

| Variable | Default | Purpose |
|---|---|---|
| `DSP_APP_VERSION` / `DSP_SERVICE_VERSION` | from `VERSION` | Service identity in health/meta |
| `DSP_SERVICE_NAME` | `dsp-ai-indicator` | Service name |
| `DSP_LOG_LEVEL` | `INFO` | Log level |
| `DSP_REDIS_URL` | unset → memory | Redis URL |
| `DSP_REDIS_FALLBACK` | `true` | Degrade if Redis unavailable |
| `DSP_REDIS_PREFIX` | `dsp` | Key prefix |
| `DSP_REDIS_TIMEOUT` | `2` | Connect timeout (seconds) |
| `DSP_DATABASE_POOL_SIZE` | `5` | Pool size (settings; adapter uses connect factory) |
| `DSP_DATABASE_TIMEOUT` | `5` | Connect timeout |
| `DSP_INFRA_OFFLINE` | unset | Force in-memory stack |
| `DSP_OBJECT_STORAGE_PROVIDER` | `memory` | `memory` \| `local` \| `s3` \| `minio` \| … |
| `DSP_JOB_QUEUE_BACKEND` | `memory` | Others reserved |
| `DSP_METRICS_ENABLED` | `true` | Metrics flag |
| `DSP_TRACING_ENABLED` | `true` | Tracing flag |
| `DSP_RATE_LIMIT_ENABLED` | unset | Enable API rate-limit middleware |
| `DSP_RATE_LIMIT_PER_MINUTE` | `600` | Per-client budget |
| `DSP_ENABLE_SECURITY` | unset | Wire `SecurityBundle` |
| `DSP_CORS_ORIGINS` | localhost:3000 | CORS allow list |
| `GIT_SHA` / `BUILD_TIMESTAMP` | `unknown` | Build metadata |
| `DSP_INDIA_*` / `DSP_CERT_IN_LOG_RETENTION_DAYS` | India defaults | CERT-In / residency posture |

Secrets: `DSP_SECRET_*` via `EnvSecretsPort` (values never logged).

---

## Health monitoring

| Endpoint | Role |
|---|---|
| `GET /health/live` | Liveness — process up |
| `GET /health/ready` | Readiness — platform + optional deps; includes `dependencies` block |
| `GET /health` | Aggregate platform + composition + **database/redis** checks |

Dependency status comes from `InfrastructureBundle.health_checks()` (DB ping, Redis posture, adapter names). Missing Redis is **not** fatal when fallback is enabled.

---

## Observability foundation

Optional (no external infra required):

- Structured / JSON logging ports
- In-memory or Prometheus text metrics
- In-memory or OpenTelemetry tracing (lazy)
- Correlation / request IDs

Enable vendor SDKs only via extras; composition never hard-requires them.

---

## Runtime validation & errors

| Type | When |
|---|---|
| `StartupError` | Strict env incomplete / composition failure |
| `ConfigurationError` | Invalid typed settings |
| `DatabaseUnavailableError` | Postgres required but missing |
| `RedisUnavailableError` | Redis required (`fallback=false`) but missing |
| `DependencyError` | Generic dependency failure |
| `ProviderError` | Adapter invocation failure |

HTTP surfaces must use `safe_public_message()` — never return DSNs, passwords, or stack traces.

---

## Deployment assumptions

- Compose/K8s provides Postgres (+ Redis recommended).
- API image installs `production-platform[infra]` for production.
- `DSP_ENVIRONMENT=production` with `DSP_REGION`, `DSP_DATABASE_URL`, strong `DSP_JWT_SECRET`.
- Health probes: `/health/live` (liveness), `/health/ready` (readiness).
- Multi-replica rate limiting needs Redis (or edge limiting); in-memory limiter is single-process.
- EPIC-A008 persistence remains in-memory until a dedicated storage adapter epic.

Offline / CI: `DSP_INFRA_OFFLINE=true` or omit DB/Redis URLs.

---

## Ops notes

1. Prefer `build_runtime_infrastructure()` / `ProductionBundle.from_environment()` / `EnterprisePlatform.from_environment()` over ad-hoc client construction.
2. Adapter selection is **only** in `InfrastructureBundle` (and enterprise compose that calls it).
3. Documented gaps (A008 persistence, archive, workspace) are intentional — do not silently swap storage under repository contracts.
4. Application version (`VERSION` / `DSP_APP_VERSION`) ≠ Python package versions (`0.3.0` platform packages).

---

## Related

- [ADAPTER_MATRIX.md](../ADAPTER_MATRIX.md)
- [INFRASTRUCTURE_MIGRATION_GUIDE.md](../INFRASTRUCTURE_MIGRATION_GUIDE.md)
- [PRODUCTION_CHECKLIST.md](../PRODUCTION_CHECKLIST.md)
- [docs/ops/BACKUP_AND_RECOVERY.md](../ops/BACKUP_AND_RECOVERY.md)
