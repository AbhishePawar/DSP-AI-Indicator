# Phase C4.2 — Portfolio Assembler

**Status:** Implemented · Construction / orchestration only

## Purpose

`PortfolioAssembler` is the canonical constructor for immutable `Portfolio`
aggregates from citations.

## Assembly pipeline

```text
DecisionPack references (required)
        ↓
validate_inputs()
        ↓
Attach optional EvidenceBundle references (by instrument)
        ↓
Attach optional ComparisonReport references (holding or portfolio-level)
        ↓
Validate ownership (snapshots / orphans)
        ↓
Construct immutable Portfolio (+ optional as_of snapshot)
        ↓
PortfolioAssemblyResult
```

## Ownership

Assembler owns **construction**. It does not own analysis, constraint
evaluation, scoring, monitoring, or recommendations.

## Validation

Rejects: duplicate holdings/packs, orphan evidence/comparison refs, foreign
snapshot ownership, missing identity, invalid cash metadata.

Optional citation gaps produce `PARTIAL` status + warnings — never fabricated
citations.

## Immutability

Context, result, and assembled `Portfolio` are frozen dataclasses.

## API

- `validate_inputs(context)`
- `portfolio_metadata(context)`
- `assemble(context) -> PortfolioAssemblyResult`
- `assemble_many(contexts)`

## Non-goals

Constraint evaluation, monitoring, diversification/concentration analysis,
optimization, scoring, risk, report generation pipelines.
