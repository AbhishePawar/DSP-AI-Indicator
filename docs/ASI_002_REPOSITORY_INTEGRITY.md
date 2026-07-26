# ASI-002 — Repository Integrity

| Field | Value |
|---|---|
| **Initiative** | Architecture Stabilization Initiative (ASI) |
| **Task** | ASI-002 · Phase 1 Repository Integrity |
| **Status** | **Complete** (awaiting human approval before ASI-003) |
| **Date** | 2026-07-26 |
| **Checkpoint before change** | `eb3c597` (`v3.0.0-business-quality`) |
| **Feature development** | **Frozen** |
| **Business logic changes** | **None** |

## Purpose

Verify and correct repository integrity only: discovery, registration, versions,
orphans, and documentation consistency. No features, no API/behavior changes.

Authority → [ASI_IMPLEMENTATION_FRAMEWORK.md](ASI_IMPLEMENTATION_FRAMEWORK.md) ·
Unfreeze list → [ASI_001_REPOSITORY_PREPARATION.md](ASI_001_REPOSITORY_PREPARATION.md).

---

## Unlock scope (temporary)

| Path | Action |
|---|---|
| `pyproject.toml` (root) | Register `economic_moat`; add `compliance` to isort/coverage |
| `packages/ai_committee/pyproject.toml` | Align version metadata to `__version__` |
| `packages/economic/pyproject.toml` | Align version metadata to `__version__` |
| `packages/economic_moat/README.md` | Fix broken doc link (legacy reference) |
| `docs/VERSION_MATRIX.md` | Living package baseline + orphan note |
| `docs/ASI_002_*.md` / `docs/asi/**` / `docs/adr/**` | Reports, debt, dashboard, ADRs, rollback |
| `docs/DSP_STATUS.md` / `docs/DSP_CHANGELOG.md` | Integrity health |
| `docs/DEPENDENCY_GRAPH.md` | Note `economic_moat` scaffold edge |
| `docs/ASI_IMPLEMENTATION_FRAMEWORK.md` | Mark framework Accepted (ASI-002 authorized) |

**Not unlocked / not modified:** valuation/financial/BQ engine logic, CI workflows,
`packages/data-ingestion/**` contents, package moves/renames.

**Re-freeze:** all temporary unlocks closed at end of this task (docs remain living).

---

## 1. Repository Inventory

**31** directories under `packages/`.

| Package | Import | Version truth | pyproject | Root registered | README | tests | Status |
|---|---|---|---|---|---|---|---|
| `ai_committee` | `ai_committee` | 0.3.0 | Yes (aligned) | Yes | No | Yes | Production frozen |
| `api_platform` | `api_platform` | 0.1.0 | Yes | Yes | No | Yes | Production frozen |
| `business_quality` | `business_quality` | 0.7.0 | Yes | Yes | Yes | Yes | Phase 3 frozen |
| `comparison` | `comparison` | 0.2.0 | Yes | Yes | Yes | Yes | Frozen |
| `compliance` | `compliance` | 0.1.0 | Yes | Yes | Yes | Yes | Frozen |
| `contracts` | `contracts` | 0.3.0 | No | Yes | Yes | Yes | Frozen |
| `copilot` | `copilot` | 0.5.0 | Yes | Yes | No | Yes | Frozen |
| `core` | `core` | 0.2.0 | No | Yes | Yes | Yes | Frozen |
| `data-ingestion` | `data_ingestion` | — | No | **No** | No | stub | **Orphan scaffold** |
| `data_engine` | `data_engine` | 0.6.0 | No | Yes | Yes | Yes | Frozen |
| `decision_intelligence` | `decision_intelligence` | 0.2.0 | Yes | Yes | Yes | Yes | Frozen |
| `dsp` | `dsp` | 0.2.0 | No | Yes | Yes | Yes | Frozen |
| `dsp_platform` | `dsp_platform` | 0.6.0 | No | Yes | Yes | Yes | Frozen |
| `economic` | `economic` | 0.1.1 | Yes (aligned) | Yes | Yes | Yes | Frozen |
| `economic_moat` | `economic_moat` | 0.1.0 | Yes | **Yes (ASI-002)** | Yes | Yes | F4.1 scaffold only |
| `financial` | `financial` | 0.7.0 | Yes | Yes | Yes | Yes | Phase 2 frozen |
| `fundamental` | `fundamental` | 0.1.0 | No | Yes | Yes | Yes | Frozen |
| `industry` | `industry` | 0.9.0 | Yes | Yes | Yes | Yes | Frozen |
| `knowledge_graph` | `knowledge_graph` | 0.4.0 | Yes | Yes | No | Yes | Frozen |
| `orchestration` | `orchestration` | 0.2.0 | No | Yes | Yes | Yes | Frozen |
| `portfolio` | `portfolio` | 0.5.0 | Yes | Yes | No | Yes | Frozen |
| `production_platform` | `production_platform` | 0.1.0 | Yes | Yes | No | Yes | Frozen |
| `quantitative_risk` | `quantitative_risk` | 0.3.0 | Yes | Yes | No | Yes | Frozen |
| `recommendation` | `recommendation` | 0.4.0 | Yes | Yes | Yes | Yes | Frozen |
| `research` | `research` | 0.4.0 | Yes | Yes | No | Yes | Frozen |
| `risk` | `risk` | 0.5.0 | Yes | Yes | No | Yes | Frozen |
| `security_platform` | `security_platform` | 0.1.0 | Yes | Yes | No | Yes | Frozen |
| `snapshot_bridge` | `snapshot_bridge` | 0.1.0 | No | Yes | Yes | Yes | Frozen |
| `universe` | `universe` | 0.1.0 | Yes | Yes | Yes | Yes | Frozen |
| `valuation` | `valuation` | 0.12.0 | Yes | Yes | Yes | Yes | Phase 1 frozen |
| `workflow` | `workflow` | 0.4.0 | Yes | Yes | No | Yes | Frozen |

Import verification (all `packages/*/src` on `sys.path`): **31/31 importable** (including orphan `data_ingestion` stubs and `economic_moat`).

---

## 2. Package Discovery Report

| Finding | Result |
|---|---|
| Duplicate package directories | None |
| Invalid layouts (missing `src/<name>`) | None among registered packages |
| Registered path missing on disk | None |
| Unregistered intentional scaffold | `economic_moat` → **registered** this task |
| Unregistered orphan | `data-ingestion` → **deferred** (ADR-ASI-002-002) |

---

## 3. Registration Audit Report

### Issues found

| ID | Issue | Disposition |
|---|---|---|
| R1 | `economic_moat` absent from root `packages.find`, `pythonpath`, ruff, coverage, isort, mypy_path | **Fixed** |
| R2 | `compliance` in find/pythonpath/ruff but missing from isort `known-first-party` + coverage `source` | **Fixed** |
| R3 | Empty `packages/data-ingestion` not registered | **Deferred** — do not expand monorepo surface without ownership ADR |

### Root registration after ASI-002

All production/foundation packages including `economic_moat` and `compliance` appear consistently across discovery, pytest path, ruff, coverage, and first-party isort lists.

---

## 4. Version Consistency Report

| Surface | Before | After |
|---|---|---|
| `ai_committee` pyproject | 0.2.0 vs `__version__` 0.3.0 | **0.3.0** |
| `economic` pyproject | 0.1.0 vs `__version__` 0.1.1 | **0.1.1** |
| VERSION_MATRIX `economic` / `ai_committee` | Matched `__version__`, mismatched pyproject | Matrix remains `__version__` truth |
| VERSION_MATRIX `economic_moat` | Missing | **0.1.0** listed |
| STATUS “Backend RC v2.0.0” | Conflated API RC with domain milestone | Clarified → API RC `v1.0.0-rc1` + milestone tags |
| VERSION_MATRIX regression 1538 | Stale as living gate | Kept as **historical RC**; living count → STATUS |
| Root project version | 0.1.0 | Unchanged (meta) |

---

## 5. Dependency Audit Report

| Check | Result |
|---|---|
| Broken imports (registered packages) | None observed under full `packages/*/src` path |
| Circular redesign | **Not performed** (architecture → ASI-003) |
| `economic_moat` declared deps | `core`, `financial`, `business_quality` — consistent with F4.1 shell (FA/BQ refs only) |
| Orphan package | `data-ingestion` — empty stubs; no docs refs; not wired |
| Unused root registrations | None |

No dependency graph redesign. See [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) note for `economic_moat`.

---

## 6. Legacy Reference Report

| Finding | Action |
|---|---|
| `packages/economic_moat/README.md` → missing `docs/F4_1_ECONOMIC_FRAMEWORK.md` | **Fixed** — point to STATUS / ASI framework |
| Historical docs citing `v1.0.0-rc1` / 1538 | **Preserved** (freeze history); living truth in STATUS + VERSION_MATRIX note |
| `docs/C4_0_PORTFOLIO_INTELLIGENCE_DESIGN.md` “No packages/portfolio yet” | **Deferred** to ASI-005 (docs excellence); not deleted |
| Missing package READMEs (11 packages) | **Deferred** to ASI-005 (TD-D002) |

---

## 7. Repository Integrity Report

| Dimension | Status |
|---|---|
| Package discovery | **PASS** |
| Registration consistency | **PASS** (orphan deferred with ADR) |
| Imports | **PASS** |
| Version documentation | **PASS** |
| Orphan handling | **PASS** (documented; not silently registered) |
| Feature freeze preserved | **PASS** |
| CI modified | **No** (out of scope) |

**Final Repository Health Score (integrity):** **88 / 100**

Deductions: orphan `data-ingestion` (−5), missing READMEs deferred (−4), CI narrowness deferred (−3).

---

## 8–10. Debt / Metrics / Package Health

→ [asi/TECHNICAL_DEBT_REGISTER.md](asi/TECHNICAL_DEBT_REGISTER.md)  
→ [asi/ENGINEERING_METRICS_DASHBOARD.md](asi/ENGINEERING_METRICS_DASHBOARD.md)  
→ Package Health Summary below

### Package Health Summary (modified packages)

| Package | Overall | Notes |
|---|---|---|
| `economic_moat` | **PASS** | Registered; README link fixed; no analytics added |
| `ai_committee` | **PASS** | Metadata version only |
| `economic` | **PASS** | Metadata version only |
| Root monorepo (`pyproject.toml`) | **PASS** | Registration integrity |

Full checklists embedded in §Package Health Detail.

### Package Health Detail — `economic_moat`

| Dimension | Status | Evidence |
|---|---|---|
| Repository Integrity | PASS | Present under `packages/`; registered root ASI-002 |
| Documentation | PASS | README accurate; broken F4.1 link removed |
| Architecture | PASS | Scaffold only; no F4 analytics |
| Dependencies | PASS | Declared FA/BQ/core only |
| Public API | PASS | Unchanged façade |
| Testing | N/A | No test changes this task |
| Architecture Tests | N/A | ASI-003 |
| CI | N/A | ASI-007 |
| Versioning | PASS | 0.1.0 consistent |
| Metadata | PASS | pyproject present |
| **Overall Health** | **PASS** | |

### Package Health Detail — `ai_committee` / `economic`

| Dimension | Status | Evidence |
|---|---|---|
| Repository Integrity | PASS | Already registered |
| Documentation | N/A | Unchanged |
| Architecture | PASS | No code change |
| Dependencies | PASS | Unchanged |
| Public API | PASS | Unchanged |
| Testing | N/A | Unchanged |
| Architecture Tests | N/A | — |
| CI | N/A | — |
| Versioning | PASS | pyproject ≡ `__version__` |
| Metadata | PASS | Aligned ASI-002 |
| **Overall Health** | **PASS** | |

---

## 11. ADRs

| ADR | Title | Status |
|---|---|---|
| [ADR-ASI-002-001](adr/ADR-ASI-002-001-living-version-truth.md) | Living version truth vs historical API RC | Accepted |
| [ADR-ASI-002-002](adr/ADR-ASI-002-002-orphan-data-ingestion.md) | Defer registration of empty `data-ingestion` | Accepted |
| [ADR-ASI-002-003](adr/ADR-ASI-002-003-register-economic-moat.md) | Register `economic_moat` without enabling F4 analytics | Accepted |

---

## 12. Rollback Plan

→ [asi/rollback/ASI-002.md](asi/rollback/ASI-002.md)

---

## 13. Executive Summary

### Changes made
- Registered `economic_moat` in root monorepo tooling paths.
- Completed `compliance` coverage/isort registration.
- Aligned `ai_committee` / `economic` pyproject versions to `__version__`.
- Corrected VERSION_MATRIX + STATUS version narrative; fixed `economic_moat` README link.
- Documented orphan `data-ingestion`; created 3 ADRs + rollback + metrics/debt updates.

### Files modified
`pyproject.toml` · `packages/ai_committee/pyproject.toml` · `packages/economic/pyproject.toml` · `packages/economic_moat/README.md` · `docs/VERSION_MATRIX.md` · `docs/DSP_STATUS.md` · `docs/DSP_CHANGELOG.md` · `docs/DEPENDENCY_GRAPH.md` · `docs/ASI_IMPLEMENTATION_FRAMEWORK.md` · `docs/asi/*` · `docs/adr/ADR-ASI-002-*.md` · `docs/asi/rollback/ASI-002.md` · this file

### Issues resolved
R1, R2, version metadata drift, broken F4.1 README link, STATUS/API RC conflation (documented).

### Issues deferred
Orphan `data-ingestion` · missing READMEs · CI parity · architecture tests · stale design-doc wording (C4.0).

### Recommendation for ASI-003
Proceed to **Architecture Verification**: additive architecture tests and dependency-boundary enforcement, starting with newly registered `economic_moat` and uneven arch-test packages. Do **not** enable F4 analytics.

**Stop.** Do not begin ASI-003 until explicit approval.
