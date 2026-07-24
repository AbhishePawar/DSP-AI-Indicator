# V1.5 — Valuation Core Framework

**Domain package:** `valuation` **`0.5.0`** · **Core:** `0.5.0-valuation-core`  

**Scope:** Shared valuation **infrastructure only** (no new methodology).  

**Mode:** Research Mode only · Overall Valuation remains **DISABLED**

---

## Objective

Create a reusable Valuation Core Framework under `packages/valuation/src/valuation/core/` as the common foundation for all future valuation methods.

This sprint does **not** introduce EPV or any new valuation methodology. Existing DCF Intelligence, Reverse DCF, and Residual Income calculations remain **mathematically identical**.

---

## Architecture

```text
valuation/
  core/                    ← NEW shared infrastructure
    result_models.py       ValuationResult (+ serializers)
    confidence_engine.py
    sensitivity_engine.py
    scenario_engine.py
    explainability_engine.py
    validation_engine.py
    metadata.py
    quality_flags.py
    errors.py
    interfaces.py
  dcf_intelligence/        unchanged math
  reverse_dcf/             unchanged math
  residual_income/         unchanged math
```

Clean Architecture preserved: domain-only, no HTTP, no Web VIE, no `/api/v1`, no Research/MIE/EMI/EQI/Decision/Copilot changes.

---

## Components

| Component | Role |
|---|---|
| `ValuationResult` | Standardized result + `to_dict` / `to_aggregate_payload` |
| `ConfidenceEngine` | Weighted research confidence (high/medium/low) |
| `ValidationEngine` | Shared input checks → `ValidationSummary` |
| `SensitivityEngine` | OTAT grids (heatmap-ready) |
| `ScenarioEngine` | Bear / Base / Bull / Custom plugs |
| `ExplainabilityEngine` | Formats calculation steps + research disclaimer |
| `QualityFlag` | Reusable research flags |
| `ValuationMetadata` | Model / version / timing / assumptions |
| Error hierarchy | Extends package `ValuationError` |
| Interfaces | ABC contracts for future engines |

---

## Integration policy

- **Optional** consumption by existing modules only where beneficial.
- This sprint does **not** refactor DCF / Reverse DCF / RIV internals.
- Public method signatures (`analyze`, `analyze_dcf`, `analyze_reverse_dcf`, `analyze_residual_income`) unchanged.
- Additive exports only from `valuation` / `valuation.core`.

---

## Performance

Shared engines target **&lt; 5 ms** overhead for a typical confidence + validation + scenario + sensitivity + explainability pass (see `tests/test_core`).

---

## Tests

`packages/valuation/tests/test_core/` — confidence, validation, sensitivity, scenario, explainability, metadata, errors, interfaces, serialization, performance.

Target: **100% coverage** of `valuation.core`.

---

## Success criteria

- Domain-only · Clean Architecture preserved  
- No valuation math / public API / behavior changes for existing methods  
- Standard `ValuationResult` + shared engines  
- Research Mode only · Overall Valuation disabled  
- Regression GREEN  

---

## Recommended git tag

`milestone/V1.5-valuation-core`
