<!-- ASI-005-PACKAGE-CARD -->
# fundamental

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

DSP Fundamental Engine — company analysis over financial snapshots

## 2. Responsibilities

Provide the stable `fundamental` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Production · Frozen** · Version **0.1.0** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`__all__` exports (23): `DEFAULT_ANALYZER_NAMES`, `Analyzer`, `BusinessRuleOutcome`, `BusinessSignalGenerator`, `CompanyAnalysis`, `EvidenceGenerator`, `ExplanationGenerator`, `FinancialSnapshot`, `FundamentalEngine`, `FundamentalError`, `FundamentalMetric`, `FundamentalResult`, … (+11)

## 5. Package Structure

`packages/fundamental/src/fundamental/` · `packages/fundamental/tests/` · local `pyproject.toml` when present.

## 6. Dependencies

`contracts`, `core`

## 7. Architecture Notes

Architecture allowlists / freeze policy apply. See appendix and [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
import fundamental
print(fundamental.__version__)
```

Worked examples live in `packages/fundamental/tests/`.

## 9. Testing

```bash
pytest packages/fundamental/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

# Fundamental — Business Analysis Engine

`fundamental` is the platform's **Fundamental Engine** (Section 3.5 of
`docs/DSP_AI_INDICATOR_ARCHITECTURE.md`): it analyzes a company's
as-reported financial statements and produces explainable,
evidence-backed business observations for every downstream engine
(ultimately the AI Investment Committee) to consume.

Sprint 4.0 establishes this engine's architecture from nothing, in the
same style `dsp` (the Indicator Engine) already established for
technical readings:

```
contracts.FundamentalStatement (one or more, per instrument)
     │
     ▼
FinancialSnapshot                    fundamental.models
     │
     ▼
FundamentalEngine.analyze()          fundamental.engine.service
     │  (runs the requested analyzers through the registry,
     │   calls each analyzer's own unmodified analyze())
     ▼
CompanyAnalysis
 ├─ FundamentalResult  (per analyzer)      fundamental.models
 └─ MetricAnalysis     (per metric)        fundamental.engine.results
     ├─ Signal        (contracts)
     ├─ Explanation   (contracts)
     └─ Evidence      (contracts)
```

## Responsibilities

The Fundamental Engine is responsible for:

- Accepting a validated, ordered bundle of a company's as-reported
  financial statements — `fundamental.models.FinancialSnapshot`.
- Orchestrating a pluggable set of single-responsibility analyzers
  against that snapshot — `fundamental.engine.service.FundamentalEngine`.
  It contains no ratio formulas itself.
- Computing a minimal set of business ratios — `fundamental.analyzers`
  (`ProfitabilityAnalyzer`, `GrowthAnalyzer`, `LeverageAnalyzer`,
  `QualityAnalyzer`) — each returning plain
  `fundamental.models.FundamentalMetric` values, never a
  `contracts` type and never raw NumPy/DataFrame objects.
- Interpreting a computed metric into a directional business
  observation using simple, deterministic rules —
  `fundamental.signals.rules`.
- Producing the platform's shared, explainable output types —
  `contracts.Signal`, `contracts.Explanation`, `contracts.Evidence` —
  for every metric it computes, via
  `fundamental.signals.signal_generator`,
  `fundamental.signals.explanation_generator`,
  `fundamental.signals.evidence_generator`.

The Fundamental Engine is explicitly **not** responsible for:

- Acquiring or normalizing financial statement data — that is
  `data_engine`'s job (`data_engine.ports.FundamentalsDataPort`);
  `FundamentalEngine.analyze()` accepts an already-built
  `FinancialSnapshot` and has no opinion about where its statements
  came from.
- Any AI/LLM reasoning, valuation, peer comparison, or multi-year
  scoring/composite models — every business signal in this sprint comes
  from exactly one metric's own deterministic rule, never a combination
  of several metrics or periods.
- Advanced fundamental analysis — DCF, intrinsic value, Buffett Score,
  Piotroski Score, Altman Z-Score, DuPont analysis, and forecasting are
  explicitly out of scope for this sprint.
- An exhaustive ratio library — only seven metrics are implemented
  (Revenue Growth, EPS Growth, ROE, ROCE, Debt-to-Equity, Operating
  Margin, Free Cash Flow), enough to prove the architecture extends
  cleanly, not to cover every ratio a real research platform would need.

## Package Structure

```
packages/fundamental/
├── README.md
├── src/
│   └── fundamental/
│       ├── __init__.py            # public API
│       ├── enums.py                # MetricUnit
│       ├── exceptions.py            # FundamentalError
│       ├── models.py                 # FinancialSnapshot, FundamentalMetric,
│       │                             #   FundamentalResult (leaf — see Design
│       │                             #   Decision 1)
│       ├── registry.py               # name -> Analyzer registry
│       ├── analyzers/                # ratio computation (no orchestration)
│       │   ├── __init__.py
│       │   ├── base.py                 # Analyzer ABC
│       │   ├── _math.py                 # safe_divide, growth_rate
│       │   ├── profitability.py          # ProfitabilityAnalyzer (ROE, ROCE,
│       │   │                              #   operating margin)
│       │   ├── growth.py                  # GrowthAnalyzer (revenue/EPS growth)
│       │   ├── leverage.py                 # LeverageAnalyzer (debt-to-equity)
│       │   └── quality.py                   # QualityAnalyzer (free cash flow)
│       ├── engine/                    # orchestration layer
│       │   ├── __init__.py             # barrel re-export
│       │   ├── results.py               # MetricAnalysis, CompanyAnalysis
│       │   └── service.py                # FundamentalEngine
│       └── signals/                   # signal-generation layer
│           ├── __init__.py             # barrel re-export
│           ├── rules.py                 # BusinessRuleOutcome + higher/lower
│           │                             #   is-better rule families
│           ├── signal_generator.py       # BusinessSignalGenerator
│           ├── explanation_generator.py   # ExplanationGenerator
│           └── evidence_generator.py       # EvidenceGenerator
└── tests/
    ├── conftest.py                  # FundamentalStatement / FinancialSnapshot
    │                                #   factories
    ├── test_models.py               # FinancialSnapshot, FundamentalMetric,
    │                                #   FundamentalResult, format_metric_value
    ├── test_analyzers.py            # all four concrete analyzers
    ├── test_registry.py             # name -> Analyzer registry
    ├── test_engine_results.py       # MetricAnalysis, CompanyAnalysis
    ├── test_engine_service.py       # FundamentalEngine end-to-end
    ├── test_signals_rules.py        # higher/lower-is-better rules + registry
    ├── test_signals_generators.py   # Signal/Explanation/Evidence generators
    ├── test_exceptions.py           # FundamentalError hierarchy
    └── test_public_api.py           # fundamental.* re-export surface
```

## Dependency Diagram

```
contracts   (Instrument, FundamentalStatement, Signal, Explanation,
             Evidence, enums)
    ▲
    │
core        (DSPAIError, ValidationError, Registry[T])
    ▲
    │
fundamental
    │
    ├── models.py       ── depends on: contracts, core, fundamental.enums
    │                        (a leaf — no dependency on engine, analyzers,
    │                        registry, or signals; see Design Decision 1)
    ├── enums.py         ── depends on: nothing but the standard library
    ├── exceptions.py    ── depends on: core (DSPAIError)
    │
    ├── analyzers/
    │   ├── base.py           ── depends on: fundamental.models
    │   ├── _math.py           ── depends on: nothing but the standard library
    │   └── profitability.py,  ── depend on: analyzers.base, analyzers._math,
    │       growth.py,             fundamental.models, fundamental.enums
    │       leverage.py,
    │       quality.py
    │
    ├── registry.py      ── depends on: core (Registry[T]), analyzers.*
    │
    ├── engine/
    │   ├── results.py    ── depends on: contracts, fundamental.models
    │   └── service.py     ── depends on: fundamental.models, engine.results,
    │                           fundamental.registry, fundamental.analyzers.base,
    │                           fundamental.exceptions, fundamental.signals
    │
    └── signals/
        ├── rules.py                 ── depends on: contracts (enums),
        │                                core (Registry[T]), fundamental.models
        ├── signal_generator.py       ── depends on: contracts, fundamental.models,
        │                                  signals.rules
        ├── explanation_generator.py   ── depends on: contracts, fundamental.models,
        │                                    signals.rules
        └── evidence_generator.py       ── depends on: contracts, fundamental.models,
                                              signals.rules
```

`fundamental` depends only on `contracts` and `core` — it does **not**
depend on `data_engine` or `dsp`, matching the architecture document's
Section 4 dependency table exactly (see Known Architectural Issues for
a discrepancy this surfaced in the mission text itself). Nothing in
`contracts`, `core`, `data_engine`, or `dsp` was modified.

Within `fundamental`, `models.py` is the one leaf every other module
depends on (directly or transitively) — it holds `FinancialSnapshot`,
`FundamentalMetric`, and `FundamentalResult`, and has no dependency on
`analyzers`, `registry`, `engine`, or `signals`. This is a deliberate
structural difference from `dsp.engine.models` — see Design Decision 1.

## The Flow

This is what `FundamentalEngine.analyze()` does, matching the mission's
`FinancialSnapshot -> FundamentalEngine -> Analyzer -> FundamentalResult
-> BusinessSignal -> Explanation -> Evidence` framing:

```
FinancialSnapshot                     fundamental.engine.service
     │  (caller-provided: an ordered,      .FundamentalEngine
     │   validated bundle of                .analyze(snapshot, ...)
     │   contracts.FundamentalStatement)
     ▼
[1] "profitability", "growth", ...    analyzer_names (caller-supplied,
     │  which analyzer categories to run       or DEFAULT_ANALYZER_NAMES)
     ▼
[2] fundamental.registry.get(name)    fundamental.registry
     │  resolves and instantiates a fresh Analyzer
     ▼
[3] ProfitabilityAnalyzer().analyze(snapshot)   fundamental.analyzers.*
     │  the analyzer's own ratio math — ROE, ROCE, operating margin, ...
     ▼
[4] FundamentalMetric × N              fundamental.models.FundamentalMetric
     │  (name, value, unit, period_end) — value is None, not NaN, when
     │  a required line item was not reported (see Design Decision 4)
     ▼
[5] FundamentalResult                  fundamental.models.FundamentalResult
     │  (instrument, analyzer_name, metrics, computed_at) — the engine,
     │  not the analyzer, stamps computed_at (see Design Decision 2)
     ▼
[6] fundamental.signals.rules.evaluate(metric)  fundamental.signals.rules
     │  one deterministic rule (higher-is-better or lower-is-better)
     │  decides a BusinessRuleOutcome: direction + observation +
     │  reasoning + threshold + strength, for *each* metric
     ▼
[7] ExplanationGenerator.generate(..., generated_at=result.computed_at)
     │  -> contracts.Explanation (summary == outcome.reasoning)
     ▼
[8] BusinessSignalGenerator.generate(..., explanation=...)
     │  -> contracts.Signal (direction, value, strength, explanation)
     ▼
[9] EvidenceGenerator.generate(..., explanation)
     │  -> contracts.Evidence (claim, value, reference, weight, explanation)
     ▼
MetricAnalysis(metric, signal, explanation, evidence)
     │  one of these per metric, across every requested analyzer,
     │  collected into
     ▼
CompanyAnalysis(instrument, results=(...), analyses=(...))
```

Steps `[7]`–`[9]` all consume the **same** `BusinessRuleOutcome` produced
once in step `[6]` — a `Signal`'s direction, its `Explanation`'s summary,
and its `Evidence`'s claim can never disagree with each other, exactly
mirroring `dsp`'s Design Decision 3 for the same reason.

## Base Interfaces

### Models (`fundamental.models`)

- `FinancialSnapshot(instrument, statements)` — a validated, ordered
  bundle of `contracts.FundamentalStatement` for one instrument,
  most-recent-first (matching
  `data_engine.ports.FundamentalsDataPort.get_fundamental_statements`'s
  documented ordering). Rejects an empty bundle, statements for more
  than one instrument, duplicate `period_end` values, or an out-of-order
  bundle. `.latest` / `.previous` expose the current and prior period.
- `FundamentalMetric(instrument, name, value, unit, period_end)` — one
  computed ratio for one period. `value` is `float | None` (`None`
  means "not computable"), `unit` is a `MetricUnit` used only for
  display. `.label` (e.g. `"ROE"`) and `.formatted_value` (e.g.
  `"18.0%"`) are display helpers. **Not** a `contracts` type.
- `FundamentalResult(instrument, analyzer_name, metrics, computed_at)` —
  the outcome of running one analyzer. **Not** a `contracts` type.
- `format_metric_value(value, unit)` — renders a value for its unit
  (`"18.0%"` / `"$1,234"` / `"1.20x"`), shared by `FundamentalMetric`
  and `fundamental.signals.rules`.

### Analyzers (`fundamental.analyzers`)

- `Analyzer` — abstract base every analyzer implements (`name`,
  `analyze(snapshot) -> tuple[FundamentalMetric, ...]`). Mirrors
  `dsp.indicators.base.Indicator` in shape and in dividing labor with
  its caller: the analyzer never stamps its own `computed_at` (see
  Design Decision 2).
- `ProfitabilityAnalyzer` — `roe` (`net_income / total_equity`), `roce`
  (`operating_income / (total_equity + total_debt)`, an approximation —
  see Design Decision 3), `operating_margin`
  (`operating_income / revenue`).
- `GrowthAnalyzer` — `revenue_growth`, `eps_growth` (using
  `eps_diluted` only — see Design Decision 5), each comparing
  `snapshot.latest` against `snapshot.previous`.
- `LeverageAnalyzer` — `debt_to_equity`
  (`total_debt / total_equity`).
- `QualityAnalyzer` — `free_cash_flow`
  (`operating_cash_flow - capital_expenditures`).
- Every ratio degrades to `value=None` rather than raising when a
  required line item is missing or a denominator is zero
  (`fundamental.analyzers._math.safe_divide` / `growth_rate`) —
  financial statements routinely omit fields, exactly as
  `contracts.FundamentalStatement`'s own docstring already notes.

### Registry (`fundamental.registry`)

- `register(name, cls)` / `get(name)` / `list_analyzers()` — a name ->
  `Analyzer` registry built on `core.registry.Registry`, following the
  exact pattern `dsp.registry` already established for indicators.
  Unlike an indicator, an analyzer takes no constructor arguments, so
  `get(name)` simply instantiates the registered class.

### Engine (`fundamental.engine`)

- `MetricAnalysis(metric, signal, explanation, evidence)` — the complete
  output for one metric.
- `CompanyAnalysis(instrument, results, analyses)` — what `analyze()`
  returns: `results` is one `FundamentalResult` per analyzer that ran
  (for traceability), `analyses` is the flattened per-metric
  `MetricAnalysis` tuple, with `.signals` / `.explanations` / `.evidence`
  convenience properties.
- `FundamentalEngine(resolve_analyzer=..., signal_generator=...,
  explanation_generator=..., evidence_generator=..., clock=...)` — the
  orchestrator. `.analyze(snapshot, analyzer_names=None) ->
  CompanyAnalysis` runs each named analyzer (or
  `DEFAULT_ANALYZER_NAMES` — `"profitability"`, `"growth"`,
  `"leverage"`, `"quality"`) and returns the fully explained result.
  Every collaborator is constructor-injectable, exactly as
  `dsp.engine.service.IndicatorEngine` already established.

### Signals (`fundamental.signals`)

- `BusinessRuleOutcome(direction, observation, reasoning, threshold,
  strength)` — the shared intermediate every generator consumes.
  `observation` (e.g. `"Strong Profitability"`, `"High Debt"`) is a
  first-class label, not only text embedded in `reasoning`.
- `evaluate_higher_is_better(metric, *, strong, weak, strong_label,
  weak_label)` — for metrics where a higher reading is better
  (profitability, growth, cash generation): above `strong` is
  `BULLISH`, below `weak` is `BEARISH`, otherwise `NEUTRAL`.
- `evaluate_lower_is_better(metric, *, healthy, high, healthy_label,
  high_label)` — the mirror image, for leverage: above `high` is
  `BEARISH`, below `healthy` is `BULLISH`, otherwise `NEUTRAL`.
- `evaluate(metric)` / `register_rule(name, rule)` — the name -> rule
  registry dispatch, built on `core.registry.Registry`, mirroring
  `dsp.signals.rules`'s exact extension pattern (see Design Decision 6
  for why this is convergent design, not a shared dependency on `dsp`).
- `BusinessSignalGenerator.generate(metric, outcome, *,
  explanation=None) -> Signal`, `ExplanationGenerator.generate(metric,
  outcome, *, generated_at) -> Explanation`,
  `EvidenceGenerator.generate(metric, outcome, explanation=None) ->
  Evidence` — thin, single-responsibility shapers from
  `BusinessRuleOutcome` to each `contracts` type.

## Known Architectural Issues

**A genuine circular import surfaced during implementation and was
fixed, not worked around.** The natural first design nested
`FinancialSnapshot`/`FundamentalMetric`/`FundamentalResult` under
`fundamental.engine.models`, mirroring `dsp.engine.models` exactly.
That works for `dsp` because `dsp.indicators.base.Indicator` never
imports `dsp.engine` — an indicator returns a plain NumPy array, and
only the *engine* wraps it into `IndicatorResult`. In `fundamental`,
every `Analyzer.analyze()` returns `FundamentalMetric` objects directly
(there is no separate raw-array boundary to cross), so
`fundamental.analyzers.base` must import the models module directly.
Because `fundamental.engine` is a regular Python package, importing
*any* name from `fundamental.engine.models` first requires fully
executing `fundamental/engine/__init__.py` — which imports
`engine.service`, which imports `fundamental.registry`, which imports
the analyzer classes themselves, which (in the original design) would
import back into the still-initializing `fundamental.engine.models` —
a genuine cycle, reproducible on the very first `import fundamental`.
The fix was structural, not a workaround: the three models now live in
a true leaf module, `fundamental/models.py`, a sibling of `engine/`,
`analyzers/`, and `signals/` rather than nested inside `engine/` (see
Design Decision 1). No production code referenced the old
`fundamental.engine.models` path, so this was resolved before it
shipped.

**The mission's literal dependency chain text conflicts with the
architecture document's own Section 4 table, and this package follows
the document.** The mission states `contracts ↑ core ↑ data_engine ↑
dsp ↑ fundamental`, which read literally would permit `fundamental` to
depend on `dsp`. `docs/DSP_AI_INDICATOR_ARCHITECTURE.md` Section 4's
dependency table, and its Section 6 roadmap ("Phase 4 — Fundamental
Engine and Economic Engine ... both depend only on Data Engine, not on
each other"), are unambiguous that `indicator-engine` and
`fundamental-engine` are **siblings**, both depending only on
`contracts`, `core`, and `data-engine` — neither depends on the other.
Since every prior sprint has treated this document as "the single
source of truth," and the mission itself opens by instructing "read
this document first," this package depends only on `contracts` and
`core` (not `dsp`, not even `data_engine` — see Design Decision 7) and
does not import anything from `dsp`. `fundamental.signals.rules`
independently re-implements the same *shape* `dsp.signals.rules`
established (a `RuleOutcome`-like dataclass, two generic rule
functions, a name-keyed registry) without a runtime dependency between
the two packages — see Design Decision 6. This is flagged here rather
than silently resolved because it is a genuine tension in the
instructions that a future sprint's author should be aware of.

**Two independent registries (`fundamental.registry` and
`fundamental.signals.rules`) can drift out of sync, exactly as flagged
in `dsp`'s README.** Registering a fifth analyzer that produces a new
metric name via `fundamental.registry.register(...)` makes it
immediately computable through `FundamentalEngine`, but
`FundamentalEngine.analyze()` will only discover that no rule exists
for that metric *at call time* — `fundamental.signals.rules.evaluate()`
raises `KeyError`, which `FundamentalEngine._analyze_metric` translates
into `FundamentalError` (see
`test_metric_without_a_registered_rule_raises_fundamental_error`) so
callers see the platform's own exception hierarchy rather than a bare
`KeyError`. The underlying gap is not fixed, for the same reason `dsp`
left it unfixed: no second analyzer addition exists yet to prove which
consistency check would actually be useful.

## Design Decisions

1. **`FinancialSnapshot`, `FundamentalMetric`, and `FundamentalResult`
   live in a top-level `fundamental/models.py`, not nested under
   `fundamental/engine/`, unlike `dsp.engine.models`.** This is a
   deliberate structural difference from `dsp`, not an inconsistency —
   see Known Architectural Issues for the circular import it exists to
   prevent. Models are shared vocabulary between `analyzers/`,
   `engine/`, and `signals/`; nesting them under any one of those three
   would make that one package's `__init__.py` a hidden prerequisite
   for the other two, which is exactly backwards for a leaf dependency.

2. **Analyzers never stamp their own `computed_at`; `FundamentalEngine`
   does, after calling `Analyzer.analyze()`.** This directly mirrors
   how `dsp.indicators.base.Indicator.compute()` returns a plain array
   and only `IndicatorEngine._compute()` stamps `IndicatorResult`'s
   `computed_at`. Keeping the clock out of every analyzer keeps them
   trivially testable (no monkeypatching `datetime.now`) and keeps
   `FundamentalEngine` the single place execution metadata is decided,
   exactly as the mission's "engine orchestrates, analyzers don't"
   framing requires.

3. **ROCE approximates capital employed as `total_equity + total_debt`,
   not the textbook `total_assets - current_liabilities`.**
   `contracts.FundamentalStatement` does not report current liabilities
   separately from total liabilities (a deliberate Contracts scoping
   decision from Sprint 1.1, treated as stable this sprint), so the
   textbook definition is not computable from it. Equity plus
   interest-bearing debt is the standard, widely used approximation
   when only balance-sheet totals are available, and is used
   consistently rather than silently returning `None` for every ROCE
   computation.

4. **`FundamentalMetric.value` is `float | None`, not `float("nan")`,
   unlike `dsp.engine.models.IndicatorResult.values`.** `dsp` uses NaN
   because a warmup-period gap in a numeric series is a well-understood
   NumPy convention. Financial statements are different: fields are
   routinely *not reported at all* (see
   `contracts.FundamentalStatement`'s own docstring, "reporting
   completeness varies by provider"), and Contracts already models
   that as `None`. Reusing `None` for "not computable" throughout
   `fundamental` keeps one consistent vocabulary for "missing" across
   the raw statement and every derived metric, rather than introducing
   a second, NumPy-flavored convention for the same concept.

5. **`eps_growth` uses `eps_diluted` only, with no `eps_basic`
   fallback.** Diluted EPS is the more conservative, more commonly
   cited figure, and adding a fallback chain (diluted, else basic, else
   None) is exactly the kind of scope creep the mission's "implement
   only a minimal set of metrics" instruction warns against. A future
   sprint can add the fallback if a real statement gap proves it
   necessary.

6. **`fundamental.signals.rules` independently re-implements the
   *shape* of `dsp.signals.rules` (a `RuleOutcome`-like dataclass, a
   small family of generic rule functions, a name-keyed registry)
   without importing anything from `dsp`.** Per Known Architectural
   Issues, `fundamental` and `dsp` are siblings in the dependency
   table, so `fundamental` cannot depend on `dsp` even though the two
   modules would otherwise be near-identical. Converging on the same
   *pattern* independently — rather than either duplicating `dsp`'s
   literal code via copy-paste with a different docstring, or reaching
   across the sibling boundary to reuse it — is what "consistent
   architecture across engines" should look like without violating
   the dependency table.

7. **No dependency on `data_engine` was added, even though the
   architecture document permits `fundamental-engine` to depend on
   `data-engine`.** `FundamentalEngine.analyze()` only needs a
   `FinancialSnapshot`, which it can receive from any source — a real
   `data_engine` fundamentals adapter (once one exists), a hand-built
   fixture, or a future different engine entirely. This mirrors `dsp`'s
   own Design Decision 10 for the identical reason: adding an unused
   dependency would violate the "no upward dependency without a real
   need" discipline established in prior sprints.

8. **Business observation rules use two generic shapes —
   "higher is better" and "lower is better" — instead of one bespoke
   function per metric.** All seven metrics in this sprint reduce to
   one of these two shapes (a bullish band, a bearish band, and a
   neutral band in between); the labels, thresholds, and units differ
   per metric but the comparison logic does not. This directly follows
   `dsp`'s own Design Decision 4 ("rules are dispatched by a registry,
   not an `if`/`elif` chain") one level further: even the *rule bodies*
   are shared, and `fundamental.signals.rules`'s module-level
   registrations (via `functools.partial`) are the only place
   per-metric configuration lives.

9. **"Weak Balance Sheet" (one of the mission's four example business
   signals) is deliberately not implemented as a single metric's
   rule.** Unlike "Strong Profitability" (ROE), "High Debt"
   (Debt-to-Equity), and "Healthy Cash Generation" (Free Cash Flow),
   a genuine "weak balance sheet" reading inherently requires
   synthesizing leverage, liquidity, *and* cash generation together —
   exactly the kind of cross-metric combination the mission's "do not
   implement multi-year scoring models" (and, by the same logic,
   multi-metric composite scores) excludes this sprint. `debt_to_equity`
   alone produces `"High Debt"` for a bearish reading; a genuine
   balance-sheet-strength composite belongs to a future sprint that
   explicitly scopes multi-metric synthesis.

10. **`contracts.Signal`/`Explanation`/`Evidence` are reused directly
    for "Business Signals," not a new Contracts type.** The mission
    calls these "Business Signals" and notes they are "business
    observations, NOT investment recommendations" — that is exactly
    the distinction `contracts.enums.SignalDirection`
    (`BULLISH`/`BEARISH`/`NEUTRAL`) already draws against
    `RecommendationAction` (`BUY`/`SELL`/...), mirroring `dsp`'s own
    Design Decision 7. Contracts is stable this sprint; introducing a
    parallel type for the same shape would violate that and fragment
    the platform's shared vocabulary for no benefit.

## Extensibility Notes

Adding a fifth analyzer (e.g. a future `LiquidityAnalyzer` or
`EfficiencyAnalyzer` — both named as examples in the mission but not
implemented this sprint, since no metric in the "initial metrics" list
maps to a liquidity ratio computable from `contracts.FundamentalStatement`
today) means:

1. Implementing it exactly as the four existing analyzers are — a class
   in `fundamental.analyzers` subclassing `Analyzer`, returning
   `FundamentalMetric` objects from `fundamental.models` — and
   registering it via `fundamental.registry.register(name, cls)`.
   Nothing in `engine/` or `signals/` needs to change for the
   computation itself to work.
2. Registering a rule for each new metric name in
   `fundamental.signals.rules` via `register_rule(name, rule)` —
   reusing `evaluate_higher_is_better` or `evaluate_lower_is_better` if
   it fits one of those two shapes, or a new small function if it needs
   its own logic. Skipping this step is the gap recorded under Known
   Architectural Issues: the metric would compute fine but
   `FundamentalEngine.analyze()` would raise `FundamentalError` for it
   until a rule is registered.
3. Optionally adding it to `DEFAULT_ANALYZER_NAMES` if it should run
   whenever a caller doesn't specify its own selection.

None of this required touching `contracts`, `core`, `data_engine`,
`dsp`, or any existing analyzer.
