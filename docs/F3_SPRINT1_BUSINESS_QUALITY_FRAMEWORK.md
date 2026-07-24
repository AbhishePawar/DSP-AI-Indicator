# F3.1 — Business Quality Framework

**Package:** `business_quality` **`0.1.0`** · **Domain payload:** `0.1.0-business-quality` · **Framework:** `0.1.0-framework`

**Scope:** Canonical Business Quality domain architecture — models, scoring primitives, validation, explainability, engine façade.

**Mode:** Framework-only · **No business-quality analysis · No financial calculations · No provider integrations · No `/api/v1` changes**

**Note:** Phase 1 Valuation and Phase 2 Financial remain frozen. Phase 3 git milestone deferred until F3.7 approval.

---

## Objective

Establish the immutable contract and reusable primitives for Phase 3 Business Quality Intelligence. Downstream F3.x sprints plug analysis modules into this scaffold.

---

## Package layout

```text
packages/business_quality/
  README.md
  pyproject.toml
  src/business_quality/
    __init__.py
    engine.py
    exceptions.py
    models.py
    validation.py
    explainability.py
    scoring.py
    metadata.py
```

## API (framework)

```python
from business_quality import BusinessQualityEngine

engine = BusinessQualityEngine()
shell = engine.create_shell_analysis(company="Acme", ticker="ACM")
# engine.analyze(...)  → BusinessQualityFrameworkError in F3.1
```

## Primitives

| Area | Types |
|---|---|
| Scoring | `Score`, `WeightedScore`, `Confidence`, `EvidenceLevel`, `Rating`, `RiskLevel`, `Assessment` |
| Flags | `BusinessQualityFlag` — Excellent / Strong / Average / Weak / Poor / Unknown / InsufficientData |
| Models | `BusinessQualityAnalysis`, `BusinessQualityScore`, `BusinessQualitySummary`, `BusinessQualityMetadata`, … |
| Validation | required / missing / invalid inputs · confidence · evidence |
| Explainability | title · description · evidence · reasoning · confidence · limitations · references |

## Design rules

- Clean Architecture bounded context
- Immutable dataclasses
- Generic scoring helpers only (`clip_score`, `weighted_mean`) — no domain interpretation
- Engine is a façade; analysis arrives in F3.2+

## Next

**F3.2 — Earnings Quality Intelligence** — completed; see [F3_SPRINT2_EARNINGS_QUALITY_INTELLIGENCE.md](F3_SPRINT2_EARNINGS_QUALITY_INTELLIGENCE.md).

**F3.3 — Capital Allocation Intelligence** — completed; see [F3_SPRINT3_CAPITAL_ALLOCATION_INTELLIGENCE.md](F3_SPRINT3_CAPITAL_ALLOCATION_INTELLIGENCE.md).

**F3.4 — Business Characteristics Intelligence**
