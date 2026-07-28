# PEP-002 — Enterprise Infrastructure Foundation

| Field | Value |
|---|---|
| **Status** | **COMPLETE** |
| **Date** | 2026-07-28 |
| **Package** | `production_platform` **0.1.0 → 0.2.0** |
| **Authority** | [PEP_000](PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md) · [ADRs](PEP_ARCHITECTURE_DECISIONS.md) · [Dependency Rules](PEP_DEPENDENCY_RULES.md) |
| **Regression** | **2622 / 2622 PASS** (pytest) |

---

## 1. Executive Summary

PEP-002 introduces a production-grade infrastructure foundation **without changing business logic**. Investment engines, `/api/v1` contracts, and the thin client are untouched. All new capability is expressed as **ports**, **reference in-memory adapters**, optional **lazy vendor adapters**, and a single **composition root** (`InfrastructureBundle`).

Local/CI continue to run with zero external services. PostgreSQL and Redis are available for staging/production via optional extras and `docker compose --profile infra`.

---

## 2. Architecture Changes

| Before (K1.3) | After (PEP-002) |
|---|---|
| Cache/Storage/Scheduler/Secrets ports + memory | + Database, RateLimit, Lock, Session, Queue, BackgroundTask, Clock, RepositoryFactory, Configuration, MarketCalendar |
| No composition root for infra | `InfrastructureBundle.create_offline()` / `from_environment()` |
| No vendor adapters in-tree | Lazy Postgres / Redis / S3-compatible under `adapters/` |
| Flat config | Typed profiles: DB, Redis, object storage, jobs, India |

Clarification vs PEP-000 table: relational DB is owned by **`DatabasePort`**, not `StoragePort` (object blobs).

---

## 3. New Ports

`DatabasePort`, `TransactionPort`, `RepositoryFactoryPort`, `CacheInvalidationPort`, `RateLimiterPort` (alias `RateLimitPort`), `LockPort`, `SessionPort`, `QueuePort` (alias `JobQueuePort`), `BackgroundTaskPort`, `ConfigurationPort`, `SecretProviderPort` (alias `SecretsPort`), `ClockPort`, `MarketCalendarPort`.

---

## 4. New Adapters

**Reference:** `InMemoryDatabasePort`, `InMemoryRateLimitPort`, `InMemoryLockPort`, `InMemorySessionPort`, `InMemoryJobQueuePort`, `InMemoryBackgroundTaskPort`, `LocalFilesystemStoragePort`, `FallbackCachePort`, `PatternCacheInvalidation`, `EnvSecretsPort`, `StaticIndiaMarketCalendar`, `MigrationRunner`, `DefaultRepositoryFactory`.

**Vendor (lazy):** `PostgresDatabasePort`, `RedisCachePort` / `RedisRateLimitPort` / `RedisLockPort` / `RedisSessionPort`, `S3CompatibleStoragePort`.

---

## 5. Dependency Injection Changes

- **Only** `InfrastructureBundle` (and optional `ProductionBundle.create(..., infrastructure=…)`) may select vendors.
- `ProductionBundle.create()` remains backward compatible (no infra unless `with_infrastructure=True` or `infrastructure=` passed).
- Health gains optional `database` check when infra is attached.

---

## 6. Contract Tests Added

`packages/production_platform/tests/test_contracts.py` — cache, rate limit, lock, session, storage (memory+local), database+migrations, job queue retry/DLQ, background tasks, India calendar, fallback cache.

Architecture tests enforce: no static vendor imports; deps remain `core` only; version **0.2.0**.

---

## 7. Documentation Updated

| Doc | Role |
|---|---|
| [INFRASTRUCTURE_ARCHITECTURE.md](INFRASTRUCTURE_ARCHITECTURE.md) | Ports & adapters overview |
| [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) | Env profiles & variables |
| [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) | Offline + infra profile |
| [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) | India production skeleton |
| [ADAPTER_MATRIX.md](ADAPTER_MATRIX.md) | Adapter coverage matrix |
| [INFRASTRUCTURE_MIGRATION_GUIDE.md](INFRASTRUCTURE_MIGRATION_GUIDE.md) | Upgrade path from K1.3 |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Compose infra pointer |
| [VERSION_MATRIX.md](VERSION_MATRIX.md) | `production_platform` 0.2.0 |
| Package README | Unlocked for infra; extras documented |

---

## 8. Backward Compatibility

| Surface | Status |
|---|---|
| Investment engine math | Unchanged |
| `/api/v1` | Unchanged |
| Thin client | Unchanged |
| `ProductionBundle.create()` defaults | Compatible |
| Offline pytest | Compatible (memory adapters) |
| Package version | Semver minor bump 0.2.0 |

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Premature Postgres schemas in engines | Dependency rules + BC ownership in migration guide |
| Redis outage breaks API | `DSP_REDIS_FALLBACK=true` + `FallbackCachePort` |
| Job backends not wired | Explicit notes; memory queue until worker epic (ADR-PEP-0017) |
| In-memory SQL dialect limited | Production uses real Postgres; memory is contract/dev only |
| India holiday seed incomplete | Architecture port; licensed calendar in PEP-008 |

---

## 10. Final Assessment

| Criterion | Result |
|---|---|
| Ports-only dependency for business code | **PASS** |
| Contract tests for reference adapters | **PASS** |
| Vendor lock-in eliminated | **PASS** |
| Lazy imports | **PASS** |
| Local dev without external services | **PASS** |
| PostgreSQL/Redis available for production | **PASS** (optional extras + compose profile) |
| Existing APIs unchanged | **PASS** |
| Deterministic behaviour preserved | **PASS** |
| Full pytest suite | **2622 PASS** |

**Verdict:** PEP-002 Enterprise Infrastructure Foundation is **COMPLETE** and ready for dependent PEPs (001 Identity, 003 Observability, 005 Performance, 008 Data Platform India).

---

## Files Added

- `packages/production_platform/src/production_platform/production/{database,migrations,rate_limit,locking,session,job_queue,india,clock,repository,background,infrastructure}.py`
- `packages/production_platform/src/production_platform/adapters/{__init__,postgres,redis_stack,object_storage}.py`
- `packages/production_platform/tests/test_contracts.py`
- `docs/{INFRASTRUCTURE_ARCHITECTURE,CONFIGURATION_GUIDE,LOCAL_DEVELOPMENT,PRODUCTION_DEPLOYMENT,ADAPTER_MATRIX,INFRASTRUCTURE_MIGRATION_GUIDE,PEP_002_ENTERPRISE_INFRASTRUCTURE_FOUNDATION}.md`

## Files Modified

- `packages/production_platform` interfaces, cache, storage, configuration, bundle, diagnostics, `__init__`, `pyproject.toml`, README, tests
- `docker/docker-compose.yml` (infra profile)
- `docs/VERSION_MATRIX.md`, `DEPLOYMENT_GUIDE.md`, `PEP_ARCHITECTURE_DECISIONS.md`
