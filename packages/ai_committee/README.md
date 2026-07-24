# AI Committee — Investment Committee

`ai_committee` is the platform's **AI Investment Committee** (Section 3.11
of `docs/DSP_AI_INDICATOR_ARCHITECTURE.md`): the orchestration layer that
combines evidence from analytical engines into one investment decision
and an auditable deliberation report.

**Sprint 8.1** proves the architecture scales from three members to four
by adding `ValuationMember` — still no LLM, no weights, no probabilities.

```
AnalysisResult ──────────────▶ TechnicalMember ──┐
CompanyAnalysis ─────────────▶ FundamentalMember ─┤
EconomicAssessment ──────────▶ EconomicMember ────┼─▶ InvestmentCommittee
ValuationAssessment ─────────▶ ValuationMember ──┘         │
                                                           ▼
                                                   CommitteeReport
```

## Purpose

Institutional research platforms deliberate across lenses. This package
models that deliberation as registered committee members, standardized
opinions, deterministic voting, and a reproducible report.

## Architecture

```
CommitteeInput(technical, fundamental, economic)
     │
     ▼
InvestmentCommittee.deliberate()
     │
     ├─ TechnicalMember.analyze(context)   → Opinion
     ├─ FundamentalMember.analyze(context) → Opinion
     ├─ EconomicMember.analyze(context)    → Opinion
     │
     ├─ MemberVote × N
     │
     ├─ aggregate_recommendations(...)     → Decision
     │
     └─ CommitteeReport
```

## Folder Structure

```
packages/ai_committee/
├── README.md
├── pyproject.toml
├── src/ai_committee/
│   ├── enums.py
│   ├── models.py              # CommitteeInput(+economic), Opinion, …
│   ├── voting.py              # equal-weight plurality
│   ├── members/
│   │   ├── technical.py
│   │   ├── fundamental.py
│   │   └── economic.py        # Sprint 6.1
│   └── committee/service.py
└── tests/
```

## Public APIs

| Symbol | Role |
|---|---|
| `InvestmentCommittee` | `register()`, `deliberate(context)` |
| `CommitteeMember` | ABC — `analyze(context) -> Opinion` |
| `TechnicalMember` | Indicator Engine liaison |
| `FundamentalMember` | Fundamental Engine liaison |
| `EconomicMember` | Economic Engine liaison (**new**) |
| `CommitteeInput` | `technical`, `fundamental`, `economic` |
| `Opinion` / `MemberVote` / `InvestmentDecision` / `CommitteeReport` | |
| `Decision` | BUY / HOLD / SELL / NEUTRAL |

## Usage Example

```python
from ai_committee import (
    CommitteeInput,
    EconomicMember,
    FundamentalMember,
    InvestmentCommittee,
    TechnicalMember,
)

committee = InvestmentCommittee(
    members=[
        TechnicalMember(),
        FundamentalMember(),
        EconomicMember(),
    ]
)

report = committee.deliberate(
    CommitteeInput(
        instrument=instrument,
        technical=indicator_engine.analyze(price_series),
        fundamental=fundamental_engine.analyze(snapshot),
        economic=economic_engine.analyze(macro_snapshot),
    )
)

print(report.decision.decision)
print(report.voting_summary)
print(report.explanation)
```

Two-member callers remain valid — pass an explicit roster and omit
`economic`:

```python
committee = InvestmentCommittee(
    members=[TechnicalMember(), FundamentalMember()]
)
```

## Voting Matrix (Sprint 6.1)

Equal-weight plurality. Clear plurality wins. BUY↔SELL ties for the
lead → NEUTRAL. BUY↔HOLD or SELL↔HOLD ties → HOLD (preserves Sprint 5.0
two-member behavior).

| Votes | Overall |
|---|---|
| BUY BUY BUY | BUY |
| SELL SELL SELL | SELL |
| BUY BUY HOLD | BUY |
| SELL SELL HOLD | SELL |
| BUY HOLD HOLD | HOLD |
| SELL HOLD HOLD | HOLD |
| BUY BUY SELL | BUY |
| SELL SELL BUY | SELL |
| BUY SELL HOLD | **NEUTRAL** |
| BUY SELL SELL | SELL |
| BUY + HOLD (2 members) | HOLD |
| BUY + SELL (2 members) | NEUTRAL |

## Dependency Diagram

```
contracts  ◀── ai_committee (DTOs only)
    ▲
core
    ▲
engines ──▶ orchestration (maps engine → DTOs) ──▶ ai_committee
```

`ai_committee` never imports engine packages. Engines never depend on
`ai_committee`.

## Sequence Diagram

```
Caller
  │ deliberate(CommitteeInput)
  ▼
InvestmentCommittee
  ├─ TechnicalMember.analyze()  → Opinion(BUY|HOLD|SELL)
  ├─ FundamentalMember.analyze() → Opinion(...)
  ├─ EconomicMember.analyze()    → Opinion(...)  # maps EconomicContext
  ├─ ValuationMember.analyze()   → Opinion(...)  # maps ValuationContext (+ MoS)
  ├─ aggregate_recommendations(votes)
  └─ CommitteeReport(decision, explanation, evidence trail)
```

## Design Decisions

1. **Additive `CommitteeInput` contexts** — optional DTOs; members omit
   themselves when the matching context is ``None``.
2. **Contracts-only inputs (Phase A2)** — `TechnicalContext`,
   `FundamentalContext`, `EconomicContext`, `ValuationContext`.
3. **Plurality voting** — BUY BUY SELL → BUY (majority), not NEUTRAL.
   Three-way BUY/SELL/HOLD split remains NEUTRAL.
4. **No information loss** — DTO reasoning and evidence are carried onto
   `Opinion` (with a member prefix). MoS is never recalculated.
5. **Macro contexts are not instrument-checked** — economic context
   is country-level; equity instrument matching stays on technical /
   fundamental / valuation members.

## Future Roadmap

- ValuationMember / BehavioralMember / RiskMember
- Weighted voting via `Opinion.confidence` (still reserved as `None`)
- Map `InvestmentDecision` → `contracts.Recommendation`
