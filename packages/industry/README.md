# Industry Identity, Characteristics, Methodology & Peer Eligibility (AIMF C2.1–C2.4)

DSP owns **IndustryIdentity**. **InvestmentCharacteristics** supply defaults.
**IndustryMethodology** is the policy authority. **Peer eligibility** decides
whether companies may enter a future Comparison Engine — it does not compare them.

## Architecture

```
Instrument → IndustryIdentity → IndustryMethodology → PeerEligibilityPolicy
                                                          ↓
                                              PeerEligibilityResult
                                                          ↓
                                              (future) ComparisonEngine
```

## Peer eligibility (quick start)

```python
from industry import (
    IndustryTaxonomy,
    InvestmentCharacteristicsRegistry,
    IndustryMethodologyRegistry,
    PeerEligibilityPolicyRegistry,
    InstrumentIndustryRegistry,
    PeerEligibilityEvaluator,
    EligibilityOptions,
    seed_peer_eligibility_context,
)

tax = IndustryTaxonomy()
chars = InvestmentCharacteristicsRegistry()
methods = IndustryMethodologyRegistry(tax, chars)
policies = PeerEligibilityPolicyRegistry(tax)
assignments = InstrumentIndustryRegistry(tax)
seed_peer_eligibility_context(tax, chars, methods, policies, assignments)

ev = PeerEligibilityEvaluator(
    assignments=assignments, methodologies=methods, policies=policies
)
assert ev.evaluate_pair("HDFCBANK", "ICICIBANK").status.value == "direct_peer"
assert ev.evaluate_pair("HDFCBANK", "TCS").status.value == "not_comparable"
```

## Out of scope

Comparison Engine, ranking, scoring, metric formulas.

## Compatibility

No changes to DecisionPack, Universe analysis semantics, Committee,
Recommendation, Valuation Engine, or analysis engines.
