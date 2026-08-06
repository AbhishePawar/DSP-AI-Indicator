# EPIC-R001 — Canonical Research Object

Status: **COMPLETE** · Priority: P0

## Summary

Immutable, read-only Research Object aggregating:

- Unified Data Bundle (**D005**)
- Existing analysis / valuation / quality / risk / recommendation outputs

No new calculations, scoring, valuation, or AI reasoning.

## Docs

| Doc | Path |
|---|---|
| Specification | [EPIC_R001_RESEARCH_OBJECT_SPEC.md](EPIC_R001_RESEARCH_OBJECT_SPEC.md) |
| Architecture | [EPIC_R001_ARCHITECTURE.md](EPIC_R001_ARCHITECTURE.md) |
| Developer Guide | [EPIC_R001_DEVELOPER_GUIDE.md](EPIC_R001_DEVELOPER_GUIDE.md) |

## API

- `GET /api/v1/research/object/schema`
- `POST /api/v1/research/object`

## Compliance

| Check | Result |
|---|---|
| CV-001 authenticity | PASS — unavailable, never fabricate |
| CV-002 thin / no client math | PASS — aggregate-only |
| CV-003 explainability | PASS — stage_summaries pass-through |
| RS-001…RS-010 compatible | PASS — section map + unavailable allowed |
| Thin architecture | PASS |
| No breaking changes | PASS — additive routes only |
| D001–D005 untouched | PASS |

## Final

**PASS** — production-ready canonical Research Object contract.
