<!-- ASI-005-PACKAGE-CARD -->
# decision_intelligence

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

Decision Brief, Assurance, Decision Pack (+ optional Evidence Bundle refs)

## 2. Responsibilities

Provide the stable `decision_intelligence` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Production · Frozen** · Version **0.2.0** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`__all__` exports (23): `AgreementQuality`, `AssuranceAssessment`, `AssuranceLevel`, `AssumptionRiskLevel`, `ConfidenceDriver`, `DecisionBrief`, `DecisionIntelligenceError`, `DecisionIntelligenceService`, `DecisionPack`, `DecisionPackEvidenceSummary`, `DecisionPackView`, `DecisionResilience`, … (+11)

## 5. Package Structure

`packages/decision_intelligence/src/decision_intelligence/` · `packages/decision_intelligence/tests/` · local `pyproject.toml` when present.

## 6. Dependencies

`contracts`, `core`, `ai_committee`, `industry`

## 7. Architecture Notes

Architecture allowlists / freeze policy apply. See appendix and [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
import decision_intelligence
print(decision_intelligence.__version__)
```

Worked examples live in `packages/decision_intelligence/tests/`.

## 9. Testing

```bash
pytest packages/decision_intelligence/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

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
