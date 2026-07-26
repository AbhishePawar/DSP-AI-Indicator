<!-- ASI-005-PACKAGE-CARD -->
# core

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

DSP AI Indicator technical foundation — exceptions, validation, registry

## 2. Responsibilities

Provide the stable `core` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Production · Frozen (technical foundation)** · Version **0.2.0** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`__all__` exports (6): `DSPAIError`, `Registry`, `ValidationError`, `create_output_array`, `validate_period`, `validate_prices`

## 5. Package Structure

`packages/core/src/core/` · `packages/core/tests/` · local `pyproject.toml` when present.

## 6. Dependencies

*(none declared)*

## 7. Architecture Notes

Architecture allowlists / freeze policy apply. See appendix and [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
import core
print(core.__version__)
```

Worked examples live in `packages/core/tests/`.

## 9. Testing

```bash
pytest packages/core/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

# Core

**Core is the generic technical foundation of the DSP AI Indicator platform.**

It provides shared exceptions, numeric validation utilities, and generic registry infrastructure that every engine builds on. This package implements Sprint 1.2 of the platform roadmap defined in [`docs/DSP_AI_INDICATOR_ARCHITECTURE.md`](../../docs/DSP_AI_INDICATOR_ARCHITECTURE.md). Read that document first; this README explains only how to use and extend this specific package.

## Purpose

Core exists so that every engine has a single, consistent place to get generic, non-domain-specific building blocks: an exception hierarchy to derive from, numeric input validation, and a registry pattern for anything an engine wants to make pluggable by name. Without Core, every engine would reinvent its own validation helpers and its own ad hoc `dict`-based registry — exactly the kind of drift the platform's Modular Architecture and Extensibility principles are designed to prevent.

Core sits directly above [`contracts`](../contracts/README.md) in the platform's dependency order. It has no knowledge of instruments, prices, statements, or recommendations — those concepts live in Contracts. Core only knows about generic technical concerns: is this number valid, is this name already registered, what error type should this failure raise.

## Responsibilities

Core is responsible for, and only for:

- **A generic exception hierarchy** — `DSPAIError` (root) and `ValidationError` (generic input-validation failures). Every engine's own exceptions should derive from `DSPAIError`, directly or through an engine-specific intermediate base (see `dsp.exceptions.IndicatorError` for the pattern every future engine should follow).
- **Numeric validation utilities** — `validate_period`, `validate_prices`, `create_output_array`. These operate on plain numeric arrays and integers; they know nothing about what the numbers represent.
- **Generic registry infrastructure** — `Registry[T]`, a name-keyed, case-insensitive registry any engine can instantiate to register and discover pluggable implementations (indicators, valuation models, AI agents, data providers, etc.) without depending on what `T` actually is.

Core explicitly does **not** contain:

- Market, indicator, valuation, portfolio, or recommendation logic or vocabulary.
- Business rules of any kind.
- Data-provider logic or I/O.
- Domain entities — those are Contracts' responsibility (see below).

### What changed in Sprint 1.2 and why

Reviewing Core against the architecture document surfaced three violations of "Core must never contain market/indicator logic," all now corrected:

1. **`core.enums.IndicatorName` (removed).** A static enum of indicator names is indicator-domain vocabulary, and it was already unused — `dsp.registry` never referenced it. It has not been relocated anywhere: the Indicator Engine's registry is itself the dynamic, extensible source of truth for valid indicator names, and a parallel static enum would have worked against the Extensibility principle (every new indicator would require updating two places instead of one).
2. **`core.exceptions.IndicatorError` (moved to `dsp.exceptions.IndicatorError`).** An indicator-specific exception has no business living in Core's generic hierarchy. It now lives in the Indicator Engine, deriving from `core.exceptions.DSPAIError` — the pattern every future engine should copy for its own domain-specific errors.
3. **`core.entities.PriceSeries` (removed).** This was a second, competing representation of "a price series" — the very concept Contracts now owns canonically via `contracts.domain.PriceSeries`/`PriceBar`. It was unused outside its own tests (the Indicator Engine has always operated on plain arrays via `core.validation.validate_prices`), so removing it is fully backward compatible. Any future engine that needs to model a price series should use the Contracts version, not reintroduce one in Core.
4. **`core.registry.Registry` (added).** Core previously had no generic registry infrastructure at all, despite the architecture document explicitly listing it as a Core responsibility. `dsp.registry` has been refactored to delegate to it internally — its public API and behavior are unchanged, but the underlying "register by name, look up, list" mechanism is now shared, reusable infrastructure instead of logic duplicated inside the Indicator Engine.

## Dependency Rules

Per Section 4 of the platform architecture specification, Core may depend on `contracts` and nothing else in this platform:

- Core depends on **`contracts`** (permitted) and the Python standard library. It does not currently import anything from `contracts` — there is no concrete Core utility yet that needs a Contracts type — but the dependency is allowed and expected to be exercised naturally as soon as one arises (e.g. a future generic helper that validates a `PriceSeries` structurally rather than a raw array).
- Core must **never** depend on `dsp`, any other engine, `orchestration`, or any service. Dependencies only flow one way: engines depend on Core, Core never depends on an engine.
- **Every engine may depend on Core.** This is one of the two dependency edges (alongside depending on `contracts`) that is always safe to add.
- Core must never import anything from `packages/dsp` or any future engine package. If a future change to Core seems to require it, that is a signal the change belongs in the engine, not evidence that Core needs a new dependency.

## How Engines Should Use Core

1. **Derive engine-specific exceptions from `core.exceptions.DSPAIError`.** Don't raise bare `Exception`, `ValueError`, or `KeyError` from business logic — define an engine-specific error (as `dsp.exceptions.IndicatorError` does) so callers can catch by engine or by the shared root.
2. **Reuse `core.validation` for generic numeric checks** (period validation, finite-array validation, NaN-filled output arrays) rather than re-implementing the same checks inside an engine.
3. **Build pluggable extension points on `core.registry.Registry`, not a new `dict`.** If an engine needs "register an X by name, look one up, list them all" (valuation models, AI agents, data providers), instantiate a `Registry[YourType]` with an appropriate `kind` label and wrap it the same way `dsp.registry` wraps its `Registry[type[Indicator]]` — domain-specific behavior (like instantiating with a period) stays in the engine's wrapper functions, not in the registry itself.
4. **Never put a domain entity in Core.** If a concept represents actual platform data (a price, a statement, a recommendation), it belongs in `contracts`, not here — propose it there instead.

## Package Structure

```
packages/core/
├── README.md
├── src/
│   └── core/
│       ├── __init__.py       # public API surface
│       ├── exceptions/
│       │   └── __init__.py   # DSPAIError, ValidationError
│       ├── validation.py     # validate_period, validate_prices, create_output_array
│       └── registry.py       # generic Registry[T]
└── tests/
    ├── test_validation.py
    └── test_registry.py
```

## Usage Example

```python
from core import Registry, ValidationError, validate_period


class Widget:
    def __init__(self, size: int) -> None:
        self.size = validate_period(size, name="size")


widget_registry: Registry[type[Widget]] = Registry(kind="widget")
widget_registry.register("basic", Widget)

widget_cls = widget_registry.get("basic")
widget = widget_cls(5)
```

## Running Tests

From the repository root (after installing the project in editable mode with dev dependencies):

```bash
pytest packages/core/tests
```
