# FEATURE-005 — Growth Quality & Capital Reinvestment (Phase 1)

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Complete** — awaiting approval |
| **Last updated** | 2026-07-26 |
| **Package** | `growth_quality` **0.1.0** |
| **ADR** | [ADR-FEATURE-005-001](adr/ADR-FEATURE-005-001-growth-quality-core.md) |

## Executive Summary

Phase 1 delivers an explainable Growth Quality engine in
`packages/growth_quality` only. Six Buffett-aligned dimensions produce
component scores, overall Growth Quality Score, and rating
(`very_weak` → `exceptional`). Prefer sustainable compounding and
high-return reinvestment; do not reward leverage- or dilution-driven expansion.
No platform/API/UI/AI Committee wiring.

## Scoring methodology

| Dimension | Weight |
|---|---|
| Revenue Growth Quality | 0.18 |
| Earnings Growth Quality | 0.18 |
| Reinvestment Capability | 0.20 |
| Capital Allocation Support | 0.16 |
| Growth Sustainability | 0.16 |
| Growth Risk (inverted) | 0.12 |

**Ratings:** `<40` very_weak · `≥40` weak · `≥55` moderate · `≥70` strong · `≥85` exceptional

## Architecture impact

New package registered; `/api/v1` unchanged; platform not composed.

## Test results

**23 PASS** package suite · integrity PASS · smoke/cycles PASS

## Feature health score

**91 / 100**

## Remaining technical debt

- TD-F009 platform composition of `growth_quality`
- TD-F010 customer concentration / saturation / deal-attribution providers
- Prior TD-F001…F008

## Recommended next feature

After approval: sixth core domain **or** composition epic — **do not start platform/API/UI/AI Committee without approval**.
