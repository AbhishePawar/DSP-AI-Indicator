# Phase K1.3 — Production Services

**Status:** Implemented · Provider-neutral · No business logic  

**Package:** `packages/production_platform/` **0.1.0**  
**Depends on:** `core` only  
**Suite gate:** Regression suite green at implementation

This phase adds the **Production Services** layer — operational capabilities
for deployment (logging, metrics, tracing, health, configuration, feature
flags, cache / storage / scheduler abstractions) while remaining independent
of business logic, HTTP routing, and authentication.

---

## 1. Architecture

```text
Website / Mobile
        │
REST API + Authentication
        │
API Platform
        │
DSP Platform
        │
Production Services   ← production_platform (K1.3)
  LoggingPort · MetricsPort · TracingPort
  CachePort · StoragePort · SchedulerPort · SecretsPort
  ConfigurationManager · FeatureFlagManager
  HealthManager · DiagnosticsManager
  ProductionBundle
        │
────────────────────────────────
Frozen business bounded contexts
```

`ProductionBundle` is the composition root. Concrete vendor adapters are
**external** and injected via ports.

---

## 2. Ports (provider-neutral)

| Port | Responsibility | Default adapter |
|---|---|---|
| `LoggingPort` | Structured logs + correlation ids | `InMemoryLoggingPort` / `StdlibLoggingPort` |
| `MetricsPort` | Counters / gauges / timings | `InMemoryMetricsPort` |
| `TracingPort` | Spans / annotations | `InMemoryTracingPort` |
| `CachePort` | Key/value TTL cache | `InMemoryCachePort` |
| `StoragePort` | Opaque blob put/get/delete | `InMemoryStoragePort` |
| `SchedulerPort` | Job schedule / cancel | `InMemorySchedulerPort` |
| `SecretsPort` | Secret lookup | `InMemorySecretsPort` |

**Forbidden direct deps:** Redis · Prometheus · OpenTelemetry · S3 · Azure Blob ·
GCS · Celery · RQ.

---

## 3. Managers & public API

| Type | Role |
|---|---|
| `ConfigurationManager` | Environment + settings + secrets port |
| `FeatureFlagManager` | Named boolean flags |
| `HealthManager` | Liveness / readiness / health aggregation |
| `DiagnosticsManager` | Immutable diagnostics snapshot |
| `ProductionBundle` | Operational façade |

### `ProductionBundle` methods

`health()` · `readiness()` · `liveness()` · `diagnostics()` ·
`get_configuration()` · `get_feature_flags()` · `get_metrics()` ·
`get_metadata()`

---

## 4. Dependency diagram

```text
production_platform ──depends──► core
adapters (future) ──implement──► Ports
api_platform / deploy ──may compose──► ProductionBundle
dsp_platform / domains ──✕──► production vendors
production_platform ──✕──► Redis / OTel / S3 / Celery / …
```

---

## 5. Provider-neutral philosophy

1. Define **Ports** (Protocols) in-domain.  
2. Ship **in-memory / stdlib** defaults for tests and local boot.  
3. Inject **adapters** at composition time for production.  
4. Never import vendor SDKs into `production_platform`.  
5. Never place financial / recommendation / workflow logic here.

---

## 6. Extension strategy

| Extension | Pattern |
|---|---|
| Redis cache | Adapter implementing `CachePort` |
| Prometheus / OTel | Adapters for `MetricsPort` / `TracingPort` |
| S3 / Azure / GCS | Adapter implementing `StoragePort` |
| Celery / cloud schedulers | Adapter implementing `SchedulerPort` |
| Vault / KMS | Adapter implementing `SecretsPort` |
| **K1.4 Platform Freeze** | **DONE** · see [K1.4](K1_4_PLATFORM_FREEZE.md) |

---

## 7. Non-goals

No financial calculations · no recommendation logic · no workflow
implementation · no HTTP routing · no authentication · no durable persistence
implementation (in-memory defaults only).

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | K1.3 Production Services |
| [K1_2_AUTHENTICATION_SECURITY.md](K1_2_AUTHENTICATION_SECURITY.md) | Security |
| [K1_1_API_PLATFORM.md](K1_1_API_PLATFORM.md) | API |
| [K1_0_PLATFORM_INTEGRATION.md](K1_0_PLATFORM_INTEGRATION.md) | DSP Platform |

---

## Final question

Are Production Services complete, stable, provider-neutral, and ready for
Platform Freeze (K1.4)?

Answered in the phase RETURN.
