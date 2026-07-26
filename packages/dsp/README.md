<!-- ASI-005-PACKAGE-CARD -->
# dsp

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

DSP Indicator Engine — technical indicators and explained signals

## 2. Responsibilities

Provide the stable `dsp` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Production · Frozen** · Version **0.2.0** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`__all__` exports (24): `DEFAULT_INDICATOR_SPECS`, `EMA`, `AnalysisResult`, `EvidenceGenerator`, `ExplanationGenerator`, `Indicator`, `IndicatorAnalysis`, `IndicatorEngine`, `IndicatorError`, `IndicatorResult`, `IndicatorSpec`, `RSI`, … (+12)

## 5. Package Structure

`packages/dsp/src/dsp/` · `packages/dsp/tests/` · local `pyproject.toml` when present.

## 6. Dependencies

`contracts`, `core`

## 7. Architecture Notes

Architecture allowlists / freeze policy apply. See appendix and [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
import dsp
print(dsp.__version__)
```

Worked examples live in `packages/dsp/tests/`.

## 9. Testing

```bash
pytest packages/dsp/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

# DSP — Indicator Engine

`dsp` is the platform's **Indicator Engine** (Section 3.4 of
`docs/DSP_AI_INDICATOR_ARCHITECTURE.md`): it computes technical/DSP-derived
indicators from price data and produces explainable, evidence-backed
readings for every downstream engine to consume.

Through Sprint 2.x, this package was a numerical indicator *library*:
callers passed NumPy arrays in and got NumPy arrays back, with no
knowledge of `contracts`, no explanations, and no notion of a "signal."
**Sprint 3.0** adds the orchestration and integration layer that makes it
an *engine* participating in the platform's architecture, without
touching a single line of the existing SMA/EMA/RSI/WMA algorithms:

```
Before (Sprint 2.x and earlier):        After (Sprint 3.0):

numpy array                             contracts.PriceSeries
     │                                        │
     ▼                                        ▼
EMA(period).compute(...)                IndicatorEngine.analyze()
     │                                        │  (calls the *same*,
     ▼                                        │   unmodified EMA/SMA/
numpy array                                   │   RSI/WMA underneath)
                                               ▼
                                         AnalysisResult
                                          ├─ Signal        (contracts)
                                          ├─ Explanation   (contracts)
                                          └─ Evidence      (contracts)
```

## Responsibilities

The Indicator Engine is responsible for:

- Computing technical indicators from price data —
  `dsp.indicators` (SMA, EMA, RSI, WMA), **unchanged since before Sprint
  3.0**.
- Discovering and instantiating indicators by name — `dsp.registry`,
  **unchanged since before Sprint 3.0**.
- Orchestrating indicator computation against a `contracts.PriceSeries`
  — `dsp.engine.service.IndicatorEngine` (**new in Sprint 3.0**):
  receiving the series, selecting which indicators to run, executing
  them through the existing registry, and collecting their outputs.
- Interpreting a computed reading into a directional bias using simple,
  deterministic rules — `dsp.signals.rules` (**new in Sprint 3.0**).
- Producing the platform's shared, explainable output types —
  `contracts.Signal`, `contracts.Explanation`, `contracts.Evidence` —
  for every indicator it runs, via `dsp.signals.signal_generator`,
  `dsp.signals.explanation_generator`, `dsp.signals.evidence_generator`
  (**new in Sprint 3.0**).

The Indicator Engine is explicitly **not** responsible for:

- Acquiring or normalizing price data — that is `data_engine`'s job;
  `IndicatorEngine.analyze()` accepts an already-built
  `contracts.PriceSeries` and has no opinion about where it came from.
- Any AI/LLM reasoning, portfolio construction, or multi-indicator
  voting — a `Signal`'s direction comes from exactly one indicator's own
  deterministic rule, never a combination of several.
- Advanced trading strategies — the rules in `dsp.signals.rules` are
  intentionally simple threshold/crossover checks, not backtested or
  optimized strategies.
- Adding new indicator algorithms — this sprint integrates the four that
  already existed (SMA, EMA, RSI, WMA); it adds no new math.

## Package Structure

```
packages/dsp/
├── README.md
├── src/
│   └── dsp/
│       ├── __init__.py            # public API (indicators + engine + signals)
│       ├── exceptions.py           # IndicatorError — unchanged
│       ├── indicators/              # indicator algorithms — unchanged
│       │   ├── __init__.py
│       │   ├── base.py               # Indicator ABC
│       │   ├── moving_averages.py     # SMA, EMA, WMA
│       │   └── momentum.py             # RSI
│       ├── registry/                # name -> Indicator registry — unchanged
│       │   └── __init__.py
│       ├── engine/                   # orchestration layer (new)
│       │   ├── __init__.py            # barrel re-export
│       │   ├── models.py               # IndicatorSpec, IndicatorResult
│       │   ├── results.py               # IndicatorAnalysis, AnalysisResult
│       │   └── service.py                # IndicatorEngine
│       └── signals/                  # signal-generation layer (new)
│           ├── __init__.py            # barrel re-export
│           ├── rules.py                # RuleOutcome + threshold/crossover rules
│           ├── signal_generator.py      # SignalGenerator
│           ├── explanation_generator.py  # ExplanationGenerator
│           └── evidence_generator.py      # EvidenceGenerator
└── tests/
    ├── conftest.py                  # NumPy fixtures (existing) +
    │                                #   PriceSeries factory (new)
    ├── test_moving_averages.py      # unchanged
    ├── test_momentum.py             # unchanged
    ├── test_registry.py             # unchanged
    ├── test_exceptions.py           # unchanged
    ├── test_engine_models.py        # IndicatorSpec, IndicatorResult
    ├── test_engine_results.py       # IndicatorAnalysis, AnalysisResult
    ├── test_engine_service.py       # IndicatorEngine end-to-end
    ├── test_signals_rules.py        # threshold/crossover rules + registry
    ├── test_signals_generators.py   # Signal/Explanation/Evidence generators
    └── test_public_api.py           # dsp.* re-export surface
```

## Dependency Diagram

```
contracts   (Instrument, PriceSeries, Signal, Explanation, Evidence, enums)
    ▲
    │
core        (DSPAIError, ValidationError, validate_period, Registry[T])
    ▲
    │
dsp
    │
    ├── indicators/   ── depends on: core (validation) — unchanged
    ├── registry/     ── depends on: core (Registry[T]), dsp.indicators — unchanged
    ├── exceptions.py ── depends on: core (DSPAIError) — unchanged
    │
    ├── engine/
    │   ├── models.py   ── depends on: contracts, core
    │   ├── results.py  ── depends on: contracts, engine.models
    │   └── service.py  ── depends on: contracts, core (via models),
    │                        dsp.registry, dsp.indicators.base,
    │                        dsp.exceptions, dsp.signals, engine.models,
    │                        engine.results
    │
    └── signals/
        ├── rules.py                 ── depends on: contracts (enums),
        │                                core (Registry[T]), engine.models
        ├── signal_generator.py       ── depends on: contracts, engine.models,
        │                                  signals.rules
        ├── explanation_generator.py   ── depends on: contracts, engine.models,
        │                                    signals.rules
        └── evidence_generator.py       ── depends on: contracts, engine.models,
                                              signals.rules
```

`dsp` depends only on `contracts` and `core`, exactly as required — it
does **not** depend on `data_engine`, even though the architecture
document permits it to. `IndicatorEngine.analyze()` takes a
`contracts.PriceSeries` directly; nothing in this package needs to know
that `data_engine.services.MarketDataService` (or any other producer) is
what built it. Nothing in `contracts` or `core` was modified.

Within `dsp`, `engine.models` is the one leaf every other new module
depends on (directly or transitively) — it holds `IndicatorSpec` and
`IndicatorResult`, has no dependency on `engine.service` or `signals`,
and cannot cause a cycle. `signals/` depends on `engine.models` (the data
it interprets) but not on `engine.service` (the orchestrator that calls
it) — the dependency points inward from application code to domain data,
never the reverse. `indicators/` and `registry/` are completely
untouched and have no dependency on `engine/` or `signals/` in either
direction; `IndicatorEngine` depends on them, not the other way round.

## The Flow

This is what `IndicatorEngine.analyze()` does for **each** requested
indicator, exactly matching the mission's
`PriceSeries -> IndicatorEngine -> IndicatorResult -> SignalGenerator ->
ExplanationGenerator -> Evidence` framing:

```
contracts.PriceSeries                 dsp.engine.service.IndicatorEngine
     │  (caller-provided, from            .analyze(price_series, specs=...)
     │   data_engine or a test fixture)
     ▼
[1] IndicatorSpec("rsi", 14)          dsp.engine.models.IndicatorSpec
     │  selects which indicator + period to run
     │  (caller-supplied, or DEFAULT_INDICATOR_SPECS)
     ▼
[2] dsp.registry.get("rsi", 14)       dsp.registry            (unchanged)
     │  resolves the *existing*, unmodified RSI class
     ▼
[3] RSI(14).compute(closes)           dsp.indicators.momentum  (unchanged)
     │  the exact same NumPy computation as every prior sprint
     ▼
[4] IndicatorResult                   dsp.engine.models.IndicatorResult
     │  (name, period, source_values, values, latest_value, as_of,
     │   computed_at) — NumPy array converted to tuple[float, ...]
     │  exactly once, right here
     ▼
[5] dsp.signals.rules.evaluate(result)   dsp.signals.rules
     │  one deterministic rule (threshold or crossover) decides a
     │  RuleOutcome: direction + reasoning + threshold + strength
     ▼
[6] ExplanationGenerator.generate(...)   dsp.signals.explanation_generator
     │  -> contracts.Explanation (summary == outcome.reasoning)
     ▼
[7] SignalGenerator.generate(..., explanation=...)  dsp.signals.signal_generator
     │  -> contracts.Signal (direction, value, strength, explanation)
     ▼
[8] EvidenceGenerator.generate(..., explanation)    dsp.signals.evidence_generator
     │  -> contracts.Evidence (claim, value, reference, weight, explanation)
     ▼
IndicatorAnalysis(result, signal, explanation, evidence)
     │  one of these per requested indicator, collected into
     ▼
AnalysisResult(instrument, analyses=(...))
```

Steps `[6]`–`[8]` all consume the **same** `RuleOutcome` produced once in
step `[5]` — this is why a `Signal`'s direction, its `Explanation`'s
summary, and its `Evidence`'s claim can never disagree with each other
(see Design Decision 3).

## Base Interfaces

### Indicators (`dsp.indicators`) — unchanged

- `Indicator` — the existing abstract base class every algorithm
  implements (`name`, `period`, `compute()`, `__call__`).
- `SMA`, `EMA`, `WMA`, `RSI` — the existing algorithms.
  `IndicatorEngine` calls `Indicator.compute()` exactly as any other
  caller would; no algorithm was read for anything other than its
  public signature.

### Registry (`dsp.registry`) — unchanged

- `register(name, cls)` / `get(name, period)` / `list_indicators()` /
  `compute(name, prices, period)` / `indicator_factory(name)` — the
  existing name -> `Indicator` registry, built on `core.registry.Registry`.
  `IndicatorEngine` uses `get` as its default indicator resolver.

### Engine (`dsp.engine`) — new in Sprint 3.0

- `IndicatorSpec(name, period)` — an immutable request to run one
  registered indicator with one period. Normalizes `name` to lowercase
  and validates `period` via `core.validation.validate_period`.
- `IndicatorResult` — the outcome of running one `IndicatorSpec`:
  `instrument`, `name`, `period`, `frequency`, `source_values` (close
  prices), `values` (the indicator's own output), `latest_value`,
  `as_of` (timestamp of the latest bar), `computed_at` (execution
  timestamp). Both `source_values` and `values` are
  `tuple[float, ...]`, not NumPy arrays — see Design Decision 2. **Not**
  a `contracts` type; see Design Decision 1.
- `IndicatorAnalysis(result, signal, explanation, evidence)` — the
  complete output for one requested indicator.
- `AnalysisResult(instrument, analyses)` — what `analyze()` returns, with
  `.signals` / `.explanations` / `.evidence` convenience properties that
  flatten `analyses` into plain tuples of `contracts` objects.
- `IndicatorEngine(resolve_indicator=..., signal_generator=...,
  explanation_generator=..., evidence_generator=..., clock=...)` —
  the orchestrator. `.analyze(price_series, specs=None) ->
  AnalysisResult` runs each spec (or `DEFAULT_INDICATOR_SPECS` — one
  SMA(20), EMA(12), WMA(20), and RSI(14) reading) and returns the fully
  explained result. Every collaborator is constructor-injectable.

### Signals (`dsp.signals`) — new in Sprint 3.0

- `RuleOutcome(direction, reasoning, threshold, strength)` — the shared
  intermediate every generator consumes.
- `evaluate_threshold_rule(result, *, overbought=70.0, oversold=30.0)` —
  for bounded oscillators (registered for `"rsi"`): above `overbought`
  is `BEARISH` (overbought), below `oversold` is `BULLISH` (oversold),
  otherwise `NEUTRAL`.
- `evaluate_crossover_rule(result)` — for moving-average-style
  indicators (registered for `"sma"`, `"ema"`, `"wma"`): a bullish
  crossover event on the latest bar is `BULLISH`, a bearish crossover
  event is `BEARISH`, no crossover on the latest bar is `NEUTRAL` (see
  Design Decision 5).
- `evaluate(result)` / `register_rule(name, rule)` — the name -> rule
  registry dispatch, built on `core.registry.Registry`, following the
  exact same extension pattern `dsp.registry` already established.
- `SignalGenerator.generate(result, outcome, *, explanation=None) ->
  Signal`, `ExplanationGenerator.generate(result, outcome) ->
  Explanation`, `EvidenceGenerator.generate(result, outcome,
  explanation=None) -> Evidence` — thin, single-responsibility shapers
  from `RuleOutcome` to each `contracts` type.

## Known Architectural Issues

Sprint 3.0's mission was to integrate the existing indicators into an
orchestration layer without redesigning them. Doing so surfaced one
genuine structural gap, recorded here rather than fixed silently:

**`dsp.registry` and `dsp.signals.rules` are two independent registries
keyed by the same name vocabulary, with nothing enforcing that every
indicator registered in the first has a matching rule registered in the
second.** Registering a fifth indicator (e.g. a future MACD) via
`dsp.registry.register(...)` makes it immediately computable through
`IndicatorEngine`, but `IndicatorEngine.analyze()` will only discover
that no rule exists for it *at call time*, when
`dsp.signals.rules.evaluate()` raises `KeyError` for that name. This
sprint added a defensive translation of that specific `KeyError` into
`IndicatorError` inside `IndicatorEngine._analyze_one` (see
`test_indicator_without_a_registered_rule_raises_indicator_error`), so
callers see the platform's own exception hierarchy rather than a bare
`KeyError` — but the underlying gap (two registries that can silently
drift out of sync) is not fixed. A future sprint that adds a fifth
indicator should either register a matching rule in the same change, or
this package should grow a startup-time consistency check (e.g.
"every name in `dsp.registry.list_indicators()` must have a
`dsp.signals.rules` entry") — deliberately not built now, since no
second indicator addition exists yet to prove which check is actually
useful.

## Design Decisions

1. **`IndicatorSpec` and `IndicatorResult` are internal `dsp` models,
   not `contracts` types**, per the mission's explicit instruction.
   They may change shape without being a breaking change to the
   platform's shared vocabulary, and other engines must never import
   them directly. The only stable, cross-engine output of this package
   is the `Signal`/`Explanation`/`Evidence` triple inside
   `AnalysisResult`. `IndicatorResult` is still returned (nested inside
   `IndicatorAnalysis`) from `analyze()`'s public return value, rather
   than being fully hidden — see Design Decision 2 for why that does not
   violate "no NumPy leaves the public API."

2. **The NumPy-to-tuple boundary is crossed exactly once, immediately
   after `Indicator.compute()` returns**, inside
   `IndicatorEngine._compute()`. `IndicatorResult.values` and
   `.source_values` are `tuple[float, ...]`, not
   `npt.NDArray[np.float64]`. This makes the success criterion ("no raw
   NumPy array should leave the public API of the Indicator Engine")
   true even for `IndicatorResult` itself, not just for
   `Signal`/`Explanation`/`Evidence` — so `IndicatorResult` can safely
   remain visible on `IndicatorAnalysis` for introspection (e.g. a future
   dashboard drawing a sparkline) without reintroducing a NumPy leak.
   The conversion cost (one Python-level loop over the computed series)
   is accepted as the price of that safety; see the Known Architectural
   Issues section's sibling in `data_engine`'s README for the same
   trade-off made differently at a different layer.

3. **A single `RuleOutcome`, computed once per `IndicatorResult`, feeds
   all three generators.** The mission asks for three separate
   components (`SignalGenerator`, `ExplanationGenerator`, and an
   evidence-producing component), but interpreting *what a reading
   means* — is this overbought, is this a crossover — is one decision,
   not three. Each generator independently re-deriving that decision
   would risk a `Signal` disagreeing with its own `Explanation`, and
   would be exactly the kind of duplicated logic the mission's
   "do not duplicate calculations" principle warns against, applied to
   interpretation rather than computation. `dsp.signals.rules.evaluate()`
   is the one place that decision is made; the three generators only
   *shape* it differently.

4. **Rules are dispatched by a name-keyed registry
   (`core.registry.Registry`), not an `if`/`elif` chain in
   `SignalGenerator`.** This directly follows Coding Standard 5
   ("anything designed to be extended must use a registry") and the
   exact pattern `dsp.registry` already established for indicators
   themselves. Adding a rule for a future indicator means calling
   `dsp.signals.rules.register_rule(name, fn)`, never editing
   `SignalGenerator`, `ExplanationGenerator`, `EvidenceGenerator`, or
   `IndicatorEngine`.

5. **The crossover rule detects a crossover *event* on the latest bar,
   not standing position.** "Price is above its moving average" is true
   for many consecutive bars in a trend; treating that whole span as a
   repeated bullish signal would misrepresent one underlying event as
   many, and drift toward the "advanced trading strategy" territory the
   mission excludes. The rule only fires when the previous bar's
   price-vs-average relationship differs from the latest bar's — a
   single bar's transition, checked with plain comparisons, nothing
   more.

6. **The crossover rule compares price against a *single* moving
   average line, not two moving averages of different speeds (a
   "golden cross").** `IndicatorResult` represents one indicator's
   output; a dual-moving-average crossover would require comparing two
   separate `IndicatorResult`s, which is a form of multi-indicator
   combination the mission explicitly excludes ("do not implement
   multi-indicator voting"). Price-versus-single-average is the
   standard, well-known technical rule that stays within one
   indicator's own result.

7. **`Signal.direction` uses `contracts.enums.SignalDirection`
   (`BULLISH`/`BEARISH`/`NEUTRAL`), not `RecommendationAction`
   (`BUY`/`SELL`/...), even though the mission phrases its examples as
   "RSI > 70 -> SELL."** `RecommendationAction` is `contracts`'s type for
   the AI Investment Committee's *final* recommendation (Section 3.11)
   — a `Signal` is one engine's raw analytical reading, not an
   investment decision. Overbought/bearish-leaning readings are mapped
   to `BEARISH`, oversold/bullish-leaning readings to `BULLISH`, exactly
   matching `Signal`'s own existing contract. Any future engine that
   turns indicator signals into an actual buy/sell/hold call is where
   `RecommendationAction` belongs.

8. **`IndicatorEngine`'s every collaborator is constructor-injected,
   with the real registry and wall-clock time only as defaults.**
   `resolve_indicator`, `signal_generator`, `explanation_generator`,
   `evidence_generator`, and `clock` can all be swapped, which is what
   lets `test_engine_service.py` assert deterministic output (a fixed
   `clock`) and exercise indicator-resolution failure paths (a fake
   `resolve_indicator`) without mutating or depending on the real,
   shared `dsp.registry` state.

9. **`DEFAULT_INDICATOR_SPECS` (SMA(20), EMA(12), WMA(20), RSI(14)) is a
   named, documented default, not a hidden hardcoded basket.** The
   mission requires the engine to be responsible for "selecting
   indicators"; a caller-overridable default (rather than *requiring*
   every caller to specify indicators, or silently always running a
   fixed set with no way to override it) demonstrates that
   responsibility concretely while remaining simple. The specific
   periods chosen are common defaults, not a trading recommendation.

10. **No dependency on `data_engine` was added.** The dependency table
    permits `indicator-engine` to depend on `data-engine`, but
    `IndicatorEngine.analyze()` only needs a `contracts.PriceSeries`,
    which it can receive from any source — a real `MarketDataService`
    call, a hand-built fixture, or a future different engine entirely.
    Adding an unused dependency would violate the "no upward dependency
    without a real need" discipline established in prior sprints' design
    decisions.

## Extensibility Notes

Adding a fifth indicator (e.g. a future MACD) to this engine means:

1. Implementing it exactly as SMA/EMA/RSI/WMA already are — a class in
   `dsp.indicators` subclassing `Indicator` — and registering it via
   `dsp.registry.register(name, cls)`. Nothing in `engine/` or
   `signals/` needs to change for the computation itself to work.
2. Registering a rule for it in `dsp.signals.rules` via
   `register_rule(name, rule_fn)` — reusing `evaluate_threshold_rule`
   or `evaluate_crossover_rule` if it fits one of those shapes, or a new
   small function if it needs its own logic. Skipping this step is the
   gap recorded under Known Architectural Issues: the indicator would
   compute fine but `IndicatorEngine.analyze()` would raise
   `IndicatorError` for it until a rule is registered.
3. Optionally adding it to `DEFAULT_INDICATOR_SPECS` if it should run
   whenever a caller doesn't specify its own selection.

None of this required touching `contracts`, `core`, or any existing
indicator algorithm.
