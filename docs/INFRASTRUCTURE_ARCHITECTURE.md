# Infrastructure Architecture (PEP-002)

| Field | Value |
|---|---|
| **Status** | Implemented (foundation) |
| **Package** | `production_platform` **0.2.0** |
| **Authority** | [PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md](PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md) |
| **Report** | [PEP_002_ENTERPRISE_INFRASTRUCTURE_FOUNDATION.md](PEP_002_ENTERPRISE_INFRASTRUCTURE_FOUNDATION.md) |

---

## Design

Hexagonal **Ports & Adapters**:

```text
Business / API / Security
        │  depend only on ports
        ▼
production_platform.interfaces  (DatabasePort, CachePort, …)
        │
        ├─ reference adapters (in-memory) — CI / local / deterministic
        └─ vendor adapters (lazy) — Postgres / Redis / S3-compatible
                ▲
                │ selected ONLY by InfrastructureBundle composition root
```

Investment engines **never** import adapters or vendor SDKs.

---

## Ports

| Port | Purpose |
|---|---|
| `DatabasePort` / `TransactionPort` | SQL system of record |
| `RepositoryFactoryPort` | BC-owned persistence factories |
| `CachePort` / `CacheInvalidationPort` | Distributed or local cache |
| `RateLimiterPort` | Rate limiting |
| `LockPort` | Distributed locks |
| `SessionPort` | Session blob store |
| `StoragePort` | Object / blob storage |
| `QueuePort` (`JobQueuePort`) | Background jobs + DLQ |
| `BackgroundTaskPort` | Task submission façade |
| `ConfigurationPort` | Typed config access |
| `SecretProviderPort` | Secrets (env today; AWS/Azure/Vault later) |
| `ClockPort` | Injectable time |
| `MarketCalendarPort` | India NSE/BSE calendar (seed) |

---

## Adapters

| Capability | Reference | Production (optional extras) |
|---|---|---|
| Database | `InMemoryDatabasePort` | `PostgresDatabasePort` (`[postgres]`) |
| Cache / rate / lock / session | In-memory | Redis stack (`[redis]`) |
| Object storage | Memory / local FS | S3-compatible / MinIO (`[s3]`) |
| Secrets | In-memory / `EnvSecretsPort` | Future KMS adapters |
| Jobs | `InMemoryJobQueuePort` | Redis Streams / SQS / RabbitMQ (reserved) |

---

## Composition root

```python
from production_platform import InfrastructureBundle, ProductionBundle

infra = InfrastructureBundle.create_offline()  # CI / local
# or
infra = InfrastructureBundle.from_environment()  # env-driven with fallback

bundle = ProductionBundle.create(with_infrastructure=True)
```

No package may construct Postgres/Redis/S3 clients outside this root.

---

## India-first defaults

- Timezone: `Asia/Kolkata`
- Currency: `INR`
- CERT-In log retention posture: ≥180 days (config enforced)
- DPDP residency flag: `in`
- Future ports (stubs): DigiLocker, PAN, UPI, Demat, AA, OCEN

---

## Related guides

- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
- [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- [ADAPTER_MATRIX.md](ADAPTER_MATRIX.md)
- [INFRASTRUCTURE_MIGRATION_GUIDE.md](INFRASTRUCTURE_MIGRATION_GUIDE.md)
