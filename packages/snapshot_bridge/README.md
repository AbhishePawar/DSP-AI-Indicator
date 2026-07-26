<!-- ASI-005-PACKAGE-CARD -->
# snapshot_bridge

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

DSP Snapshot Bridge — contracts to engine-native snapshots

## 2. Responsibilities

Provide the stable `snapshot_bridge` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Production · Frozen** · Version **0.1.0** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`__all__` exports (5): `EconomicBridgeService`, `EconomicSnapshotBuilder`, `FinancialBridgeService`, `FinancialSnapshotBuilder`, `SnapshotBridgeError`

## 5. Package Structure

`packages/snapshot_bridge/src/snapshot_bridge/` · `packages/snapshot_bridge/tests/` · local `pyproject.toml` when present.

## 6. Dependencies

`contracts`, `core`, `data_engine`, `economic`, `fundamental`

## 7. Architecture Notes

Architecture allowlists / freeze policy apply. See appendix and [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
import snapshot_bridge
print(snapshot_bridge.__version__)
```

Worked examples live in `packages/snapshot_bridge/tests/`.

## 9. Testing

```bash
pytest packages/snapshot_bridge/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

# Snapshot Bridge

Sprint 6.4 completes the **data plane** by translating Data Engine
`contracts` outputs into the engine-native snapshot types analytical
engines were designed to consume.

This package is an **integration / bridge layer**. It is not a provider,
not an engine, and not a committee.

## Responsibilities

- `FundamentalStatement[]` → `FinancialSnapshot`
- `EconomicSeries` map → `EconomicSnapshot` (with derived metrics)
- Optional bridge services that compose Data Engine services with builders

## Non-responsibilities

- HTTP / provider I/O
- Engine analysis / scoring
- Committee deliberation
- Constructing snapshots inside `data_engine` (forbidden reverse deps)

## Folder Structure

```
packages/snapshot_bridge/
├── README.md
├── src/snapshot_bridge/
│   ├── __init__.py              # public API
│   ├── exceptions.py            # SnapshotBridgeError
│   ├── financial.py             # FinancialSnapshotBuilder
│   ├── economic.py              # EconomicSnapshotBuilder
│   ├── derivation.py            # YoY / percent / liquidity helpers
│   └── services.py              # FinancialBridgeService, EconomicBridgeService
└── tests/
    ├── test_financial_builder.py
    ├── test_economic_builder.py
    └── test_services.py
```

## Dependency Diagram

```
                 contracts
                     ▲
                     │
        ┌────────────┼────────────┐
        │            │            │
   data_engine   fundamental   economic
        ▲            ▲            ▲
        │            │            │
        └────────────┼────────────┘
                     │
              snapshot_bridge
                     │
                     ▼
              (orchestration — Sprint 7.0)
```

Rules:

- `snapshot_bridge` → `contracts`, `core`, `data_engine`, `fundamental`, `economic`
- `data_engine` never imports `fundamental` / `economic` / `snapshot_bridge`
- engines never import `snapshot_bridge`

## Bridge Architecture

```
Data Engine                          Snapshot Bridge                 Engines
───────────                          ───────────────                 ───────
FundamentalsDataService ──statements──▶ FinancialSnapshotBuilder ──▶ FundamentalEngine
EconomicDataService ──────series map──▶ EconomicSnapshotBuilder ───▶ EconomicEngine
```

Builders are pure (no I/O). Bridge services are thin wrappers for
orchestration convenience.

## Sequence Diagram

```
Orchestration          EconomicBridgeService       EconomicDataService       Builder
     │                          │                          │                   │
     │ get_snapshot(US)         │                          │                   │
     │─────────────────────────▶│ get_available_series     │                   │
     │                          │─────────────────────────▶│                   │
     │                          │◀── {GDP, CPI, ...}       │                   │
     │                          │ build(series_map)                            │
     │                          │─────────────────────────────────────────────▶│
     │                          │◀── EconomicSnapshot                          │
     │◀── EconomicSnapshot      │                          │                   │
```

## Transformation Tables

### Financial

| Input | Output |
|---|---|
| `tuple[FundamentalStatement, ...]` (any order) | `FinancialSnapshot` (most-recent-first) |
| Line items (revenue, income, assets, …) | Preserved on statements; analyzers derive margins/ROE/growth |

### Economic

| Series | Snapshot field | Derivation |
|---|---|---|
| `GDP` | `gdp_growth` | YoY level change (decimal) |
| `CPI` | `cpi_inflation` | YoY index change (decimal) |
| `INTEREST_RATE` | `interest_rate` | Latest level ÷ 100 |
| `INTEREST_RATE` | `interest_rate_change` | Δ pp ÷ 100 |
| `UNEMPLOYMENT` | `unemployment` | Latest level ÷ 100 |
| `PMI` | `pmi` | Latest index (unchanged) |
| `M2` | `liquidity_indicator` | YoY growth → `[0, 1]` |
| (none) | `currency_trend` | Always `None` today |

Missing series → corresponding field `None` (engine emits neutral/unavailable).

## Design Decisions

1. **New package, not `data_engine`.** Prevents reverse deps onto engines.
2. **Builders are pure; services optional.** Orchestration can inject either.
3. **Reuse `FundamentalStatementsBuilder`.** Single source of ordering rules.
4. **Economic derivation matches engine decimals.** FRED percent levels are
   converted; YoY growth is fractional.
5. **Liquidity is a bridge concern.** M2 → `[0, 1]` mapping lives here so
   the Economic Engine stays unchanged.
6. **No `dsp` / `ai_committee` dependency.** Keeps the bridge focused on
   the data-plane → analysis-plane handoff.

## Public API

```python
from snapshot_bridge import (
    FinancialSnapshotBuilder,
    EconomicSnapshotBuilder,
    FinancialBridgeService,
    EconomicBridgeService,
    SnapshotBridgeError,
)
```

## Example

```python
from snapshot_bridge import EconomicSnapshotBuilder, FinancialSnapshotBuilder

financial = FinancialSnapshotBuilder.build(instrument, statements)
economic = EconomicSnapshotBuilder.build(
    {"GDP": gdp_series, "CPI": cpi_series, "INTEREST_RATE": rates},
    country="US",
)
```
