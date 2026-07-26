<!-- ASI-005-PACKAGE-CARD -->
# recommendation

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

DSP Recommendation Intelligence — assemble, synthesize, report (G1.0–G1.3)

## 2. Responsibilities

Provide the stable `recommendation` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Production · Frozen** · Version **0.4.0** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`__all__` exports (35): `AssemblyContext`, `AssemblyResult`, `AssemblyStatus`, `CitationSection`, `ComparisonReference`, `ConfidenceLevel`, `ConflictSeverity`, `DecisionReference`, `EngineContext`, `EngineResult`, `EngineStatus`, `PortfolioReference`, … (+23)

## 5. Package Structure

`packages/recommendation/src/recommendation/` · `packages/recommendation/tests/` · local `pyproject.toml` when present.

## 6. Dependencies

`core`

## 7. Architecture Notes

Architecture allowlists / freeze policy apply. See appendix and [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
import recommendation
print(recommendation.__version__)
```

Worked examples live in `packages/recommendation/tests/`.

## 9. Testing

```bash
pytest packages/recommendation/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

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
