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
| `MarketQuotePort` (data_engine) | `NullAuthenticatedQuoteAdapter` | `ConfiguredHttpQuoteAdapter` / memory seeded | EPIC-D001 | Ready |
| `FinancialStatementPort` (data_engine) | `NullAuthenticatedStatementAdapter` | `ConfiguredHttpStatementAdapter` / memory seeded | EPIC-D002 | Ready |
| `CorporateActionPort` (data_engine) | `NullAuthenticatedCorporateActionAdapter` | `ConfiguredHttpCorporateActionAdapter` / memory seeded | EPIC-D003 | Ready |
| `HistoricalSeriesPort` (data_engine) | `NullAuthenticatedHistoricalAdapter` | `ConfiguredHttpHistoricalAdapter` / memory seeded | EPIC-D004 | Ready |

**Contract tests:** `packages/production_platform/tests/test_contracts.py`  
All reference adapters must pass; Redis/Postgres adapters must satisfy the same behaviours when extras + services are present.

**Market quotes:** `packages/data_engine/tests/test_market_quote.py` · [EPIC_D001_MARKET_DATA_PROVIDER.md](EPIC_D001_MARKET_DATA_PROVIDER.md)

**Financial statements:** `packages/data_engine/tests/test_financial_statement.py` · [EPIC_D002_PROVIDER_GUIDE.md](EPIC_D002_PROVIDER_GUIDE.md)

**Corporate actions:** `packages/data_engine/tests/test_corporate_actions.py` · [EPIC_D003_PROVIDER_GUIDE.md](EPIC_D003_PROVIDER_GUIDE.md)

**Historical series:** `packages/data_engine/tests/test_historical_series.py` · [EPIC_D004_PROVIDER_GUIDE.md](EPIC_D004_PROVIDER_GUIDE.md)

**Unified orchestrator:** `packages/data_engine/tests/test_data_orchestrator.py` · [EPIC_D005_ORCHESTRATOR_DESIGN.md](EPIC_D005_ORCHESTRATOR_DESIGN.md)
