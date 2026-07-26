# investment_recommendation

## 1. Package Purpose

Deterministic Investment Recommendation Engine — converts valuation and
domain-quality outputs into an explainable investment recommendation
(FEATURE-007 Phase 1).

**Distinct from** G1.3 `recommendation.RecommendationEngine`.

## 2. Responsibilities

- Blend business quality, MoS/valuation, moat, management, FS, EQ, GQ.
- Produce recommendation (`strong_sell` → `strong_buy`) with confidence.
- Enforce MoS gates (no Strong Buy when materially above intrinsic value).
- Emit evidence, triggered rules, thesis, and decision summary.

## 3. Package Status

**Active · Phase 1 decision intelligence** · Version **0.1.0**

## 4. Public API

- `InvestmentRecommendationEngine` — `validate` / `analyze` / `explain`
- `ValuationSignals` — share-level IV/price/MoS contract (also accepts `OverallValuationResult`)
- `InvestmentRecommendation`, `InvestmentRecommendationAction`, `DecisionWeights`

## 5. Package Structure

```
packages/investment_recommendation/
├── README.md · pyproject.toml
├── src/investment_recommendation/
└── tests/
```

## 6. Dependencies

- `core` · `valuation`
- `economic_moat` · `management_quality` · `financial_strength`
- `earnings_quality` · `growth_quality` · `business_quality_aggregator`

## 7. Architecture Notes

- Decision-intelligence layer only — not platform / API / frontend / orchestration / AI Committee.
- No LLM / ML. Fully deterministic rule engine.
- Does not import G1.3 `recommendation` package.

## 8. Decision Methodology

| Component | Default weight |
|---|---|
| Business Quality (aggregator) | 40% |
| Valuation / MoS | 35% |
| Economic Moat | 8% |
| Management Quality | 6% |
| Financial Strength | 5% |
| Earnings Quality | 3% |
| Growth Quality | 3% |

**Actions:** `<25` strong_sell · `≥25` sell · `≥40` reduce · `≥50` hold · `≥65` accumulate · `≥75` buy · `≥85` strong_buy

## 9. Conflict / Gate Rules

- Material premium (≥25% above IV) → cap at Hold
- Negative MoS → cap at Accumulate (blocks Strong Buy)
- Excellent business + deep MoS → score boost
- Weak business + cheap → value-trap penalty
- Strong growth + weak BS · wide moat + poor allocation · HQ + low MoS

## 10. Usage Examples

```python
from investment_recommendation import (
    InvestmentRecommendationEngine,
    ValuationSignals,
)

signals = ValuationSignals.from_overall(overall_valuation_result)
# or: ValuationSignals(intrinsic_value_per_share=100, current_market_price=70)

result = InvestmentRecommendationEngine().analyze(
    valuation=signals,
    business_quality=bq_agg,
    economic_moat=em,
    management_quality=mq,
    financial_strength=fs,
    earnings_quality=eq,
    growth_quality=gq,
)
print(result.recommendation, result.score.value, result.investment_thesis)
```

## 11. Testing

```bash
pytest packages/investment_recommendation/tests -q --import-mode=importlib -p no:cov
```

## 12. Governance

- [FEATURE_007_INVESTMENT_RECOMMENDATION.md](../../docs/FEATURE_007_INVESTMENT_RECOMMENDATION.md)
- [ADR-FEATURE-007-001](../../docs/adr/ADR-FEATURE-007-001-investment-recommendation.md)

## 13. Limitations

- Research-only — not advice or an order router
- MoS depends on upstream IV quality
- Platform composition deferred

## 14. Future Extensions

- Richer penalty schedules · portfolio constraints · platform composition (deferred)
