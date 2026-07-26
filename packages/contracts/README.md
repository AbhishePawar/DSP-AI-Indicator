<!-- ASI-005-PACKAGE-CARD -->
# contracts

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

DSP AI Indicator shared kernel — domain contracts and explainability primitives

## 2. Responsibilities

Provide the stable `contracts` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Production · Frozen (shared kernel)** · Version **0.3.0** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`__all__` exports (28): `AnalyticalStance`, `AssetClass`, `BarFrequency`, `ContractError`, `ContractValidationError`, `EconomicContext`, `EconomicDataPoint`, `EconomicFrequency`, `EconomicSeries`, `EngineSource`, `Evidence`, `Explanation`, … (+16)

## 5. Package Structure

`packages/contracts/src/contracts/` · `packages/contracts/tests/` · local `pyproject.toml` when present.

## 6. Dependencies

*(none declared)*

## 7. Architecture Notes

Architecture allowlists / freeze policy apply. See appendix and [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
import contracts
print(contracts.__version__)
```

Worked examples live in `packages/contracts/tests/`.

## 9. Testing

```bash
pytest packages/contracts/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

# Contracts

**Contracts is the Shared Kernel of the DSP AI Indicator platform.**

It defines the domain models, enumerations, and explainability primitives that every current and future engine — Data, Indicator, Fundamental, Economic, Valuation, Behavioral, Portfolio Intelligence, Risk, AI Investment Committee, Research, and beyond — uses to communicate with every other engine.

This package implements Sprint 1.1 of the platform roadmap defined in [`docs/DSP_AI_INDICATOR_ARCHITECTURE.md`](../../docs/DSP_AI_INDICATOR_ARCHITECTURE.md). Read that document first; this README explains only how to use and extend this specific package.

## Purpose

Before this package existed, every engine would have been free to invent its own shape for "a price," "a company statement," or "a recommendation." That would silently break Clean Architecture and Modular Architecture the moment two engines needed to exchange data. Contracts exists to make that impossible: it is the single, canonical vocabulary the entire platform speaks.

Contracts is deliberately the *only* package with no dependency on the rest of the platform. Every other package — including `core` — depends on it, directly or indirectly. This is what allows any engine to be built, replaced, or reasoned about in isolation while still guaranteeing interoperability with every other engine.

## Responsibilities

Contracts is responsible for, and only for:

- **Domain entities and value objects** — `Instrument`, `PriceBar`, `PriceSeries`, `FundamentalStatement`, `EconomicSeries` (with `EconomicDataPoint`), `Signal`, `Recommendation`.
- **Explainability primitives** — `Explanation` (why a computed value has the value it has) and `Evidence` (a discrete supporting fact for a claim or decision). These give Design Principle 3, "Explainable AI," a concrete type that every engine can attach to its output.
- **Shared enumerations** — `AssetClass`, `BarFrequency`, `StatementPeriodType`, `EconomicFrequency`, `SignalDirection`, `RecommendationAction`, `EngineSource`.
- **A minimal, self-contained exception hierarchy** — `ContractError` and `ContractValidationError`, used only for structural/data-integrity validation.
- **Structural validation** — type checks, finiteness checks, range checks, chronological ordering, timezone-awareness. Contracts rejects a `PriceBar` whose `low` exceeds its `high`, for example, because that is a data-integrity defect, not a business decision.

Contracts explicitly does **not** contain:

- Business logic or business rules (ratio calculations, valuation models, portfolio construction, risk scoring, AI reasoning, etc.).
- Any computation derived from the data it models (returns, moving averages, growth rates, and similar derived metrics belong to the engine that owns that computation).
- I/O of any kind (no network calls, no file access, no database access).
- Any import of, or dependency on, another platform package.

## Dependency Rules

Per Section 4 of the platform architecture specification:

> A package may depend only on packages that appear at or above its own position in the platform pipeline. Contracts appears first, so **Contracts may depend on nothing in this platform.**

Concretely:

- Contracts depends **only on the Python standard library** (`dataclasses`, `datetime`, `enum`, `math`). It has zero third-party runtime dependencies and zero dependencies on `core` or any engine package.
- **No package in this platform may be imported by Contracts.** Not `core`, not `data-engine`, not any analytical engine, not `orchestration`, not any service.
- **Every other package in the platform may depend on Contracts.** This is the one dependency edge that is always safe to add.
- Contracts must never import anything from `packages/dsp` (the existing Indicator Engine implementation) or `packages/core`. If a future change to Contracts seems to require either, that is a signal the change belongs in a different package, not evidence that Contracts needs a new dependency.

This is why Contracts defines its own exception hierarchy (`ContractError`/`ContractValidationError`) instead of reusing `core.exceptions.DSPAIError` — `core` depends on `contracts`, not the other way around, so Contracts cannot reference anything in `core`.

## How Future Engines Should Use These Contracts

1. **Never invent a parallel shape for a concept that already exists here.** If an engine needs to represent a price observation, a financial statement, or a recommendation, it uses `PriceBar`, `FundamentalStatement`, or `Recommendation` from this package — it does not define its own dict, tuple, or ad hoc class for the same concept.
2. **Cross a package boundary only with a Contracts type.** A function's public signature that crosses from one engine's package into another's must accept or return a Contracts type (or a plain built-in like `str`/`int` for identifiers), never a raw NumPy array, DataFrame, or engine-internal object.
3. **Attach an `Explanation` to anything that could influence a downstream decision.** If an engine computes a value that will ever be shown to a user or consumed by the AI Investment Committee, it should also produce an `Explanation` (or wrap the value in an `Evidence`) describing how that value was derived.
4. **Extend by adding a new contract or a new enum value, not by repurposing an existing field.** If a new engine needs a domain concept that doesn't fit any existing contract, propose a new dataclass in `contracts/domain/`, following the same immutability and validation conventions as the existing models — do not overload an existing field with a different meaning.
5. **Tag provenance using `EngineSource`, not by importing the engine.** `Explanation.source_engine` and `Evidence.source_engine` exist precisely so that provenance can be recorded without Contracts (or any consumer of these types) needing to import the producing engine's package.
6. **Treat every contract as immutable.** All dataclasses in this package are `frozen=True` and use `__slots__`. Engines must construct new instances rather than mutate existing ones — this is required for the platform's reproducibility and auditability goals.

## Package Structure

```
packages/contracts/
├── README.md
├── src/
│   └── contracts/
│       ├── __init__.py          # public API surface
│       ├── enums.py             # shared enumerations
│       ├── exceptions.py        # ContractError, ContractValidationError
│       ├── _validation.py       # private structural-validation helpers
│       └── domain/
│           ├── __init__.py      # domain model exports
│           ├── instrument.py
│           ├── price_bar.py
│           ├── price_series.py
│           ├── fundamental_statement.py
│           ├── economic_series.py
│           ├── explanation.py
│           ├── evidence.py
│           ├── signal.py
│           └── recommendation.py
└── tests/
    ├── conftest.py
    └── test_*.py                # one test module per domain contract
```

## Usage Example

```python
from datetime import UTC, datetime

from contracts import (
    AssetClass,
    EngineSource,
    Evidence,
    Instrument,
    Recommendation,
    RecommendationAction,
)

instrument = Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")

evidence = Evidence(
    source_engine=EngineSource.VALUATION_ENGINE,
    claim="DCF fair value exceeds current price by 20%.",
    weight=0.8,
)

recommendation = Recommendation(
    instrument=instrument,
    action=RecommendationAction.BUY,
    conviction=0.75,
    rationale="Undervalued relative to intrinsic value with favorable macro backdrop.",
    generated_at=datetime.now(UTC),
    supporting_evidence=[evidence],
)
```

## Running Tests

From the repository root (after installing the project in editable mode with dev dependencies):

```bash
pytest packages/contracts/tests
```
