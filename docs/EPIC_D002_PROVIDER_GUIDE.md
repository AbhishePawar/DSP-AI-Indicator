# EPIC-D002 — Financial Statement Provider Architecture

## Port

`FinancialStatementPort` (`data_engine.financial_statement.service`):

- `get_statements(StatementQuery) -> AuthenticatedFinancialStatements | None`
- `resolve_company(instrument) -> CompanyIdentity | None`
- `health() -> StatementProviderHealth`
- `provider_id: str`

Adapters must **never invent** line items or ratios. Missing → `None`. Invalid → raise.

## Query

`StatementQuery`: instrument, optional `period_type` (`annual`|`quarterly`|`ttm`),
`limit`, `include_restated`.

## Service

`FinancialStatementService` wraps a port with:

1. Caching (`InMemoryCache`, default TTL 300s)
2. Rate limiting (shared D001 `RateLimiter`)
3. Retry + timeout (shared D001 `RetryPolicy`)
4. Circuit breaker (shared D001 `CircuitBreaker`)
5. Validation (`validate_authenticated_statements`)
6. Provenance / request_id stamping
7. Metrics + structured logging (`data_engine.financial_statement`)

## Registry

`FinancialStatementProviderRegistry` — named providers + default.

## Adapters

| Adapter | Auth | Behaviour |
|---|---|---|
| `NullAuthenticatedStatementAdapter` | none | Always unavailable |
| `InMemoryAuthenticatedStatementAdapter` | `api_key` | Seeded only; filters/sorts deterministically |
| `ConfiguredHttpStatementAdapter` | API key + base URL | Licensed vendor HTTP JSON |

Selection: `build_default_statement_adapter_from_env()`.

## Deterministic mapping

`build_period_from_mapping` / `build_statements_from_mapping` map vendor-neutral
JSON keys to the RS-003 field set. Currency normalization is **label/ISO
normalization only** — no FX conversion. Mixed currencies across periods → reject.

## Forbidden

- Calculating ROE/margins/growth in this epic
- Treating Yahoo (or any unauthenticated scrape) as authenticated filings
- Changing `/analyse` or engine scoring
- Fabricating missing line items
