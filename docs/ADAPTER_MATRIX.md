# Adapter Matrix (PEP-002)

| Port | Reference adapter | Vendor adapter | Extra | Status |
|---|---|---|---|---|
| `DatabasePort` | `InMemoryDatabasePort` | `PostgresDatabasePort` | `[postgres]` | Ready |
| `CachePort` | `InMemoryCachePort` | `RedisCachePort` | `[redis]` | Ready |
| `RateLimiterPort` | `InMemoryRateLimitPort` | `RedisRateLimitPort` | `[redis]` | Ready |
| `LockPort` | `InMemoryLockPort` | `RedisLockPort` | `[redis]` | Ready |
| `SessionPort` | `InMemorySessionPort` | `RedisSessionPort` | `[redis]` | Ready |
| `StoragePort` | `InMemoryStoragePort` / `LocalFilesystemStoragePort` | `S3CompatibleStoragePort` (S3/MinIO) | `[s3]` | Ready |
| `QueuePort` | `InMemoryJobQueuePort` | Redis Streams / SQS / RabbitMQ | — | Architecture (memory only) |
| `BackgroundTaskPort` | `InMemoryBackgroundTaskPort` | Worker service | — | Architecture |
| `SecretProviderPort` | `InMemorySecretsPort` / `EnvSecretsPort` | AWS / Azure / Vault | — | Env ready; cloud future |
| `ConfigurationPort` | `ConfigurationManager` | — | — | Ready |
| `ClockPort` | `SystemClockPort` / `FixedClockPort` | — | — | Ready |
| `MarketCalendarPort` | `StaticIndiaMarketCalendar` | Licensed NSE/BSE feed | — | Seed calendar |
| DigiLocker / PAN / UPI | Null stubs | Licensed providers | — | Architecture only |

**Contract tests:** `packages/production_platform/tests/test_contracts.py`  
All reference adapters must pass; Redis/Postgres adapters must satisfy the same behaviours when extras + services are present.
