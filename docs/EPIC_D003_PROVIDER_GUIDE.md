# EPIC-D003 — Corporate Actions Provider Architecture

## Port

`CorporateActionPort`:

- `get_actions(CorporateActionQuery) -> AuthenticatedCorporateActions | None`
- `resolve_company(instrument) -> CorporateActionCompanyIdentity | None`
- `health() -> CorporateActionProviderHealth`
- `provider_id: str`

Never invent events. Missing → `None`. Invalid → raise.

## Query

`CorporateActionQuery`: instrument, optional `action_type`, `start_date`,
`end_date`, `limit`.

## Models

Each `AuthenticatedCorporateAction` carries:

- action_id, action_type, symbol, description
- effective_date, ex_date, record_date, payment_date, announcement_date
- optional as-reported numerics: ratio_from/to, amount, shares
- optional symbol change fields; provenance on the bundle

## Service / adapters

Same resilience stack as D001/D002 (cache, rate limit, retry, circuit breaker).

| Adapter | Behaviour |
|---|---|
| Null | Always unavailable |
| InMemory | Auth + seeded; deterministic newest-first sort/filter |
| ConfiguredHttp | API key + base URL |

Env: `build_default_corporate_action_adapter_from_env()`.

## Forbidden

- Adjusting historical prices
- Calculating dilution / impact
- Valuation, scoring, recommendations
- Fabricating events when feed missing
