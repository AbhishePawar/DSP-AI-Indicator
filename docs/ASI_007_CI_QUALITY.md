# ASI-007 — CI Quality

| Field | Value |
|---|---|
| **Initiative** | Architecture Stabilization Initiative (ASI) |
| **Task** | ASI-007 · Phase 6 CI Quality |
| **Status** | **Complete** (awaiting human approval before ASI-008) |
| **Date** | 2026-07-26 |
| **Production code** | **Unchanged** |
| **CI Health Score** | **88 / 100** |

## Purpose

Align GitHub Actions with the living monorepo: integrity, architecture, smoke, and full
package tests. Reliability over features.

Authority → [ASI_IMPLEMENTATION_FRAMEWORK.md](ASI_IMPLEMENTATION_FRAMEWORK.md) ·
Operator guide → [CI.md](CI.md).

---

## Unlock scope (temporary)

| Path | Action |
|---|---|
| `.github/workflows/ci.yml` | Monorepo quality gates |
| `pyproject.toml` (`[project.optional-dependencies].dev`) | CI/test runtime deps |
| `Makefile` | Local/CI parity targets |
| `scripts/ci_repository_integrity.py` | Integrity gate |
| `docs/CI.md` · `docs/ASI_007_*.md` · `docs/asi/**` | Docs / metrics |
| `docs/DSP_STATUS.md` · `DSP_CHANGELOG.md` | Progress |

**Re-freeze:** CI unlock closed after this task; workflow remains the permanent gate.

---

## 1. CI Quality Report

| Gate | Result |
|---|---|
| CI validates registered monorepo packages | **PASS** (designed) |
| Architecture tests in CI | **PASS** (blocking step) |
| Monorepo smoke in CI | **PASS** (blocking step) |
| Integrity script | **PASS** locally (`INTEGRITY PASS`, 30 paths) |
| Style/type gates retained | **PASS** (ruff/black/mypy) |
| Product behaviour changed | **No** |

Local verification: integrity **PASS** · architecture modules green · smoke **12 PASS**.

---

## 2. CI Workflow Audit

### Before (narrow)
- Single pytest invocation with `--cov=core --cov=dsp` only
- No explicit architecture / smoke / integrity stages
- Dev install lacked FastAPI/Starlette stack for HTTP tests
- Minimal reporting

### After (ASI-007)
| Step | Purpose |
|---|---|
| Install `-e ".[dev]"` + pip cache | Discovery + HTTP/security test deps |
| `scripts/ci_repository_integrity.py` | Registration / import / export integrity |
| `find … test_architecture*.py` → pytest | Architecture + cycles |
| `test_asi_monorepo_smoke.py` | Façade / registration smoke |
| Full `pytest packages` + cov XML | Monorepo suite |
| Ruff / Black / mypy | Existing quality |
| Job summary table | Failure diagnostics |

Python matrix: **3.11**, **3.12**. Concurrency cancel-in-progress enabled.

---

## 3. CI Coverage Report

| Area | Status |
|---|---|
| Coverage collection | Expanded from core/dsp-only flags to project `tool.coverage.run` sources via `--cov` |
| Codecov upload | Optional (`fail_ci_if_error: false`) on 3.12 |
| Threshold gate | **Not** introduced (avoids vanity fail) |

---

## 4. Architecture Integration Report

CI executes every `test_architecture.py` / `test_architecture_*.py` under `packages/`.
Failures block the job.

---

## 5. Smoke Test Integration Report

CI executes `packages/dsp_platform/tests/test_asi_monorepo_smoke.py` as a dedicated blocking step
before the full suite (fast fail on registration/façade breakage).

---

## 6. Repository Validation Report

| Check | Mechanism |
|---|---|
| Package discovery paths exist | Integrity script |
| Imports + `__all__` | Integrity script + smoke |
| `economic_moat` registered | Integrity assert |
| Orphan `data-ingestion` not registered | Integrity assert |

---

## 7–9. Debt / Metrics / Package Health

→ [asi/TECHNICAL_DEBT_REGISTER.md](asi/TECHNICAL_DEBT_REGISTER.md)  
→ [asi/ENGINEERING_METRICS_DASHBOARD.md](asi/ENGINEERING_METRICS_DASHBOARD.md)

CI dimension: **PASS** (aligned). Residual: full remote Actions runtime confirmation on next push.

---

## 10. ADRs

| ADR | Title | Status |
|---|---|---|
| [ADR-ASI-007-001](adr/ADR-ASI-007-001-monorepo-ci-quality-gates.md) | Blocking monorepo CI gates (integrity/arch/smoke/full) | Accepted |

---

## 11. Rollback Plan

→ [asi/rollback/ASI-007.md](asi/rollback/ASI-007.md)

---

## 12. CI Health Score

| Field | Value |
|---|---|
| **Score** | **88 / 100** |
| Method | Start 40 (narrow cov); +20 integrity; +15 arch; +10 smoke; +8 full suite; −5 pending first remote green proof |
| Trend | ↑ |

---

## Executive Summary

### CI improvements
- Blocking integrity, architecture, smoke, and full monorepo pytest
- Dev extras for FastAPI/Starlette/httpx/Pydantic
- Makefile parity (`ci-local`, `test-arch`, `test-smoke`, `test-integrity`)
- Job summary diagnostics

### Remaining CI debt
- Confirm first remote Actions run on `main`/PR
- Optional: Black/Ruff churn if formatting drift appears on Ubuntu (not rewritten in ASI-007)
- Coverage thresholds still unset (intentional)

### Recommendation for ASI-008
Final Repository Audit — re-freeze confirmation, STATUS checkpoint, no feature creep, close ASI.

**Stop.** Do not begin ASI-008 until explicit approval.
