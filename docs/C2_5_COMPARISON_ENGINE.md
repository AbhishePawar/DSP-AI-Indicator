# Phase C2.5 — Qualitative Comparison Engine

**Status:** Implemented · Qualitative only · No rankings or scores

## Purpose

Explain differences among eligible peer DecisionPacks. Never declare winners.

## Architecture

```
InvestmentUniverse / DecisionPacks
        ↓
Instrument + Methodology resolution
        ↓
Peer Eligibility (C2.4)
        ↓
QualitativeComparisonEngine
        ↓
ComparisonReport
```

The engine **consumes** IndustryMethodology and PeerEligibilityPolicy.
It owns neither.

## Why no rankings

Scores and league tables create false precision across heterogeneous
business models. A refusal or degraded scope is preferable to a misleading
ordering.

## Qualitative philosophy

- Use only dimensions declared on the active IndustryMethodology
- Observations cite Decision Pack fields (MoS, assurance, agreement, guidance)
- Forbidden language: better / best / winner / score / rank
- Every report includes limitations and research priorities

## Entry validation

```
resolve → peer eligibility → single methodology among included → observe
```

Ineligible or unresolved sets return `ComparisonStatus.REFUSED` with reasons.
Mixed universes return `DEGRADED` with exclusions — never silent downgrade.

## Universe integration

`compare_universe_result(engine, multi_stock_result)` and
`DSPPlatform.compare_universe(...)` (additive). Requires ≥2 successful packs.

## Non-goals

Ranking, scoring, league tables, portfolio recommendations, ML/LLM.

## Future roadmap

Richer industry metric vectors, pairwise methodology injection for RELATED
peers, optional DecisionPackView sections for comparison UI.
