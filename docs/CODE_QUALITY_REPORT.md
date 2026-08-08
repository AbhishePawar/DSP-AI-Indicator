# Code Quality Report — EPIC-P7.2

**Date:** 2026-07-29  
**Scope:** Automated inspection only — no analytical refactors.

## Tooling already in CI

| Gate | Workflow |
|---|---|
| Ruff lint | `ci.yml` |
| Black format check | `ci.yml` |
| mypy | `ci.yml` |
| Architecture boundary tests | `ci.yml` |
| Frontend vitest + build | `frontend.yml` |

## TODOs / FIXMEs

| Finding | Assessment |
|---|---|
| Literal `TODO`/`FIXME` in product engines | Not used as work markers in sampled advisor UI (`status: "todo"` is domain enum, not debt) |
| Test assertions rejecting `TODO` placeholders | Present in institutional dashboard tests — healthy |

## Oversized files (>800 LOC) — monitor

| File | Lines (approx) | Note |
|---|---|---|
| `packages/dsp_platform/.../platform.py` | ~1550 | Façade composition — do not “clean” under P7.2 |
| `packages/dsp_platform/.../__init__.py` | ~1230 | Public exports |
| `apps/web/.../admin-console/Sections.tsx` | ~1286 | UI surface |
| `apps/web/.../mapInstitutionalDashboard.ts` | ~1194 | Presentation mapping |
| Valuation consensus modules | ~900+ | **Frozen** — out of scope |

## Dead code / unused imports

- Enforced continuously by Ruff/CI — failures block merge.  
- No mass auto-deletion in this epic (risk of behaviour change).

## Duplicated logic

- Presentation mappers intentionally mirror API DTOs (thin client rule).  
- Duplicate legal policy version files retained for history.

## Quality posture

| Dimension | Score |
|---|---|
| Lint/format gates | 9 |
| Type checking | 8 |
| Size / complexity debt | 7 |
| TODO hygiene | 8 |
| **Overall code quality** | **8.0** |

## Recommendations (future epics — not P7.2)

1. Split oversized UI section components behind presentation-only boundaries.  
2. Add Knip/depcheck for unused exports.  
3. Keep engines frozen while reducing façade `__init__` surface carefully.
