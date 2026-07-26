# ASI-004 — Package Governance

| Field | Value |
|---|---|
| **Initiative** | Architecture Stabilization Initiative (ASI) |
| **Task** | ASI-004 · Phase 3 Package Governance |
| **Status** | **Complete** (awaiting human approval before ASI-005) |
| **Date** | 2026-07-26 |
| **Feature / architecture / business logic** | **Frozen — unchanged** |
| **Governance Health Score** | **90 / 100** |

## Purpose

Standardise package metadata, version governance, exports visibility, and ownership
**without** changing behaviour or APIs.

Authority → [ASI_IMPLEMENTATION_FRAMEWORK.md](ASI_IMPLEMENTATION_FRAMEWORK.md) ·
[PACKAGE_GOVERNANCE.md](PACKAGE_GOVERNANCE.md).

---

## Unlock scope (temporary)

| Path | Action |
|---|---|
| `packages/*/pyproject.toml` (metadata only) | Add thin manifests; fix compliance deps |
| `packages/*/tests/test_architecture.py` (dep assertions) | Align with new manifests |
| `docs/PACKAGE_*.md` · `docs/ASI_004_*.md` · `docs/asi/**` · `docs/adr/**` | Governance docs |
| `docs/VERSION_MATRIX.md` · `DSP_STATUS` · `DSP_CHANGELOG` | Version / progress |

**Not modified:** domain/engine source, CI, public API shapes, package moves.

**Re-freeze:** metadata unlocks closed; standards remain living docs.

---

## 1. Package Governance Report

| Gate | Result |
|---|---|
| Metadata standard applied | **PASS** — all registered packages have local pyproject |
| Version pyproject ≡ `__version__` | **PASS** (0 mismatches) |
| Public `__all__` resolvable | **PASS** (30/30 registered) |
| Ownership matrix published | **PASS** |
| API behaviour changed | **No** |

---

## 2. Metadata Consistency Report

### Baseline (pre-ASI-004)
- 22 packages with pyproject (`name`/`version`/`description`/`license`)
- 8 registered packages **without** local pyproject (root-owned only)
- 0 version mismatches among existing pyprojects
- Authors/URLs absent package-wide (root owns authors)

### Corrections
| Change | Packages |
|---|---|
| Added thin `pyproject.toml` | `contracts`, `core`, `data_engine`, `dsp`, `dsp_platform`, `fundamental`, `orchestration`, `snapshot_bridge` |
| Removed unused declared dep `core` | `compliance` |
| Authors/URLs mass-add | **Deferred** — inherit root (governance standard §4) |

### Accepted asymmetries
| Item | Rationale |
|---|---|
| Hyphenated dist names (`api-platform`, …) | Existing PEP-style; import remains underscore |
| `business_quality` declares `financial` without import | ADR-ASI-003-001 duck typing |
| Orphan `data-ingestion` without pyproject | ADR-ASI-002-002 — do not register |

---

## 3. Version Governance Report

| Surface | Status |
|---|---|
| pyproject ↔ `__version__` | Aligned for all registered packages |
| VERSION_MATRIX | Updated notes; ASI-004 governance pass recorded |
| DSP_STATUS | Suite **1.3.17**; governance health noted |
| Root `dsp-ai-indicator` 0.1.0 | Unchanged (monorepo meta) |

---

## 4. Public Export Report

| Check | Result |
|---|---|
| Packages with `__all__` | 30/30 registered |
| `__all__` names importable | **0 missing** |
| Entry points / behaviour | **Unchanged** |

---

## 5. Package Ownership Matrix

→ [PACKAGE_OWNERSHIP_MATRIX.md](PACKAGE_OWNERSHIP_MATRIX.md)

---

## 6. Governance Compliance Report

| Standard rule | Compliance |
|---|---|
| Local pyproject for registered packages | **PASS** |
| Version sync | **PASS** |
| `__all__` resolve | **PASS** |
| Orphan not registered | **PASS** |
| No API behaviour change | **PASS** |

---

## 7–9. Debt / Metrics / Package Health

→ [asi/TECHNICAL_DEBT_REGISTER.md](asi/TECHNICAL_DEBT_REGISTER.md)  
→ [asi/ENGINEERING_METRICS_DASHBOARD.md](asi/ENGINEERING_METRICS_DASHBOARD.md)

Touched packages Metadata / Versioning / Public API = **PASS**.

---

## 10. ADRs

| ADR | Title | Status |
|---|---|---|
| [ADR-ASI-004-001](adr/ADR-ASI-004-001-thin-package-pyprojects.md) | Add thin local pyprojects for former root-owned packages | Accepted |
| [ADR-ASI-004-002](adr/ADR-ASI-004-002-compliance-empty-deps.md) | Remove unused `core` dependency from `compliance` | Accepted |

---

## 11. Rollback Plan

→ [asi/rollback/ASI-004.md](asi/rollback/ASI-004.md)

---

## 12. Governance Health Score

| Field | Value |
|---|---|
| **Score** | **90 / 100** |
| Method | Start 75; +10 thin manifests; +5 compliance dep honesty; −0 blockers; −5 deferred authors/URLs/READMEs |
| Trend | ↑ |

---

## Executive Summary

### Governance improvements
- Package governance standard + ownership matrix
- Thin manifests for 8 foundation/composition packages
- Honest `compliance` dependency list

### Metadata / version corrections
- 8 pyprojects added (versions from `__version__`)
- `compliance` dependencies `["core"]` → `[]`
- VERSION_MATRIX notes cleaned

### Recommendation for ASI-005
Documentation Excellence: missing package READMEs, stale design-doc wording — still no feature work.

**Stop.** Do not begin ASI-005 until explicit approval.
