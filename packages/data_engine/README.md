# Data Engine

The Data Engine is the platform's data-acquisition and normalization
layer. It defines the abstract boundary between the platform and every
external data source (market-data vendors, fundamentals APIs, economic
data providers, alternative-data feeds), and it is the only place in the
platform where that boundary is crossed.

As of Sprint 6.3, this package contains three real provider integrations:

- `YahooFinanceAdapter` (Sprint 2.4) — historical **daily** OHLCV
- `YahooFinanceFundamentalsAdapter` (Sprint 6.2) — as-reported
  annual/quarterly financial statements via Yahoo Finance quoteSummary
- `FredEconomicAdapter` (Sprint 6.3) — US macroeconomic series via FRED

Sprints 2.1–2.3 built the ports, provider framework, and normalization
pipeline that made all adapters additive rather than redesigns.

- **Sprint 2.1** proved the Data Engine's shape: ports, adapters,
  cache, config, exceptions, models, and a first service.
- **Sprint 2.2** replaced Sprint 2.1's minimal `ProviderMetadata` with a
  full provider framework — structured capabilities, rate-limit and
  authentication metadata, provider status, and a `ProviderFactory` —
  so that Yahoo Finance, Alpha Vantage, Polygon, Financial Modeling
  Prep, Twelve Data, NSE, RBI, FRED, Quandl, CoinGecko, or any provider
  added after them can plug in later without any further architecture
  change. Still no concrete adapter, HTTP client, or network call.
- **Sprint 2.3** added the canonical **normalization and transformation
  framework**: provider-neutral raw models, abstract normalizer
  interfaces, a composable validation-stage pipeline, and a reusable
  `TransformationPipeline` orchestrator, plus one fully worked
  reference implementation (`DefaultMarketDataNormalizer`). This is the
  layer that turns whatever an adapter fetches into validated
  `contracts` objects — still no concrete adapter, HTTP client, or
  network call.
- **Sprint 2.4** added `data_engine.adapters.yahoo_finance` — the
  first concrete adapter, a minimal isolated HTTP client, and the
  registration wiring (`ProviderMetadata` + a `ProviderFactory`
  builder) that plugs it into the unmodified `ProviderRegistry`. This
  is the first sprint that performs an actual (test-mocked in the test
  suite; real in production use) network call and the first time
  `MarketDataService` retrieves data through a provider that isn't a
  test fake.
- **Sprint 6.2** completed the fundamentals **data plane**:
  `YahooFinanceFundamentalsAdapter` implementing `FundamentalsDataPort`,
  `DefaultFundamentalNormalizer`, `FundamentalStatementsBuilder`,
  `FundamentalsDataService`, and registration under
  `yahoo_finance_fundamentals`. Output stops at
  `contracts.FundamentalStatement` — `FinancialSnapshot` remains an
  engine-local type assembled in Sprint 6.4 / orchestration.
- **Sprint 6.3** completed the economic **data plane**:
  `FredEconomicAdapter` implementing `EconomicDataPort`,
  `DefaultEconomicNormalizer`, `EconomicSeriesBuilder`,
  `EconomicDataService`, and registration under `fred`. Output stops at
  `contracts.EconomicSeries` — `EconomicSnapshot` remains engine-local
  for Sprint 6.4.
- **Sprint 6.4** (external package `snapshot_bridge`) wraps contracts
  outputs into `FinancialSnapshot` / `EconomicSnapshot`. That package
  depends on `data_engine` + engines; this package never imports it.

## Responsibilities

The Data Engine is responsible for:

- Defining **ports** — abstract interfaces describing what data the
  platform can request (price history, financial statements, economic
  series, alternative-data signals) without saying how it is obtained.
- Defining the **adapter** scaffolding that concrete provider
  integrations will implement against those ports.
- Providing a **provider framework** — structured metadata, capability
  flags, a registry, and a factory — so callers can register, discover,
  filter, and select a provider by id or by capability without ever
  importing a concrete adapter class.
- Providing a **cache** abstraction and a minimal in-memory reference
  implementation, so repeated requests don't necessarily hit a real
  provider.
- Providing a small **application-layer service** that composes the
  cache and the provider registry to fulfill a request end-to-end.
- Defining **provider-neutral raw models** that describe exactly what
  shape a provider adapter must populate, without describing how any
  particular provider is structured internally.
- Providing the **normalization and transformation framework** —
  abstract normalizer interfaces, composable validation stages, and a
  reusable pipeline orchestrator — that converts raw models into
  `contracts` objects the same way for every provider.
- Providing concrete provider adapters
  (`YahooFinanceAdapter`, `YahooFinanceFundamentalsAdapter`,
  `FredEconomicAdapter`) that prove the whole chain works end to end.
- Producing nothing but validated `contracts` types. Every method that
  returns data returns a `contracts` domain object — never a raw dict,
  DataFrame, or vendor-specific response shape.

The Data Engine is explicitly **not** responsible for:

- Talking to any vendor's SDK or REST API *outside* of a concrete
  adapter — Yahoo/FRED adapters are the only classes aware of those
  vendor endpoints.
- Any indicator, valuation, fundamental *analysis*, or economic
  *regime* computation (engines analyze; this package acquires and
  normalizes).
- Constructing `fundamental.models.FinancialSnapshot` or
  `economic.models.EconomicSnapshot` — those types live in their
  engines; builders emit ordered contracts tuples/series for Sprint 6.4.
- Deciding *how* configuration is loaded from the environment (only the
  configuration *shape* is defined here — see Design Decisions).
- Orchestrating across engines (that's the future `orchestration`
  package's job).
- Resolving instrument identity from a raw ticker string (that's a
  reference/master-data concern — normalizers accept an
  already-resolved `Instrument`, they don't produce one).

## Package Structure

```
packages/data_engine/
├── README.md
├── src/
│   └── data_engine/
│       ├── __init__.py       # public API
│       ├── ports/             # abstract interfaces for external data sources
│       ├── adapters/          # BaseAdapter scaffolding + concrete adapters
│       │   ├── __init__.py     # BaseAdapter
│       │   ├── yahoo_finance/   # Yahoo adapters (subpackage — see below)
│       │   │   ├── __init__.py
│       │   │   ├── adapter.py               # YahooFinanceAdapter (OHLCV)
│       │   │   ├── fundamentals_adapter.py
│       │   │   ├── fundamentals_registration.py
│       │   │   ├── http_client.py           # shared JsonHttpClient Protocol
│       │   │   └── registration.py
│       │   └── fred/                # FRED economic adapter (Sprint 6.3)
│       │       ├── __init__.py
│       │       ├── adapter.py               # FredEconomicAdapter
│       │       ├── catalog.py               # platform code → FRED series_id
│       │       └── registration.py
│       ├── builders/           # FundamentalStatementsBuilder, EconomicSeriesBuilder
│       ├── providers/          # provider framework (subpackage — see below)
│       │   ├── __init__.py     # barrel re-export
│       │   ├── enums.py         # ProviderStatus, AuthenticationType, DataCapability
│       │   ├── capabilities.py  # ProviderCapabilities
│       │   ├── metadata.py      # ProviderMetadata, RateLimitPolicy
│       │   ├── registry.py      # ProviderRegistry
│       │   └── factory.py       # ProviderFactory
│       ├── cache/              # CachePort + InMemoryCache reference impl
│       ├── config/             # DataEngineConfig settings shape
│       ├── exceptions/         # DataEngineError root + NormalizationError family
│       ├── models/             # PriceSeriesRequest, FundamentalsRequest
│       ├── raw_models/          # provider-neutral raw models (subpackage — see below)
│       │   ├── __init__.py        # barrel re-export
│       │   ├── market.py           # RawMarketBar, RawMarketSeries
│       │   ├── fundamentals.py      # RawFundamentalData
│       │   ├── economic.py           # RawEconomicDataPoint, RawEconomicSeries
│       │   └── alternative.py         # RawAlternativeData
│       ├── normalization/       # normalization framework (subpackage — see below)
│       │   ├── __init__.py        # barrel re-export
│       │   ├── normalizers.py      # 4 abstract Normalizer interfaces
│       │   ├── defaults.py          # DefaultMarketDataNormalizer + DefaultFundamentalNormalizer
│       │   ├── records.py            # NormalizedBar, NormalizedStatement
│       │   ├── coercion.py            # coerce_timestamp/float/date/optional_float
│       │   ├── pipeline.py             # TransformationPipeline orchestrator
│       │   └── validation/              # composable validation stages
│       │       ├── __init__.py            # barrel re-export
│       │       ├── base.py                  # ValidationStage, ValidationPipeline
│       │       └── stages.py                  # 7 concrete stages
│       └── services/           # MarketDataService + FundamentalsDataService
└── tests/
    ├── … (existing suite)
    ├── test_fundamental_normalizer.py
    ├── test_yahoo_finance_fundamentals_adapter.py
    └── test_yahoo_finance_fundamentals_registration.py
```

## Sprint 6.2 — Fundamentals Data Flow

```
Yahoo Finance quoteSummary
        │
        ▼
YahooFinanceFundamentalsAdapter   (vendor shape → RawFundamentalData)
        │
        ▼
RawFundamentalData                (provider-neutral line_items map)
        │
        ▼
DefaultFundamentalNormalizer      (alias map → coerce → validate → contracts)
        │
        ▼
FundamentalStatement[]            (contracts; optional fields may be None)
        │
        ▼
FundamentalStatementsBuilder      (order, uniqueness, instrument check)
        │
        ▼
FundamentalsDataService           (cache + registry composition)
        │
        ▼
[Sprint 6.4] FinancialSnapshot    (fundamental package — not built here)
        │
        ▼
Fundamental Engine
```

### Sequence (annual request)

```
Caller                  FundamentalsDataService     Registry / Adapter              Normalizer
  │                              │                          │                          │
  │  FundamentalsRequest         │                          │                          │
  │─────────────────────────────▶│  get(provider)           │                          │
  │                              │─────────────────────────▶│                          │
  │                              │  get_fundamental_…       │                          │
  │                              │─────────────────────────▶│  HTTP quoteSummary       │
  │                              │                          │──────▶ Yahoo             │
  │                              │                          │◀───── JSON               │
  │                              │                          │  RawFundamentalData × N  │
  │                              │                          │─────────────────────────▶│
  │                              │                          │◀── FundamentalStatement  │
  │                              │  Builder.assemble        │                          │
  │◀──── tuple[FundamentalStatement, ...] (most-recent-first)                         │
```

### Provider mapping table (Yahoo → contracts)

| Yahoo field | Canonical / destination |
|---|---|
| `totalRevenue` | `FundamentalStatement.revenue` |
| `costOfRevenue` | `cost_of_revenue` |
| `grossProfit` | `gross_profit` |
| `operatingIncome` | `operating_income` |
| `netIncome` | `net_income` |
| `basicEPS` / `dilutedEPS` | `eps_basic` / `eps_diluted` |
| `totalAssets` | `total_assets` |
| `totalLiab` / `totalLiabilities*` | `total_liabilities` |
| `totalStockholderEquity` | `total_equity` |
| `cash` / `cashAndCashEquivalents` | `cash_and_equivalents` |
| `totalDebt` / `longTermDebt` / `shortLongTermDebtTotal` | `total_debt` |
| `totalCashFromOperatingActivities` | `operating_cash_flow` |
| `totalCashflowsFromInvestingActivities` | `investing_cash_flow` |
| `totalCashFromFinancingActivities` | `financing_cash_flow` |
| `capitalExpenditures` | `capital_expenditures` |
| `sharesOutstanding` | `extra_line_items["shares_outstanding"]` |
| `marketCap` | `extra_line_items["market_capitalization"]` |
| `enterpriseValue` | `extra_line_items["enterprise_value"]` |
| ratios (`currentRatio`, `debtToEquity`, …) | `extra_line_items[...]` |

Missing Yahoo fields become `None` on the statement (or are omitted from
`extra_line_items`). Malformed identity fields raise
`MissingFieldError` / `InvalidProviderDataError` — never silent defaults
for required identity.

### Snapshot builder explanation

`FundamentalStatementsBuilder` validates and orders
`tuple[FundamentalStatement, ...]` with the same structural rules the
Fundamental Engine's `FinancialSnapshot` expects (non-empty, one
instrument, unique `period_end`, most-recent-first). It does **not**
import `fundamental` — dependency direction stays
`data_engine → contracts, core` only. Sprint 6.4 (or orchestration)
wraps the builder output in `FinancialSnapshot(instrument, statements)`.

## Dependency Diagram

```
contracts   (shared domain vocabulary — Instrument, PriceSeries, ...)
    ▲
    │
core        (generic exceptions, validation, Registry[T])
    ▲
    │
data_engine
    │
    ├── ports/       ── depends on: contracts (types in method signatures)
    ├── cache/       ── depends on: nothing outside stdlib
    ├── adapters/    ── depends on: nothing outside stdlib (BaseAdapter itself)
    │   └── yahoo_finance/ ── depends on: contracts, data_engine.ports,
    │                          data_engine.exceptions, data_engine.normalization,
    │                          data_engine.raw_models, data_engine.providers
    │                          (registration.py only), data_engine.adapters
    ├── config/      ── depends on: nothing outside stdlib
    ├── exceptions/  ── depends on: core (DSPAIError)
    ├── models/      ── depends on: contracts, data_engine.exceptions
    ├── providers/   ── depends on: core (Registry[T]), data_engine.adapters,
    │                                 data_engine.exceptions
    ├── raw_models/  ── depends on: nothing outside stdlib
    ├── normalization/ ── depends on: contracts (construct step only),
    │                                   data_engine.exceptions,
    │                                   data_engine.raw_models
    └── services/    ── depends on: contracts, and every module above it
```

`data_engine` depends only on `contracts` and `core`, exactly as
required. It does **not** depend on `dsp` or any future engine, and
nothing in `contracts` or `core` was modified to build it — Sprints
2.2, 2.3, and 2.4 touched only files inside `packages/data_engine/`.

`adapters/yahoo_finance/` is the first module in this package to
depend on `normalization/`, `raw_models/`, `ports/`, and `providers/`
all at once — that is expected and by design: an adapter is the one
place all four are meant to converge. `http_client.py` inside it is
the exception: it depends on nothing but `data_engine.exceptions` and
the standard library, since it is a generic JSON-over-HTTP utility
that happens to be *located* next to the only adapter that currently
uses it, not something conceptually specific to Yahoo Finance (see
Design Decision 27).

`raw_models/` is a leaf: it depends on nothing but the standard
library, not even `contracts`, so that `adapters/` (which populates raw
models) never needs to import the normalization framework just to know
what shape to produce. `normalization/` depends on `raw_models/` (its
input) and `contracts` (its output) but not on `ports/`, `adapters/`,
`providers/`, `cache/`, `config/`, or `services/` — nothing about *how*
a provider is registered or invoked leaks into *how* its data gets
normalized.

### Provider Framework Diagram

```
enums.py: ProviderStatus, AuthenticationType, DataCapability
     │  (closed vocabularies)
     ▼
capabilities.py: ProviderCapabilities (frozenset[DataCapability])
     │  used by
     ▼
metadata.py: ProviderMetadata (id, name, version, capabilities,
             rate_limit, auth_type, priority, status)
     │  stored per provider by
     ▼
registry.py: ProviderRegistry
   .register(adapter, metadata)
   .get(id) / .get_metadata(id)
   .filter_by_capability(*caps)
   .select_preferred(*caps)
     ▲
     │ registers the adapter a builder produced
     │
factory.py: ProviderFactory
   .register_builder(id, builder)
   .create(id, config) -> BaseAdapter
```

`ProviderRegistry` tracks already-constructed adapters plus their
`ProviderMetadata`; `ProviderFactory` tracks *how to construct* an
adapter from configuration. They compose — a factory-built adapter is
handed to the registry along with its metadata — but neither class
depends on the other (see Design Decisions).

External providers are only ever reached through this chain:

```
caller
  → data_engine.services.MarketDataService
    → data_engine.providers.ProviderRegistry   (look up / select by id or capability)
      → data_engine.ports.MarketDataPort        (abstract interface)
        → data_engine.adapters.yahoo_finance.YahooFinanceAdapter
          → data_engine.adapters.yahoo_finance.http_client.JsonHttpClient
            → the actual Yahoo Finance HTTP request
```

No layer above the adapter line knows which vendor, if any, is behind a
given provider id — `MarketDataService` and `ProviderRegistry` are
completely unmodified by Sprint 2.4; they compose `YahooFinanceAdapter`
purely through `MarketDataPort`, exactly as they would compose any
future adapter. That is the dependency-inversion guarantee Sprint 2.1
established, Sprint 2.2 built on, and Sprint 2.4 is the first sprint to
actually exercise with a real, network-calling implementation.

### Transformation Pipeline Diagram

This is the flow every provider adapter follows. `YahooFinanceAdapter`
(Sprint 2.4) is the first adapter to walk it end to end; every other
future adapter follows the identical shape:

```
Yahoo Finance                    data_engine.adapters.yahoo_finance.http_client
     │  chart-API JSON response   (JsonHttpClient / UrllibJsonHttpClient)
     ▼
YahooFinanceAdapter               data_engine.adapters.yahoo_finance.adapter
     │  populates raw_models.RawMarketBar / RawMarketSeries
     │  (the ONLY class aware Yahoo Finance exists)
     ▼
Raw Provider Response            data_engine.raw_models
     │  (provider-neutral shape, every field loosely typed)
     ▼
Normalizer                       data_engine.normalization.normalizers
     │  .normalize(raw, instrument) -> Contract
     │  internally built on TransformationPipeline:
     │
     │    raw items
     │       │
     │       ▼
     │    [1] raw_validation: ValidationPipeline    (required fields,
     │       │                                        sentinel values)
     │       ▼
     │    [2] coerce: Raw -> NormalizedBar          ("Normalize")
     │       │                                       (coerce_timestamp,
     │       │                                        coerce_float)
     │       ▼
     │    [3] normalized_validation: ValidationPipeline  ("Validate")
     │       │   (timestamp, duplicate, sorting,
     │       │    OHLC consistency, volume)
     │       ▼
     │    [4] construct: NormalizedBar -> PriceBar  ("Construct Contracts")
     │       ▼
     │    tuple[PriceBar, ...]
     ▼
contracts Models                 PriceBar / PriceSeries (etc.)
     │  ("Return Canonical Objects")
     ▼
MarketDataService                 data_engine.services   (unchanged)
     │
     ▼
Future Engines
```

Steps `[1]`–`[4]` are exactly what
`TransformationPipeline.run()` executes, and exactly what
`DefaultMarketDataNormalizer` configures. Any `NormalizationError`
raised inside steps `[1]`–`[3]` propagates unchanged (it already
carries a provider-attributed diagnostic); any other, unexpected
exception is wrapped as a `TransformationError` — see Design Decisions.

`YahooFinanceAdapter` adds exactly one translation step *before* this
pipeline even starts: a failed HTTP request (network error, timeout,
non-2xx status, unparsable body) is raised as `ProviderRequestError`
by `http_client.py`, a `DataEngineError` sibling of
`NormalizationError` rather than a subclass of it — see Design
Decision 26. A response that Yahoo Finance itself flags as an error,
or one with an unexpected shape or zero usable bars, is raised as
`InvalidProviderDataError` by the adapter directly, reusing the
existing normalization exception hierarchy rather than inventing a
new one for what is fundamentally the same kind of problem (bad
provider data) at an earlier stage (before a raw model even exists).

## Base Interfaces

### Ports (`data_engine.ports`)

Four abstract interfaces, one per category of external data the platform
will eventually need, each returning only `contracts` types:

- `MarketDataPort.get_price_series(instrument, frequency, start, end) -> PriceSeries`
- `FundamentalsDataPort.get_fundamental_statements(instrument, period_type, *, limit=None) -> tuple[FundamentalStatement, ...]`
- `EconomicDataPort.get_economic_series(indicator_code, country) -> EconomicSeries`
- `AlternativeDataPort.get_signals(instrument) -> tuple[Signal, ...]`

### Cache (`data_engine.cache`)

- `CachePort.get(key) -> V | None`, `.set(key, value, *, ttl_seconds=None)`, `.invalidate(key)`
- `InMemoryCache` — a minimal, non-thread-safe reference implementation
  used by tests and by the service layer when no real cache backend is
  configured.

### Adapters (`data_engine.adapters`)

- `BaseAdapter` — the one piece of shared shape every concrete adapter
  must implement: a `provider_name` property used for registration.
- `YahooFinanceAdapter` (`data_engine.adapters.yahoo_finance`) — concrete
  `MarketDataPort` for historical **daily** OHLCV bars only.
- `YahooFinanceFundamentalsAdapter` — concrete `FundamentalsDataPort`
  for annual/quarterly/TTM as-reported statements via quoteSummary.
  Shares `JsonHttpClient` with the OHLCV adapter; registered separately
  as `yahoo_finance_fundamentals` so capability discovery stays clean.
- `JsonHttpClient` / `UrllibJsonHttpClient`
  (`data_engine.adapters.yahoo_finance.http_client`) — a minimal,
  vendor-agnostic `get_json(url, *, params=None) -> Mapping` boundary.
- `YAHOO_FINANCE_METADATA` / `build_yahoo_finance_adapter` /
  `register_yahoo_finance` — OHLCV registration helpers.
- `YAHOO_FINANCE_FUNDAMENTALS_METADATA` /
  `build_yahoo_finance_fundamentals_adapter` /
  `register_yahoo_finance_fundamentals` — fundamentals registration
  helpers. None of this runs automatically at import time.

### Providers (`data_engine.providers`)

- `ProviderStatus` — `ACTIVE` / `DISABLED` / `EXPERIMENTAL` / `DEPRECATED`.
- `AuthenticationType` — `NONE` / `API_KEY` / `OAUTH` / `BASIC` / `TOKEN`.
- `DataCapability` — the 13 discrete capability flags named in the
  Sprint 2.2 mission (`MARKET_DATA`, `FUNDAMENTALS`, `ECONOMIC_DATA`,
  `ALTERNATIVE_DATA`, `INTRADAY`, `DAILY`, `OPTIONS`, `CRYPTO`, `FOREX`,
  `NEWS`, `ETF`, `INDICES`, `MUTUAL_FUNDS`).
- `ProviderCapabilities` — a structured, set-based wrapper around
  `frozenset[DataCapability]`, built via
  `ProviderCapabilities.from_flags(market_data=True, ...)`, with
  `has`/`has_all`/`has_any` plus one named boolean property per
  capability.
- `RateLimitPolicy` — descriptive `requests_per_minute` /
  `requests_per_day` / `concurrent_requests` fields. Not enforced by
  this package.
- `ProviderMetadata` — `provider_id`, `name`, `version`, `description`,
  `homepage`, `capabilities`, `rate_limit`, `auth_type`, `priority`,
  `status`. Structurally validates that `provider_id`/`name` are
  non-empty and normalizes `provider_id` to lowercase.
- `ProviderRegistry` — a capability-aware wrapper around
  `core.registry.Registry[BaseAdapter]` supporting registration,
  id lookup, metadata lookup, `filter_by_capability(*caps)`, and
  `select_preferred(*caps)` (lowest `priority` wins, ties broken by id,
  only `ACTIVE` providers considered).
- `ProviderFactory` — a `core.registry.Registry[ProviderBuilder]`
  wrapper: `register_builder(id, builder)` then
  `create(id, config) -> BaseAdapter`.

### Raw Models (`data_engine.raw_models`)

Provider-neutral containers for exactly what a provider adapter
reports, before any coercion or validation. Every value field is
`Any` — a raw model asserts that *some* value was reported, never that
it is well-formed:

- `RawMarketBar` / `RawMarketSeries` — one bar / a provider's full
  series of bars for a symbol.
- `RawFundamentalData` — one financial statement, with line items kept
  as a flat, provider-labeled mapping rather than named fields.
- `RawEconomicDataPoint` / `RawEconomicSeries` — one observation / a
  full series for a country/indicator pair.
- `RawAlternativeData` — one alternative/behavioral-data point.

None of these are `contracts` types, none of them validate their
content, and none of them depend on anything outside the standard
library.

### Normalization (`data_engine.normalization`)

The canonical raw-to-contracts pipeline described in the Transformation
Pipeline Diagram above:

- **Normalizer interfaces** — `MarketDataNormalizer`,
  `FundamentalNormalizer`, `EconomicDataNormalizer`,
  `AlternativeDataNormalizer`. Each declares one `normalize(...)`
  method converting a raw model (plus an already-resolved `Instrument`
  where relevant) into its matching `contracts` type.
- **`DefaultMarketDataNormalizer`** / **`DefaultFundamentalNormalizer`**
  — concrete, provider-agnostic normalizers. Contain zero vendor-specific
  endpoint logic; adapters only populate raw models.
- **`NormalizedBar`** / **`NormalizedStatement`** — strictly-typed
  intermediate records produced by the "Normalize" step.
- **`coerce_timestamp` / `coerce_float` / `coerce_optional_float` /
  `coerce_date`** (`data_engine.normalization.coercion`)
  — generic helpers turning loosely-typed raw values into strict types.
- **`ValidationStage` / `ValidationPipeline`** (`data_engine.normalization.validation`)
  — the composable-check abstraction, plus seven concrete stages:
  `RequiredFieldValidationStage`, `MissingValueValidationStage`,
  `TimestampValidationStage`, `DuplicateDetectionStage`,
  `SortingVerificationStage`, `OHLCConsistencyStage`,
  `VolumeValidationStage`. Every stage is parameterized by field names
  or a key-extraction callable, so none of them are hard-coded to bars
  specifically.
- **`TransformationPipeline`** (`data_engine.normalization.pipeline`)
  — the generic `coerce -> raw_validation -> normalized_validation ->
  construct` orchestrator every normalizer is built on, instead of each
  one hand-rolling its own control flow.

### Builders (`data_engine.builders`)

- `FundamentalStatementsBuilder` — assembles a canonical
  most-recent-first `tuple[FundamentalStatement, ...]`. Does not create
  `FinancialSnapshot` (engine-local; Sprint 6.4).

### Services (`data_engine.services`)

- `MarketDataService` — cache-then-provider composition for price series.
- `FundamentalsDataService` — cache-then-provider composition for
  fundamental statements, always run through
  `FundamentalStatementsBuilder` before return.
- `EconomicDataService` — cache-then-provider composition for
  macroeconomic series, plus `get_available_series` for graceful
  multi-indicator acquisition (Sprint 6.3).

## Known Architectural Issues

Sprint 2.4's mission was to integrate one real provider without
refactoring the "stable" Provider Infrastructure or Normalization
Framework. Doing so surfaced one genuine gap in that stable code,
which is recorded here rather than fixed silently, per that
constraint:

**`DefaultMarketDataNormalizer.normalize()` can raise an untranslated
`contracts.exceptions.ContractValidationError` instead of a
`data_engine` exception, if handed a `RawMarketSeries` with zero
bars.** `TransformationPipeline.run()` only wraps failures raised
*while it runs* (`raw_validation` → `coerce` → `normalized_validation`
→ `construct`); an empty input sequence passes through every one of
those steps trivially (there is nothing to validate or construct) and
`run()` returns `()` successfully. `DefaultMarketDataNormalizer.normalize()`
then calls `PriceSeries(instrument=..., frequency=..., bars=())`
*outside* that try/except — and `contracts.domain.price_series.PriceSeries.__post_init__`
rejects empty `bars` with `ContractValidationError`, a plain
`Exception` subclass with no relationship to `DataEngineError`. A
caller that only catches `DataEngineError`/`NormalizationError` (the
documented contract of `normalize()`) would not catch this.

This is real but latent: it can only be triggered by a raw series
with zero bars, which the Normalization Framework's own tests never
constructed. `YahooFinanceAdapter` (Sprint 2.4) works around it at the
adapter boundary — it raises its own `InvalidProviderDataError` if
Yahoo Finance returns no usable bars for the requested range,
*before* ever calling `normalize()` — so this adapter cannot trigger
the gap in practice. That workaround does not fix the underlying
issue for any *other* future adapter that forgets the same guard.
Recommended follow-up (not performed this sprint, since it would mean
modifying "stable" code beyond this sprint's scope): either have
`TransformationPipeline.run()`/`DefaultMarketDataNormalizer.normalize()`
raise a `data_engine` exception (e.g. `InvalidProviderDataError`) for
an empty input up front, or explicitly document "raw series must be
non-empty" as a precondition every adapter must enforce itself.

## Design Decisions

1. **Ports are synchronous, not asynchronous, for now.** The long-term
   architecture guidance recommends designing the Data Engine for async
   I/O. This sprint deliberately kept every port and service method
   synchronous instead, because no real, network-calling adapter exists
   yet to justify the added complexity — and introducing `async def`
   would have required adding `pytest-asyncio` as a new test dependency
   with nothing concrete to test against. This is a **named, revisitable**
   decision, not an oversight: the first real adapter that performs
   actual network I/O should be the trigger to migrate `ports` (and the
   services that call them) to `async def`.

2. **`CachePort` lives inside `cache/`, not `ports/`.** Both are
   dependency-inversion boundaries in the generic sense, but they're
   conceptually different: `ports/` is the boundary the Data Engine
   crosses to reach *external* systems it doesn't control. Caching is
   *internal* infrastructure the Data Engine owns outright. Keeping
   `CachePort` and its reference implementation together in `cache/`
   keeps that distinction visible in the package layout rather than
   collapsing every abstract interface into one undifferentiated
   `ports/` module.

3. **`adapters/` intentionally contains no concrete adapter.** Per the
   mission's explicit constraint, no Yahoo Finance (or any other vendor)
   integration was built. `BaseAdapter` exists to give future adapters a
   consistent registration shape, but the module is otherwise a
   placeholder by design — the point of this sprint was to prove the
   *shape* of the boundary, not to cross it yet.

   > **Superseded by Sprint 2.4.** `adapters/` now contains
   > `YahooFinanceAdapter` (see Design Decision 25). This entry is kept
   > verbatim as a historical record of Sprint 2.1's own scope, not as
   > a statement of the package's current contents.

4. **`providers/` and `adapters/` are separate on purpose.** `adapters/`
   answers "what does a concrete implementation of a port look like?";
   `providers/` answers "which implementations are currently registered,
   and what can each one do?" Conflating them would make it harder to
   reason about "is this a code-shape question or a runtime-registration
   question" as more providers are added.

5. **The provider registry is built on `core.registry.Registry[T]`,
   not a bespoke dict.** This directly follows the pattern
   `dsp.registry` already established for indicators, and is the exact
   reuse of Core's generic infrastructure that the architecture document
   calls for. `ProviderRegistry` wraps it rather than replacing it, so
   provider name-conflict semantics stay consistent with the rest of the
   platform.

6. **`models/` holds only internal request shapes, not new domain
   types.** `PriceSeriesRequest` bundles the parameters of a price-series
   request into a single, validated, immutable object. It intentionally
   does not duplicate anything in `contracts` — it is a Data Engine
   operational detail (how a caller asks), not a platform domain concept
   (what the data means). Its only validation rule (`start <= end`) is
   structural, matching the "structural validation only" pattern already
   established in `contracts`.

7. **Only `MarketDataService` was implemented, not four parallel
   services.** `FundamentalsDataService`, `EconomicDataService`, and
   `AlternativeDataService` would follow an identical
   cache-then-provider composition pattern. Building all four now, with
   no real adapter to exercise any of them, would have been speculative
   duplication. `MarketDataService` exists as the one fully worked
   example; the other three should be added when their corresponding
   ports get a real adapter to coordinate.

   > **Partially superseded by Sprint 6.2.** `FundamentalsDataService`
   > now exists alongside `MarketDataService`. Economic and alternative
   > services remain deferred until their adapters land.

8. **No configuration-loading logic was implemented.**
   `DataEngineConfig` declares the *shape* of what the Data Engine needs
   to be configured with (a default provider, cache TTL, request
   timeout) but includes no environment-variable or file-loading code.
   How configuration is actually sourced is a platform-wide concern that
   belongs to its own future sprint, not something this package should
   decide unilaterally.

9. **No new exception subclasses beyond the generic root.**
   `DataEngineError` is the only exception type defined. Every error the
   current code can actually raise either uses it directly or reuses
   `Registry`'s own `KeyError`/`ValueError` (the same pattern
   `dsp.registry` already relies on). No `ProviderTimeoutError`,
   `RateLimitError`, etc. were speculatively added — those belong to
   whichever adapter first needs them.

### Sprint 2.2 — Provider Infrastructure

10. **`providers/` became a subpackage instead of one growing file.**
    Sprint 2.1's `providers/__init__.py` held two classes; Sprint 2.2
    adds four more (three enums are grouped as one module, plus
    capabilities, metadata, and a factory). Splitting into
    `enums.py`/`capabilities.py`/`metadata.py`/`registry.py`/`factory.py`
    with a barrel `__init__.py` keeps each concern in its own file
    without changing the public import path
    (`data_engine.providers.X` still works). This mirrors how
    `contracts.domain` is already organized.

11. **Capabilities are a `frozenset[DataCapability]`, not thirteen
    boolean dataclass fields.** The mission explicitly asked for
    capabilities to be "structured... instead of scattered boolean
    checks." A set of enum flags is the more literal reading of
    "structured": adding a fourteenth capability later means adding one
    `DataCapability` member, not touching `ProviderCapabilities`'s
    fields, `ProviderMetadata`'s constructor, or any call site's keyword
    arguments. `ProviderCapabilities.from_flags(...)` and the named
    boolean properties (`capabilities.crypto`, etc.) exist purely for
    ergonomics — they translate to/from the set, they don't replace it.

12. **`ProviderMetadata`'s shape changed from Sprint 2.1.** Sprint 2.1's
    `ProviderMetadata` had four flat `supports_*` booleans directly on
    it. Sprint 2.2 replaces them with a single `capabilities:
    ProviderCapabilities` field, per Objective 2 of this sprint's
    mission. This is a breaking change to `ProviderMetadata`'s
    constructor — it was made deliberately, is the sprint's literal
    deliverable, and all call sites in this package's own test suite
    were updated accordingly. Nothing in `dsp`, `core`, or `contracts`
    referenced the old shape, so the blast radius is contained entirely
    to `data_engine`. `data_engine.__version__` was bumped to `0.2.0` to
    mark the breaking change, mirroring how `core.__version__` was
    bumped in Sprint 1.2 for the same reason.

13. **`ProviderFactory` and `ProviderRegistry` are independent, composed
    classes, not one merged type.** A registry answers "what's
    available right now"; a factory answers "how do I build one from
    config". Keeping them separate means a provider can be registered
    without ever having a factory builder (e.g. a hand-constructed test
    fake), and a builder can be tested without touching a registry at
    all — exactly how `test_provider_factory.py` and `test_providers.py`
    exercise them independently in this sprint's test suite.

14. **`filter_by_capability`/`select_preferred` only consider `ACTIVE`
    providers; `get`/`get_metadata` do not filter by status at all.**
    Automatic discovery should not silently hand back a `DISABLED`,
    `DEPRECATED`, or even an `EXPERIMENTAL` provider — registering
    something as anything other than `ACTIVE` is a deliberate signal to
    keep it out of automatic selection until it's promoted. A direct,
    explicit lookup by id, by contrast, should always succeed if the id
    is registered, regardless of status — that's a deliberate request,
    not automatic discovery, so it isn't filtered.

15. **Rate limits and authentication requirements are descriptive, not
    enforced.** `RateLimitPolicy` and `AuthenticationType` let a
    provider declare what it needs; nothing in this package throttles
    requests or attaches credentials. Enforcing either is inherently
    tied to making a real HTTP call, which this sprint's mission
    explicitly excludes — building enforcement logic now, with nothing
    to enforce it against, would be speculative.

### Sprint 2.3 — Data Normalization & Transformation Framework

16. **`raw_models/` is a top-level sibling of `normalization/`, not
    nested inside it.** An adapter's job is to populate raw models
    (`Provider Adapter -> Raw Provider Response`); a normalizer's job
    is to consume them. Nesting `raw_models/` inside `normalization/`
    would force `adapters/` to import the normalization framework just
    to reach the raw model types it needs to populate. Keeping
    `raw_models/` dependency-free and independent means both
    `adapters/` and `normalization/` can depend on it without either
    depending on the other.

17. **Every raw-model value field is typed `Any`, on purpose.** A raw
    model's entire reason to exist is to hold data *before* it has been
    trusted enough to type strictly — a provider might report a price
    as `"102.5"`, `102.5`, or even `None`. Typing these fields as `Any`
    is the honest representation of "some value was reported, no claim
    about its shape," not a lapse in the "full typing" quality bar.
    Container fields (`extra`, `line_items`) are still typed precisely
    and frozen into read-only views in `__post_init__` — that is
    structural immutability enforcement, not content validation, so it
    doesn't contradict raw models being "unvalidated."

18. **A genuine `NormalizedBar` intermediate exists between raw and
    contract.** The mission's diagram names three distinct steps
    (Normalize, Validate, Construct Contracts). Validating directly
    against `RawMarketBar` would force every semantic check (OHLC
    consistency, volume) to re-implement ad hoc numeric coercion
    inside itself. Instead, `coerce_*` helpers turn a raw bar into a
    `NormalizedBar` with real `datetime`/`float` fields exactly once;
    every later validation stage and the final `PriceBar` construction
    can then assume those types are already correct.

19. **Presence/format checks run on raw items; semantic checks run on
    normalized records.** `RequiredFieldValidationStage` and
    `MissingValueValidationStage` run *before* coercion, against
    `RawMarketBar`, because they exist to catch garbage before
    attempting to interpret it as a number. `DuplicateDetectionStage`,
    `SortingVerificationStage`, `OHLCConsistencyStage`, and
    `VolumeValidationStage` run *after* coercion, against
    `NormalizedBar`, because they need real numeric/datetime
    comparisons. `TimestampValidationStage` is included in the
    post-coercion pipeline too — redundant with what `coerce_timestamp`
    already guarantees for this particular normalizer, but kept there
    deliberately as a cheap, defensive re-check and as a demonstration
    that the stage is genuinely reusable by pipelines that *don't*
    coerce timestamps themselves.

20. **The Validation Pipeline is not redundant with `contracts`'s own
    validation, even though both check similar things.**
    `contracts.PriceBar.__post_init__` will eventually catch the same
    OHLC/volume/timestamp problems on its own. The Validation Pipeline
    still exists as a distinct step because it runs *before* any
    `contracts` object is constructed (so bad data is never even
    attempted to be packed into one) and produces a
    provider-attributed, field-specific message (`InvalidProviderDataError:
    provider 'yahoo_finance' returned...`) rather than a generic
    `ContractValidationError` with no provenance. `contracts` remains
    the last-resort safety net; the Validation Pipeline is the
    first-resort diagnostic layer.

21. **Validation stages are parameterized by field names or
    key-extraction callables, never hard-coded to `RawMarketBar` or
    `NormalizedBar`.** This is what makes "validation should be
    composable" concretely true: the same `DuplicateDetectionStage`
    class, for example, can check for duplicate timestamps in bars
    today and duplicate observation dates in economic points tomorrow,
    just by passing a different `key=` callable — no stage subclassing
    required.

22. **`NormalizationError` and `TransformationError` are siblings, not
    parent/child.** `NormalizationError` (and its subclasses
    `InvalidProviderDataError`, `MissingFieldError`) means "this
    specific piece of provider data is bad" — raised by validation
    stages and coercion helpers, always with a provider-attributed
    message, and always propagated unchanged by `TransformationPipeline`
    so callers can distinguish bad data from a pipeline bug.
    `TransformationError` means "the pipeline itself could not
    complete" for a reason *not* already covered by a validation stage
    — for example a `contracts` construction failure that slipped past
    every configured check, which would indicate a gap in the
    Validation Pipeline's own coverage rather than a plain data-quality
    issue. Keeping them as siblings under `DataEngineError` (rather
    than making `TransformationError` a `NormalizationError` subclass)
    keeps that distinction visible at the type level.

23. **Only `DefaultMarketDataNormalizer` was implemented; the other
    three normalizers have interfaces only.** `FundamentalNormalizer`,
    `EconomicDataNormalizer`, and `AlternativeDataNormalizer` are fully
    specified ABCs so adapters can already depend on them, but a
    concrete default implementation is deferred until a real provider
    needs one — the same restraint already applied to
    `MarketDataService` (Sprint 2.1, Decision 7) and to
    `filter_by_capability` consumers (Sprint 2.2). Market data has the
    richest, most explicit set of validation requirements in the
    mission (timestamp, duplicate, sorting, OHLC, volume all map
    directly onto bars), making it the natural fully-worked example;
    the other three follow an identical
    coerce/validate/construct pattern once a provider needs them.

24. **`TransformationPipeline` takes its coerce/construct steps as
    injected callables, not as abstract methods to override.** This is
    dependency inversion applied to functions rather than objects: a
    concrete normalizer *composes* a `TransformationPipeline` instance
    with plain functions/lambdas instead of subclassing a pipeline base
    class. This keeps the pipeline itself completely provider-agnostic
    and testable in isolation (see `test_transformation_pipeline.py`,
    which exercises it with plain `int`/`str` types and no `contracts`
    or raw-model dependency at all).

### Sprint 2.4 — Yahoo Finance Provider Adapter

25. **`YahooFinanceAdapter` lives in its own subpackage
    (`adapters/yahoo_finance/`), not as a single file in `adapters/`.**
    A concrete adapter needs at least three concerns that don't belong
    in one class: the adapter itself, an isolated HTTP layer, and
    registration wiring (metadata + a factory builder). Splitting
    these into `adapter.py`/`http_client.py`/`registration.py` behind
    one barrel `__init__.py` keeps each concern independently testable
    (see the three separate test files) and gives every future adapter
    an obvious, consistent place to live —
    `adapters/<provider_id>/` — rather than one flat, growing
    `adapters/` module.

26. **`ProviderRequestError` is a new `DataEngineError` **sibling** of
    `NormalizationError`, not a subclass of it.** Before this sprint,
    every failure mode the Data Engine could describe assumed a
    response had already been received and was merely bad
    (`NormalizationError` and its subclasses). There was no existing
    type for "no response was received at all" (a network error, a
    timeout, a non-2xx status, an unparsable body) — and forcing that
    into `NormalizationError`'s hierarchy would blur a real
    distinction a caller might care about: "the provider is
    unreachable" vs. "the provider answered but the data is wrong."
    This is the sprint's only new exception type, added because no
    existing one covered this failure mode — consistent with the
    restraint Design Decision 9 already established.

27. **The HTTP client (`JsonHttpClient`/`UrllibJsonHttpClient`) knows
    nothing about Yahoo Finance.** It is a generic "GET a URL, parse
    JSON, translate transport failures" utility with no vendor-specific
    URL structure, query parameters, or response-shape knowledge —
    that all lives in `YahooFinanceAdapter` itself. It is physically
    located inside `adapters/yahoo_finance/` only because no second
    adapter exists yet to justify promoting it to a shared,
    top-level location; either class could be reused as-is by a future
    HTTP-based adapter without modification. This is what lets the
    mission's "the adapter should be the only class aware of Yahoo
    Finance" requirement hold literally: the HTTP client, the
    normalization framework, and the provider registry are all
    reused completely unaware of which vendor, if any, sits behind
    them.

28. **`YahooFinanceAdapter` is deliberately synchronous, built on
    `urllib` from the standard library rather than a new dependency
    like `requests` or `httpx`.** This keeps Design Decision 1 (ports
    stay synchronous until a real adapter's I/O forces the question)
    honestly unresolved rather than silently deciding it via a
    dependency choice, and avoids adding a new runtime dependency to
    `pyproject.toml` for a sprint whose mission explicitly excludes
    retries, connection pooling, and async I/O. `JsonHttpClient` is a
    `Protocol`, so swapping in an async-capable or connection-pooled
    implementation later requires no change to `YahooFinanceAdapter`
    itself, only a different object passed to its constructor.

29. **A raw bar is only skipped as "no trading session" if *every*
    OHLC field is `None`; a *partial* null is treated as bad data,
    not a special case.** Yahoo Finance represents exchange holidays
    and other non-trading timestamps within a requested range as a
    bar where `open`/`high`/`low`/`close` are all `null`. Silently
    dropping such a bar is a legitimate, minimal piece of
    provider-specific mapping — it reflects a known fact about how
    this specific vendor represents "no data for this day," not a
    validation workaround. Any *other* combination (e.g. `close` is
    `None` but `open` is not) is passed through unchanged to the
    normalizer, which correctly rejects it with `MissingFieldError` —
    the adapter never tries to "fix" or interpret genuinely malformed
    data itself.

30. **The adapter raises its own `InvalidProviderDataError` for an
    empty raw series *before* calling the normalizer, rather than
    relying on the normalizer to reject it.** As recorded under Known
    Architectural Issues, `DefaultMarketDataNormalizer.normalize()`
    does not itself guard against zero raw bars. Rather than fix that
    in the "stable" Normalization Framework (out of scope for this
    sprint), `YahooFinanceAdapter` guards against it at its own
    boundary — consistent with "translate provider failures into Data
    Engine exceptions; do not leak provider-specific exceptions,"
    applied here to a normalization-framework gap rather than a
    provider-specific one.

31. **Both the HTTP call and the normalizer call are wrapped to
    translate *any* unexpected exception, not just the ones each is
    documented to raise.** `_fetch_chart_payload` catches
    `DataEngineError` and re-raises it unchanged, but wraps anything
    else as `DataEngineError`; `get_price_series` does the same around
    `normalizer.normalize(...)`, wrapping unexpected exceptions as
    `TransformationError`. This is deliberate defense-in-depth against
    exactly the kind of gap described above: even if a future change
    to `http_client.py` or `normalization/` introduces a new
    unwrapped exception type, `YahooFinanceAdapter` still guarantees
    callers only ever see `DataEngineError` subclasses — never a raw
    `urllib` exception, a `contracts` exception, or anything else.

32. **Sprint 6.2 stops at `FundamentalStatement`, not `FinancialSnapshot`.**
    `FinancialSnapshot` is an engine-local type in `fundamental.models`.
    Importing it from `data_engine` would invert the dependency rule.
    `FundamentalStatementsBuilder` therefore produces the ordered
    contracts tuple that `FinancialSnapshot` wraps; Sprint 6.4 performs
    the wrap in a layer allowed to depend on both packages.

33. **Ratios, shares outstanding, market cap, and enterprise value go
    into `extra_line_items`, not new Contracts fields.**
    `FundamentalStatement` deliberately stores as-reported line items
    only. Extending Contracts mid-sprint would redesign a stable package.
    Market/ratio metrics remain available to engines via extras until a
    deliberate Contracts evolution decides otherwise.

34. **Fundamentals use a separate provider id
    (`yahoo_finance_fundamentals`) rather than extending
    `YahooFinanceAdapter`.** The registry is one-adapter-per-id. Keeping
    OHLCV and fundamentals as sibling adapters preserves capability
    filtering (`MARKET_DATA` vs `FUNDAMENTALS`) and avoids modifying the
    stable Sprint 2.4 adapter beyond reuse of `JsonHttpClient`.

35. **`coerce_optional_float` returns `None` for missing values, unlike
    volume's `0.0` default.** As-reported financials must not invent
    zeros for omitted line items; analyzers already treat `None` as
    "unavailable."

36. **Sprint 6.3 chooses FRED over Yahoo for macroeconomic data.** FRED
    is the institutional source of record for US macro series, exposes a
    stable observations API, and maps cleanly onto
    `contracts.EconomicSeries`. Yahoo remains the market/fundamentals
    vendor; economic series stay on a dedicated adapter so capability
    filtering (`ECONOMIC_DATA`) stays accurate.

37. **FRED missing observations (`"."`) are skipped, not fatal.** This
    mirrors Yahoo's all-null OHLCV holiday bars: a known vendor sentinel
    for "no value," not malformed data. After skipping, an empty series
    still raises `InvalidProviderDataError`.

38. **`EconomicDataService.get_available_series` is the graceful
    multi-indicator path.** The port remains strict (one series or
    error). The service-level batch helper omits failures so Sprint 6.4
    can build a partial `EconomicSnapshot` without redesigning the port.

39. **Platform indicator codes are canonical; FRED series ids stay in
    `adapters/fred/catalog.py`.** Engines and orchestration never see
    `CPIAUCSL` / `FEDFUNDS` — only `CPI` / `INTEREST_RATE`.

## Extensibility Notes

`YahooFinanceAdapter` is now the worked example — not a hypothetical
one — for adding a real provider. Adding the *next* one (Alpha
Vantage, Polygon, FMP, Twelve Data, NSE, RBI, FRED, Quandl, CoinGecko,
...) means:

1. Writing a concrete class subclassing `BaseAdapter` and whichever
   port(s) it implements, in its own `adapters/<provider_id>/`
   subpackage (see Design Decision 25).
2. Inside that port method, fetching the vendor's response — via an
   isolated HTTP layer, following `http_client.py`'s pattern if useful
   — and mapping it onto the matching raw model
   (e.g. `RawMarketBar`/`RawMarketSeries`). This is the *only*
   provider-specific code the adapter needs to write.
3. Passing the populated raw model to the matching normalizer —
   `DefaultMarketDataNormalizer` for market data today — and returning
   whatever `contracts` object it hands back. No adapter implements its
   own validation or transformation logic.
4. Declaring its `ProviderMetadata` (capabilities, rate limit,
   authentication type), following `registration.py`'s pattern.
5. Registering a `ProviderFactory` builder so it can be constructed
   from configuration instead of by hand.
6. Registering the constructed adapter, with its metadata, into a
   `ProviderRegistry` — this package never does that registration
   itself; wiring belongs to whoever composes the running application (a
   future bootstrap step or the `orchestration` package). See
   `register_yahoo_finance` for the reference pattern.
7. Deciding, at that point, whether the new adapter's I/O should push the
   ports back toward `async def` (see Design Decision 1) — Yahoo
   Finance's adapter stayed synchronous (Design Decision 28); a future
   adapter with a stricter latency budget might not.

None of this required touching `contracts` or `core` for Yahoo
Finance, and it should not for the next provider either — only
additive work.

### Example: how `YahooFinanceAdapter` is registered

This is the actual registration pattern, taken directly from
`data_engine.adapters.yahoo_finance.registration` — nothing below is
hypothetical:

```python
from data_engine.providers import DataCapability, ProviderFactory, ProviderRegistry
from data_engine.adapters.yahoo_finance import register_yahoo_finance

# 1. An application composes its own factory and registry — data_engine
#    never constructs these on its own behalf.
factory = ProviderFactory()
providers = ProviderRegistry()

# 2. register_yahoo_finance() builds YahooFinanceAdapter via a
#    ProviderFactory builder and registers it, with its ProviderMetadata,
#    into the ProviderRegistry — the same two-step sequence any other
#    provider would follow.
adapter = register_yahoo_finance(factory, providers, {"timeout_seconds": 5.0})

# 3. Consuming code never imports YahooFinanceAdapter directly.
best = providers.select_preferred(DataCapability.MARKET_DATA, DataCapability.DAILY)
```

And how `MarketDataService` retrieves data through it without ever
importing `YahooFinanceAdapter`:

```python
from datetime import date

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, BarFrequency
from data_engine.cache import InMemoryCache
from data_engine.models import PriceSeriesRequest
from data_engine.services import MarketDataService

service = MarketDataService(
    providers=providers, cache=InMemoryCache(), default_provider="yahoo_finance"
)
aapl = Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")
request = PriceSeriesRequest(
    instrument=aapl,
    frequency=BarFrequency.DAILY,
    start=date(2024, 1, 1),
    end=date(2024, 12, 31),
)
series = service.get_price_series(request)  # a contracts.PriceSeries
```

### Example: fundamentals registration (Sprint 6.2)

```python
from contracts.enums import StatementPeriodType
from data_engine.adapters.yahoo_finance import register_yahoo_finance_fundamentals
from data_engine.cache import InMemoryCache
from data_engine.models import FundamentalsRequest
from data_engine.providers import DataCapability, ProviderFactory, ProviderRegistry
from data_engine.services import FundamentalsDataService

factory = ProviderFactory()
providers = ProviderRegistry()
register_yahoo_finance_fundamentals(factory, providers)

service = FundamentalsDataService(
    providers=providers,
    cache=InMemoryCache(),
    default_provider="yahoo_finance_fundamentals",
)
statements = service.get_fundamental_statements(
    FundamentalsRequest(instrument=aapl, period_type=StatementPeriodType.ANNUAL, limit=4)
)
# statements -> tuple[FundamentalStatement, ...] most-recent-first
# Sprint 6.4: FinancialSnapshot(instrument=aapl, statements=statements)
```

## Sprint 6.3 — Economic Data Flow (FRED)

```
FRED observations API
        │
        ▼
FredEconomicAdapter              (catalog resolve → RawEconomicSeries)
        │
        ▼
RawEconomicSeries                (provider-neutral points + frequency)
        │
        ▼
DefaultEconomicNormalizer        (skip "." → coerce → sort → contracts)
        │
        ▼
EconomicSeries                   (contracts; ascending, duplicate-free)
        │
        ▼
EconomicSeriesBuilder            (optional limit / identity checks)
        │
        ▼
EconomicDataService              (cache + registry; get_available_series)
        │
        ▼
[Sprint 6.4] EconomicSnapshot    (economic package — not built here)
        │
        ▼
Economic Engine
```

### Sequence (GDP request)

```
Caller                EconomicDataService      Registry / FredAdapter         Normalizer
  │                          │                          │                        │
  │ EconomicRequest(GDP,US)  │                          │                        │
  │─────────────────────────▶│ get(fred)                │                        │
  │                          │─────────────────────────▶│                        │
  │                          │ get_economic_series      │                        │
  │                          │─────────────────────────▶│ HTTP observations      │
  │                          │                          │──────▶ FRED            │
  │                          │                          │◀───── JSON             │
  │                          │                          │ RawEconomicSeries      │
  │                          │                          │───────────────────────▶│
  │                          │                          │◀── EconomicSeries      │
  │                          │ Builder.build(limit?)    │                        │
  │◀──── EconomicSeries (contracts only)                                         │
```

### Series mapping table (platform → FRED)

| Platform code | Aliases | FRED `series_id` | Frequency |
|---|---|---|---|
| `GDP` | — | `GDP` | quarterly |
| `CPI` | `INFLATION` | `CPIAUCSL` | monthly |
| `INTEREST_RATE` | `FEDFUNDS` | `FEDFUNDS` | monthly |
| `PMI` | — | `NAPM` | monthly |
| `M2` | `MONEY_SUPPLY`, `LIQUIDITY` | `M2SL` | monthly |
| `UNEMPLOYMENT` | `UNRATE` | `UNRATE` | monthly |
| `INDPRO` | `INDUSTRIAL_PRODUCTION` | `INDPRO` | monthly |

Unsupported codes and non-`US` countries raise clear `DataEngineError`.
`EconomicDataService.get_available_series` skips failures so Sprint 6.4
can assemble a partial snapshot without aborting the pipeline.

### Example: FRED registration

```python
from data_engine.adapters.fred import register_fred
from data_engine.cache import InMemoryCache
from data_engine.models import EconomicRequest
from data_engine.providers import ProviderFactory, ProviderRegistry
from data_engine.services import EconomicDataService

factory = ProviderFactory()
providers = ProviderRegistry()
register_fred(factory, providers, {"api_key": "YOUR_FRED_KEY"})

service = EconomicDataService(
    providers=providers, cache=InMemoryCache(), default_provider="fred"
)
gdp = service.get_economic_series(
    EconomicRequest(indicator_code="GDP", country="US", limit=8)
)
bundle = service.get_available_series(
    indicator_codes=("GDP", "CPI", "INTEREST_RATE", "PMI", "M2"),
    country="US",
)
```
