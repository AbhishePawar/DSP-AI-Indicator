# Comparison (AIMF C2.5)

Qualitative peer comparison of DecisionPacks after peer eligibility.

## Install / import

```python
from comparison import QualitativeComparisonEngine, ComparisonStatus
from industry import (
    IndustryTaxonomy,
    InvestmentCharacteristicsRegistry,
    IndustryMethodologyRegistry,
    PeerEligibilityPolicyRegistry,
    InstrumentIndustryRegistry,
    PeerEligibilityEvaluator,
    seed_peer_eligibility_context,
)

tax = IndustryTaxonomy()
chars = InvestmentCharacteristicsRegistry()
methods = IndustryMethodologyRegistry(tax, chars)
policies = PeerEligibilityPolicyRegistry(tax)
assignments = InstrumentIndustryRegistry(tax)
seed_peer_eligibility_context(tax, chars, methods, policies, assignments)
engine = QualitativeComparisonEngine(
    evaluator=PeerEligibilityEvaluator(
        assignments=assignments, methodologies=methods, policies=policies
    ),
    methodologies=methods,
)
result = engine.compare_packs((pack_a, pack_b))
assert result.status in {
    ComparisonStatus.COMPLETE,
    ComparisonStatus.DEGRADED,
    ComparisonStatus.REFUSED,
}
```

## Rules

- No scores, ranks, or league tables
- Refusal preferred to misleading comparison
- Dimensions come only from IndustryMethodology

Dependencies: `contracts`, `core`, `decision_intelligence`, `universe`, `industry`.
