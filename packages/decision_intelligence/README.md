# Decision Intelligence

Phase B2 — investor-facing **Decision Pack** synthesis.

Decision Intelligence sits **above** Recommendation. It never recalculates
valuation, MoS, votes, or engine outputs. It consumes only:

- `ai_committee.CommitteeReport`
- `contracts.Recommendation`

and produces:

1. **Decision Brief** — why / attribution / evidence / assumptions /
   invalidators / watchlist
2. **Decision Assurance** — deterministic robustness + investor guidance
3. **Decision Pack** — Recommendation + Brief + Assurance
   (+ optional `evidence_bundle_ref` — citation only, never embeds bundles)

## Architecture position

```
DSPPlatform
    ↓
Orchestration
    ↓
Analysis Engines
    ↓
Committee
    ↓
Recommendation
    ↓
Decision Intelligence
        ├── Decision Brief
        └── Decision Assurance
                ↓
          Decision Pack
```

## Package structure

```
packages/decision_intelligence/
├── README.md
├── pyproject.toml
├── src/decision_intelligence/
│   ├── __init__.py          # public API only
│   ├── exceptions.py
│   ├── service.py           # DecisionIntelligenceService
│   ├── brief/               # Decision Brief builder
│   ├── assurance/           # deterministic assurance + guidance
│   └── models/              # DecisionBrief, AssuranceAssessment, DecisionPack
└── tests/
```

## Public API

```python
from decision_intelligence import (
    DecisionIntelligenceService,
    DecisionPack,
    DecisionBrief,
    AssuranceAssessment,
    AssuranceLevel,
    GuidanceStance,
    present_decision_pack,
)

pack: DecisionPack = DecisionIntelligenceService().build_pack(
    committee_report,
    recommendation,
)

view = present_decision_pack(pack)
# view.decision / view.robustness / view.valuation / view.committee /
# view.why / view.caution / view.action / view.watch
```

Platform consumers should prefer:

```python
from dsp_platform import DSPPlatform

pack = platform.analyze_decision_pack(request)
# platform.analyze(request) still returns Recommendation (compat)
```

## Decision Brief fields

| Field | Purpose |
|---|---|
| `headline` | One-line decision statement |
| `executive_summary` | Compact CIO-style narrative |
| `attribution` | Supporting / dissenting / neutral members |
| `evidence_highlights` | Strongest / weakest evidence |
| `key_assumptions` | What must remain true |
| `invalidators` | What would reopen the decision |
| `monitoring_watchlist` | What to watch next |

## Decision Assurance (deterministic only)

Robustness bands: `HIGH` | `MODERATE` | `GUARDED` | `LOW`

Derived only from agreement, dissent, evidence breadth, MoS availability,
and recommendation context — **no ML / LLM / probabilistic scoring**.

Investor guidance stances:

- `INVEST_IMMEDIATELY`
- `ACCUMULATE_GRADUALLY`
- `WAIT_FOR_CONFIRMATION`
- `REVIEW_AFTER_EARNINGS`
- `MONITOR_MACRO_CHANGE`
- `WATCH_VALUATION`
- `STAND_ASIDE`

## Sequence diagram

```
Caller                 DSPPlatform              Orchestration
  │ analyze_decision_pack(req) │                      │
  │───────────────────────────▶│ analyze(req)         │
  │                            │─────────────────────▶│
  │                            │◀─ CommitteeReport ───│
  │                            │                      │
  │                            │ RecommendationMapper.map
  │                            │ DecisionIntelligenceService.build_pack
  │◀──────── DecisionPack ─────│                      │
```

## Forbidden

- Engine / provider imports
- MoS or valuation recalculation
- Vote casting or recommendation mutation
- Behavioral / Portfolio / Risk / Research / Dashboard / LLM features

## Dependencies

```
contracts ◄── decision_intelligence ──► ai_committee
                   ▲
                   │ (composition only)
             dsp_platform
```
