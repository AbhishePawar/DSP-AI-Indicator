# EPIC-D004 — Historical Data Provider Architecture

## Port

`HistoricalSeriesPort`:

- `get_series(HistoricalSeriesQuery) -> AuthenticatedHistoricalBundle | None`
- `resolve_company(instrument) -> HistoricalCompanyIdentity | None`
- `health() -> HistoricalProviderHealth`
- `provider_id: str`

Never invent history. Missing → `None`. Invalid → raise.

## Query

`HistoricalSeriesQuery`: instrument, `series_kind`, optional `frequency`,
`start_date`, `end_date`, `limit`.

## Bundle contents

| Kind | Payload |
|---|---|
| `ohlcv` | Ascending `bars` (O/H/L/C/V) |
| `market_cap` / `volume` / `enterprise_value` | Ascending `points` |
| `fundamentals` / `ratios` | Ascending `snapshots` (pass-through fields) |

OHLC consistency validated when all four prices present — no fabrication.

## Adapters

Null · InMemory (auth + seeded) · ConfiguredHttp (API key + base URL)

Env: `build_default_historical_adapter_from_env()`.

## Forbidden

- Calculating indicators / TA
- Adjusting prices for splits/dividends in this epic
- Valuation, scoring, recommendations
- Fabricating missing bars
