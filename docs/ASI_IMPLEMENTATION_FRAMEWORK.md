# ASI Implementation Framework

| Field | Value |
|---|---|
| **Initiative** | Architecture Stabilization Initiative (ASI) |
| **Version** | `1.1.0` |
| **Status** | **Closed** — ASI complete (ASI-008); framework retained as permanent OS for future quality epics |
| **Last updated** | 2026-07-26 |
| **Authority** | Supplements [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) · [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) |
| **Mode** | Documentation / governance only until task approval |

## Purpose

Enterprise operating system for every ASI task. Improves repository quality, maintainability, consistency, and recoverability **without** new product features.

**Integrity > features. Recovery > rewrite. Freeze by default.**

---

## 1. Executive Summary of Improvements (ASI-001A)

ASI-001 produced a solid freeze map and backlog, but lacked durable governance artifacts. ASI-001A upgrades ASI into a long-term framework:

| # | Improvement | Why it matters |
|---|---|---|
| 1 | **ADR mandate + template** | Significant decisions become recoverable history |
| 2 | **Rollback strategy mandate** | Every change is reversible with validation |
| 3 | **Package Health Checklist** | Uniform PASS/FAIL gate per touched package |
| 4 | **Technical Debt Register** | Debt is tracked, not rediscovered |
| 5 | **Engineering Metrics Dashboard** | Progress and health are visible after every task |
| 6 | **Revised phase order** | Architecture before doc/test expansion |
| 7 | **Enterprise Definition of Done** | No COMPLETE without integrity + audit |
| 8 | **Freeze policy reinforcement** | Temporary unlock → re-freeze + STATUS/CHANGELOG |

These standards are **mandatory** for ASI-002 onward.

---

## 2. Scope & Non-Goals

### In scope
- Repository integrity, architecture verification, package governance
- Documentation excellence, testing excellence, CI fidelity
- Final audit, re-freeze, metrics, debt, ADRs, rollback plans

### Out of scope (forbidden)
- New product features / analytics / ratios / scores
- Valuation, financial, recommendation, or provider logic changes
- `/api/v1` contract breaks
- Peer datasets, market data, UI redesigns
- Expanding the [ASI-001 unfreeze list](ASI_001_REPOSITORY_PREPARATION.md) without explicit amendment + ADR

---

## 3. Revised Phase Structure

Architecture is verified **before** documentation and tests are expanded.

| Phase | Name | Primary ASI task | Objective |
|---|---|---|---|
| **1** | Repository Integrity | ASI-002 | Registration, version truth, orphan refs, freeze log accuracy |
| **2** | Architecture Verification | ASI-003 | Additive architecture tests, dependency truth, boundary enforcement |
| **3** | Package Governance | ASI-004 | Metadata, exports, pyproject consistency (no API shape change) |
| **4** | Documentation Excellence | ASI-005 | Missing/accurate READMEs; freeze-safe docs |
| **5** | Testing Excellence | ASI-006 | Façade smoke, determinism, honest coverage policy |
| **6** | CI Quality | ASI-007 | CI matches monorepo GREEN; tool path parity |
| **7** | Final Repository Audit | ASI-008 | Re-freeze, STATUS checkpoint, no feature creep |

### Why the order changed

| Old order | Problem |
|---|---|
| Docs / Tests before Architecture | Risk of documenting or testing unstable boundaries |
| Governance late | Metadata drift undermines integrity and CI |

| New order | Benefit |
|---|---|
| Integrity → Architecture → Governance | Stable map before narrative and coverage expansion |
| Docs → Tests → CI → Audit | Docs/tests/CI build on verified boundaries |

---

## 4. Mandatory Artifacts (per ASI task)

Every implementation ASI task **must** update or produce:

| Artifact | Location |
|---|---|
| Task brief + unlock scope | `docs/ASI_00N_*.md` |
| ADR (if significant decision) | [asi/ADR_TEMPLATE.md](asi/ADR_TEMPLATE.md) → `docs/adr/` + index in [DSP_DECISION_RECORDS.md](DSP_DECISION_RECORDS.md) |
| Rollback plan | [asi/ROLLBACK_TEMPLATE.md](asi/ROLLBACK_TEMPLATE.md) (in task brief or `docs/asi/rollback/`) |
| Package Health Checklist | [asi/PACKAGE_HEALTH_CHECKLIST.md](asi/PACKAGE_HEALTH_CHECKLIST.md) — one pass per modified package |
| Technical Debt Register | [asi/TECHNICAL_DEBT_REGISTER.md](asi/TECHNICAL_DEBT_REGISTER.md) |
| Engineering Metrics Dashboard | [asi/ENGINEERING_METRICS_DASHBOARD.md](asi/ENGINEERING_METRICS_DASHBOARD.md) |
| STATUS + CHANGELOG | [DSP_STATUS.md](DSP_STATUS.md) · [DSP_CHANGELOG.md](DSP_CHANGELOG.md) |

---

## 5. Per-Task Protocol

```text
1. Read Master Protocol + STATUS + this Framework + ASI-001 unfreeze list
2. Declare unlock paths (subset of approved list only)
3. Open ADR if decision is architectural / irreversible / cross-package
4. Implement quality-only changes inside unlock
5. Fill Package Health Checklist for each modified package (all PASS)
6. Document Rollback Strategy before claiming COMPLETE
7. Prove regression GREEN
8. Update Technical Debt Register + Metrics Dashboard
9. Update STATUS + CHANGELOG
10. Re-freeze touched areas
11. Stop for human approval before next ASI task
```

---

## 6. Definition of Done (enterprise)

A task may be marked **COMPLETE** only when **all** are true:

| # | Criterion |
|---|---|
| 1 | Repository integrity verified for touched surfaces |
| 2 | Architecture verified (boundaries / arch tests as applicable) |
| 3 | Package Health Checklist **PASS** for every modified package |
| 4 | ADR completed **if** a significant decision was made |
| 5 | Rollback strategy documented and reviewed |
| 6 | Documentation updated (task brief, STATUS, CHANGELOG, READMEs as needed) |
| 7 | Tests updated (additive quality only; no product behavior change) |
| 8 | CI passes (or task-scoped CI gate documented if CI phase not yet reached) |
| 9 | Technical Debt Register updated |
| 10 | Engineering Metrics Dashboard updated |
| 11 | Repository audit confirms no regressions and no feature creep |
| 12 | Touched areas **re-frozen**; unlock log closed |

**Incomplete if any row fails.**

---

## 7. Freeze Policy (ASI)

1. Feature development remains frozen for the duration of ASI.  
2. Only ASI-approved paths may be temporarily unlocked ([ASI-001 §2](ASI_001_REPOSITORY_PREPARATION.md)).  
3. Unlock requires explicit human approval naming paths + task id.  
4. Every completed ASI task must **re-freeze**, update **STATUS**, **CHANGELOG**, and **ASI progress** (dashboard).  
5. Expanding the unfreeze list requires an **ADR** + human approval.  
6. Production math packages (`valuation`, `financial`, `business_quality` engines, Research/MIE/EMI/EQI, `/api/v1`) stay logic-frozen.

---

## 8. Repository Governance Rules (updated for ASI)

| Rule | Statement |
|---|---|
| G1 | ASI changes raise **repository quality**, not vanity metrics |
| G2 | No new analytics, providers, market data, or API breaks under ASI |
| G3 | Prefer additive tests and docs over invasive refactors |
| G4 | Significant decisions → ADR before or with the change |
| G5 | No COMPLETE without rollback plan |
| G6 | Debt is registered (resolved / deferred / accepted / new) |
| G7 | Dashboard updated after every ASI task |
| G8 | Archive docs; never delete freeze history |
| G9 | GREEN = Build + Tests + Architecture + Public APIs + Determinism + Docs ([DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md)) |
| G10 | Integrity > features ([DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md)) |

---

## 9. Task Map (post–ASI-001A)

| Task | Phase | Status |
|---|---|---|
| ASI-001 | Preparation & selective unfreeze | **Complete** (assessment) |
| ASI-001A | Strengthen implementation framework | **Complete / Accepted** |
| ASI-002 | Phase 1 Repository Integrity | **Complete** |
| ASI-003 | Phase 2 Architecture Verification | **Complete** |
| ASI-004 | Phase 3 Package Governance | **Complete** |
| ASI-005 | Phase 4 Documentation Excellence | **Complete** |
| ASI-006 | Phase 5 Testing Excellence | **Complete** |
| ASI-007 | Phase 6 CI Quality | **Complete** |
| ASI-008 | Phase 7 Final Repository Audit | **Complete — ASI CLOSED** |

---

## 10. Templates & Registers

| Artifact | Path |
|---|---|
| ADR Template | [asi/ADR_TEMPLATE.md](asi/ADR_TEMPLATE.md) |
| Rollback Template | [asi/ROLLBACK_TEMPLATE.md](asi/ROLLBACK_TEMPLATE.md) |
| Package Health Checklist | [asi/PACKAGE_HEALTH_CHECKLIST.md](asi/PACKAGE_HEALTH_CHECKLIST.md) |
| Technical Debt Register | [asi/TECHNICAL_DEBT_REGISTER.md](asi/TECHNICAL_DEBT_REGISTER.md) |
| Engineering Metrics Dashboard | [asi/ENGINEERING_METRICS_DASHBOARD.md](asi/ENGINEERING_METRICS_DASHBOARD.md) |
| ASI Charter (short index) | [ASI_CHARTER.md](ASI_CHARTER.md) |

---

## 11. Approval Gate

**Do not begin ASI-002 until this framework is explicitly approved.**

Approval confirms:
1. Revised phase order (Architecture before Docs/Tests)  
2. Mandatory ADR / Rollback / Health Checklist / Debt / Dashboard  
3. Enterprise Definition of Done  
4. Unfreeze list remains as ASI-001 (no expansion)  
