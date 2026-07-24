# Phase G0.0A — Recommendation Intelligence Architecture Freeze

**Status:** **FROZEN**  
**Date:** 2026-07-21  
**Preceded by:** [G0.0 Design](G0_0_RECOMMENDATION_INTELLIGENCE_DESIGN.md)  
**Prerequisite:** Baseline v1.0 · Qualitative stack frozen · Quantitative Risk E2.4 frozen · **1281 tests green**

## Freeze declaration

1. Recommendation Intelligence is an **independent bounded context**.  
2. Target package: **`packages/recommendation/`** (domain models from G1.0).  
3. Owns **only** Identity, Profile, Option, Score, Rationale, Conflict, Summary, Report.  
4. Upstream DI / IEF / Comparison / Portfolio / Risk / Research / Quant are **cite only**.  
5. No primary analysis, optimization, execution, OMS, or trading inside the domain.  
6. Pipeline frozen as **Models → (optional Assembler) → Engine → Reporter**.  
7. Legacy Sprint 7.1 `RecommendationMapper` remains a **committee→contracts adapter** —
   not the Recommendation Intelligence engine; it may coexist as a non-domain export.  
8. Numeric scores use **`decimal.Decimal`**; rationale is never replaced by a score.

Conflicts with this document lose unless a later freeze amendment supersedes them.

## Ownership (frozen)

**Owns:** `RecommendationIdentity`, `RecommendationProfile`, `RecommendationOption`,
`RecommendationScore`, `RecommendationRationale`, `RecommendationConflict`,
`RecommendationSummary`, `RecommendationReport`.

**Never owns:** DecisionPack, EvidenceBundle, ComparisonReport, Portfolio,
qualitative/quantitative risk engines, Research engines, OMS, Optimizer.

## Dependencies (frozen)

Runtime domain deps ⊆ `{core}`. Local reference types only. No reverse imports
into frozen upstream packages. Mapper adapter may retain `contracts` /
`ai_committee` imports in its own module without becoming the domain core.

## Roadmap

| Phase | Status |
|---|---|
| G0.0 Design | **DONE** |
| G0.0A Freeze | **DONE / FROZEN** |
| G1.0 Models | **DONE** |
| G1.1 Assembler | **DONE** |
| G1.2 Engine | **DONE** |
| G1.3 Reporter | **DONE** |
| G1.4 Validation | **DONE / FROZEN** |

## PASS / FAIL

**PASS** — Architecture frozen for G1.0 implementation.
