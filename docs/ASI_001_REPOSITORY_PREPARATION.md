# ASI-001 — Repository Preparation & Selective Unfreeze

| Field | Value |
|---|---|
| **Initiative** | Architecture Stabilization Initiative (ASI) |
| **Task** | ASI-001 |
| **Status** | **Complete** (assessment only) |
| **Date** | 2026-07-26 |
| **Code changes** | **None** |
| **Superseded workflow** | Phase order revised by [ASI-001A](ASI_IMPLEMENTATION_FRAMEWORK.md) |

## Purpose

Record the approved freeze assessment, selective unfreeze list, risks, and readiness gate before any ASI implementation.

Full enterprise operating system → [ASI_IMPLEMENTATION_FRAMEWORK.md](ASI_IMPLEMENTATION_FRAMEWORK.md).

---

## 1. Repository Freeze Assessment

### Freeze authority

| Source | Role |
|---|---|
| [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) | Permanent protection; unlock protocol |
| [DSP_STATUS.md](DSP_STATUS.md) | Living health + FROZEN Phase 1–3 |
| Epic freeze docs | Domain public surfaces frozen |
| [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md) | No mid-stream redesign; thin client |
| Sprint DO NOT MODIFY lists | Hard blocks on certified engines / `/api/v1` |

### Freeze posture

- Feature development: **frozen**
- Production-certified engines: **frozen by default**
- Phase 3 `business_quality` 0.7.0: **feature-frozen** (milestone `v3.0.0-business-quality`)
- Early architecture themes still valid: CI narrowness, README gaps, uneven architecture tests, registry/doc drift

---

## 2. Recommended Unfreeze List (do not expand without amendment)

| Path | Reason | Re-freeze? |
|---|---|---|
| `docs/DSP_STATUS.md` | ASI unlocks, health, checkpoints | Living |
| `docs/DSP_CHANGELOG.md` / `docs/VERSION_MATRIX.md` | Version truth | Living |
| `docs/ASI_*.md` / `docs/asi/**` | ASI governance | Keep |
| `README.md` (root) | Orientation accuracy | Living |
| `packages/*/README.md` (missing/outdated only) | Doc excellence | Yes |
| `.github/workflows/ci.yml` | Monorepo CI fidelity | Yes after CI phase |
| Root / package `pyproject.toml` (metadata only) | Registration / governance | Yes |
| `packages/*/tests/test_architecture.py` (**additive**) | Architecture verification | Yes |
| `packages/*/tests/**` (quality-only) | Testing excellence | Yes |
| `Makefile` / lint configs (if present) | Local/CI parity | Yes |
| `packages/economic_moat/**` (scaffolding quality only; **no F4 analytics**) | Hygiene | Yes |
| `docs/DEPENDENCY_GRAPH.md` | Dependency accuracy | Living |

### Remain frozen

`valuation` · `financial` · `business_quality` domain engines · Research/MIE/EMI/EQI cores · Decision/recommendation/risk/portfolio **logic** · Copilot/workflow/KG **engines** · Web VIE features · `/api/v1` · new analytics

**Unlock rule:** frozen packages may receive README / additive tests / metadata / architecture guards only — never new ratios, scores, providers, or API shapes.

---

## 3. Risks

| Risk | Level | Mitigation |
|---|---|---|
| Silent feature work under “quality” | High | Hard ban list; DoD + ADR |
| CI expansion breaks main | Medium | Staged CI; branch first |
| Arch tests couple to internals | Medium | Public façade + import rules only |
| Doc churn erases freeze history | Medium | Archive, never delete |
| Unlock creep into valuation/financial | High | Keep logic out of unfreeze list |
| Version matrix drift | Medium | Integrity phase first |

**Overall scoped ASI risk:** Medium, controllable.

---

## 4. Readiness

| Gate | Result |
|---|---|
| Freeze map understood | Pass |
| Selective unfreeze drafted | Pass |
| Code changes in ASI-001 | None |

**Next:** Approve unfreeze list, then run ASI under [ASI_IMPLEMENTATION_FRAMEWORK.md](ASI_IMPLEMENTATION_FRAMEWORK.md) (phase order revised by ASI-001A).
