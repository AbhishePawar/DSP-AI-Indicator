# investment_committee

## 1. Package Purpose

Deterministic AI Committee Consensus Engine — five independent rule-based
reviewers deliberate public domain and investment-recommendation outputs
(FEATURE-008 Phase 1).

**Distinct from** frozen G-era `ai_committee.InvestmentCommittee`.

## 2. Responsibilities

- Buffett, Value, Quality, Growth, and Risk Officer reviewers
- Confidence-weighted consensus with agreement score and minority opinions
- Escalation flags for classic conflicts (e.g. great business / expensive)
- Evidence-backed thesis and explainability

## 3. Package Status

**Active · Phase 1 multi-agent decision layer** · Version **0.1.0**

## 4. Public API

- `InvestmentCommitteeEngine` — `validate` / `analyze` / `explain`
- `InvestmentCommitteeResult`, `ReviewerOpinion`, `CommitteeConsensus`
- `CommitteeDecision`, `ReviewerRole`

## 5. Package Structure

```
packages/investment_committee/
├── README.md · pyproject.toml
├── src/investment_committee/
└── tests/
```

## 6. Dependencies

- `core` · `valuation`
- `economic_moat` · `management_quality` · `financial_strength`
- `earnings_quality` · `growth_quality`
- `business_quality_aggregator` · `investment_recommendation`

## 7. Architecture Notes

- Package only — not platform / API / frontend / orchestration
- No LLM / ML
- Does not modify frozen `ai_committee`

## 8. Committee Methodology

| Reviewer | Focus |
|---|---|
| Buffett Analyst | Moat, management, MoS, durability |
| Value Investor | IV discount, downside protection |
| Quality Investor | FS, earnings quality, business quality |
| Growth Investor | Growth quality, reinvestment, scalability |
| Risk Officer | Balance sheet, conflicts, uncertainty penalties |

**Consensus:** confidence-weighted rank mean + risk soft veto + agreement score.

## 9. Usage Examples

```python
from investment_committee import InvestmentCommitteeEngine

result = InvestmentCommitteeEngine().analyze(
    recommendation=ir,
    business_quality=bq,
    economic_moat=em,
    management_quality=mq,
    financial_strength=fs,
    earnings_quality=eq,
    growth_quality=gq,
    valuation=valuation_signals,
)
print(result.decision, result.consensus.agreement_score)
```

## 10. Testing

```bash
pytest packages/investment_committee/tests -q --import-mode=importlib -p no:cov
```

## 11. Governance

- [FEATURE_008_INVESTMENT_COMMITTEE.md](../../docs/FEATURE_008_INVESTMENT_COMMITTEE.md)
- [ADR-FEATURE-008-001](../../docs/adr/ADR-FEATURE-008-001-investment-committee.md)

## 12. Limitations

- Research-only · not advice
- Heuristic reviewers · not generative AI
- Platform composition deferred

## 13. Future Extensions

- Additional reviewer roles · tunable veto policy · platform composition (deferred)
