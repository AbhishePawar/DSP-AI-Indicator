# FEATURE-002 — Management Quality & Capital Allocation (Phase 1)

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Complete** — awaiting approval for next feature |
| **Last updated** | 2026-07-26 |
| **Package** | `management_quality` **0.1.0** |
| **ADR** | [ADR-FEATURE-002-001](adr/ADR-FEATURE-002-001-management-quality-core.md) |

## Executive Summary

Phase 1 delivers an explainable Management Quality engine in
`packages/management_quality` only. Six Buffett/Munger-aligned dimensions produce
component scores, overall score, rating (`poor` → `excellent`), strengths,
weaknesses, risks, and evidence. Architecture allowlists for other domains and
`/api/v1` are unchanged. Platform / API / frontend composition is deferred.

---

## Scoring methodology

| Dimension | Weight | Primary proxies |
|---|---|---|
| Capital Allocation | 0.22 | BQ CA assessments + ROIC |
| Shareholder Orientation | 0.18 | Buybacks / dividends / cash generation |
| Governance | 0.15 | Hygiene proxies only (**capped**) |
| Financial Discipline | 0.18 | Leverage, cash conversion, WC efficiency |
| Execution Quality | 0.15 | Revenue/margin/earnings consistency |
| Integrity & Transparency | 0.12 | Earnings quality / exceptional items |

**Ratings:** `<40` poor · `≥40` below_average · `≥55` average · `≥70` good · `≥85` excellent

---

## Architecture impact

| Surface | Impact |
|---|---|
| New package | `management_quality` registered |
| Package boundaries (others) | **Unchanged** |
| `dsp_platform` composition | **Not wired** (forbidden) |
| HTTP `/api/v1` | **Unchanged** |
| Frontend | **Unchanged** |

---

## Test results

```
pytest packages/management_quality/tests — 22 passed
monorepo smoke — includes ManagementEngine
```

---

## Files created / modified

### Created
Full `packages/management_quality/` tree · FEATURE report · ADR

### Modified
Root `pyproject.toml` registration · dsp_platform smoke/cycles/forbidden ·
integrity script · living STATUS/CHANGELOG/VERSION_MATRIX/debt/dashboard

---

## Feature health score

**91 / 100** — complete Phase 1 core; deferred: governance data providers, platform wiring.

---

## Remaining technical debt

- TD-F001 moat platform composition (prior)
- TD-F002 moat evidence providers (prior)
- TD-F003 management_quality platform composition (new)
- TD-F004 governance / filings / regulatory providers (new)

---

## Recommended next feature

After approval: third core domain (e.g. Industry / Risk deepening) **or** a dedicated
composition epic once several domains exist — **do not start platform wiring without approval**.

---

## Definition of Done

| Criterion | Met |
|---|---|
| Architecture unchanged (no platform wiring) | ✓ |
| Public API typed & documented | ✓ |
| Tests + architecture verification | ✓ |
| Deterministic / explainable | ✓ |
| Evidence-backed | ✓ |
