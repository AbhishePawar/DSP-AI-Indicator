# Recommendation

Sprint 7.1 — pure **mapping layer** from committee deliberation to the
canonical public recommendation model.

## Purpose

```
CommitteeReport
      ↓
InvestmentDecision
      ↓
contracts.Recommendation
```

Research Engine, Dashboard, public API, and future SDK must consume
**only** `contracts.Recommendation` — never committee-local types.

## Responsibilities

Translate only:

| Committee field | Recommendation field |
|---|---|
| `decision.decision` | `action` (`RecommendationAction`) |
| Vote agreement ratio | `conviction` ∈ `[0, 1]` |
| `decision.rationale` + `voting_summary` | `rationale` |
| Agreeing opinions' `evidence` | `supporting_evidence` |
| Disagreeing opinions | `dissenting_views` |
| `decision.decided_at` | `generated_at` |
| `instrument` | `instrument` |

No analysis, voting, providers, or engines.

## Package Structure

```
packages/recommendation/
├── README.md
├── src/recommendation/
│   ├── __init__.py
│   ├── exceptions.py
│   └── mapper.py
└── tests/
    └── test_mapper.py
```

## Dependency Diagram

```
contracts ◄── recommendation ──► ai_committee
                    ▲
                    │ (optional convenience)
              orchestration
```

Forbidden direct imports: `data_engine`, `dsp`, `fundamental`,
`economic`, `snapshot_bridge`.

## Mapping Diagram

```
Decision.BUY      → RecommendationAction.BUY
Decision.HOLD     → RecommendationAction.HOLD
Decision.SELL     → RecommendationAction.SELL
Decision.NEUTRAL  → RecommendationAction.HOLD  (contracts has no NEUTRAL)
```

Conviction:

- Unanimous matching votes → `1.0`
- Partial agreement → `agreeing / total`
- `NEUTRAL` conflict → `0.5`

## Sequence Diagram

```
Caller                 RecommendationMapper              contracts
  │ map(CommitteeReport)        │                           │
  │────────────────────────────▶│ Decision → Action         │
  │                             │ Votes → conviction        │
  │                             │ Evidence / dissent        │
  │                             │──────────────────────────▶│ Recommendation
  │◀──── Recommendation         │                           │
```

## Public API

```python
from recommendation import RecommendationMapper

recommendation = RecommendationMapper.map(committee_report)
```

Also: `RecommendationMapper.map_decision(investment_decision, ...)` when
only the final decision object is available.

## Design Decisions

1. **Separate package** — Research/Dashboard need Contracts output without
   importing orchestration or the data plane.
2. **NEUTRAL → HOLD** — Contracts `RecommendationAction` has no neutral;
   HOLD is the institutional “no directional call” action; conviction
   `0.5` and dissenting views preserve the conflict narrative.
3. **No STRONG_BUY / STRONG_SELL yet** — committee does not emit conviction
   tiers; mapping stays 1:1 with BUY/HOLD/SELL until governance defines
   strong thresholds.
4. **Pure / stateless** — classmethods only; no I/O; deterministic.

## Version

`0.1.0`
