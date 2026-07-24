# DSP Status

| Field | Value |
|---|---|
| **Version** | `1.2.2` |
| **Status** | **Active** (Living) |
| **Last updated** | 2026-07-23 |
| **Audience** | Anyone starting work today |
| **AI load** | **P2 — always with Master Protocol** |

## Purpose

**Canonical** point-in-time truth: Project Health, protected modules, freeze surfaces.  
Protection **policy** (Git, backup, recovery, approvals) → [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md).  
Do not duplicate architecture or roadmap here.

---

## 0. Project Health (mandatory dashboard)

| Field | Value |
|---|---|
| **Current Version** | Backend RC **`v1.0.0-rc1`** · Web **`2.4.0`** · VIE **`0.2.0-discounted-cash-flow`** · Docs Suite **`1.2.2`** · API **`/api/v1`** |
| **Active Sprint** | **V1.2 complete** — Discounted Cash Flow Intelligence (`apps/web/src/lib/valuation/`) · Next: V1.3 |
| **Production Modules** | Research Platform ✓ · MIE ✓ · EMI ✓ · EQI ✓ · VIE Foundation + DCF (category only; Overall Valuation disabled) — see §2–§2b |
| **Regression Status** | **GREEN** — **1551 PASS** (backend suite) · Definition → [DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md) |
| **Project Health** | **Healthy** |
| **Last Safe Checkpoint** | Recommend tag `milestone/V1.2-dcf` after user-requested commit · Prior: Docs Suite Protection Framework 2026-07-23 |

Update this table after every milestone, unlock, or recovery.

---

## 1. Platform freeze

| Item | Value |
|---|---|
| Backend RC | **`v1.0.0-rc1`** |
| HTTP API | **`/api/v1`** |
| Freeze authority | [K1_4_PLATFORM_FREEZE.md](K1_4_PLATFORM_FREEZE.md) · [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md) |
| Protection framework | [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) |

---

## 2. Protected production modules (permanent)

AI **must not modify** these unless the user **explicitly** unlocks them. Policy + unlock protocol → [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) §1–2.

| Module | Scope | Rule |
|---|---|---|
| **Research Platform** | Research intelligence packages + Research Mode / compliance surfaces | **Production** · Frozen |
| **Management Intelligence Engine (MIE / M1)** | Delivered M1 domain + certified presentation | **Production** · Frozen |
| **Economic Moat Intelligence Engine (EMI / M2)** | Moat engine + certified presentation | **Production** · Frozen |
| **Earnings Quality Intelligence Engine (EQI / EQ1)** | EQ engine + certified presentation | **Production** · Frozen |
| **Completed Web Sprints** | Closed L1.2 / V* / M* / EQ* sprint deliverables | No redesign; bugfix only with explicit task |
| **Decision / valuation / recommendation math** | Python engine cores (`packages/…`) | Epic-gated · Frozen |
| **`/api/v1` contracts** | Public HTTP | Requires RC / major bump · Breaking approval |
| **PR1.0–PR1.2 freezes** | Research Mode · PXB · VLIS | Implement within contract; do not invent a new OS |

Safety checklist → [DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md).

### 2b. Valuation Intelligence Engine (VIE) — in progress epic

| Item | Status |
|---|---|
| V1.1 Foundation | **Complete** (`0.1.0-foundation`) |
| V1.2 Discounted Cash Flow (FCFF) | **Complete** (`0.2.0-discounted-cash-flow`) — category scoring only |
| Overall Valuation | **DISABLED** (`overallValuationEnabled=false`) |
| Location | `apps/web/src/lib/valuation/` (V1 epic web module; independent of MIE/EMI/EQI) |
| Sprint brief | [V1_SPRINT2_DCF.md](V1_SPRINT2_DCF.md) |

VIE is **not** a production-certified frozen module yet. Do not enable Overall Valuation without an explicit sprint unlock.

---

## 3. Client (`apps/web`) — delivered themes

| Theme | Notes |
|---|---|
| Company Analysis workspace | Snapshot → BI → Market → Explainability → KG → Copilot → Reports → Saved Workspace |
| Thin-client mapping | `mapEnvelope` + presentation builders only |
| Trust UI | Source / category / confidence; Unavailable honesty |
| Advisor / Moat / MIE / EQ modules | Separate `apps/web/src/lib/…` trees — **protected** |
| Valuation Intelligence (VIE) | Foundation + DCF FCFF in `lib/valuation/` — Overall Valuation off |

Web SemVer ≠ backend RC.

---

## 4. Active constraints for new work

1. Declare **one** scope class (Master Protocol §5).  
2. Confirm **change approval level** (Protection §9).  
3. Run PROJECT PROTECTION RULE + AI Safety Checklist.  
4. Prefer localStorage demos over fake cloud claims.  
5. Copilot ≠ autonomous investment advice.  
6. PDF/DOCX may stay placeholder until generation epic.  
7. Portfolio broker sync is not L1.2 scope.  
8. **Do not enable Overall Valuation** until a dedicated sprint unlocks it.

---

## 5. Known limitations

Canonical lists live in epic files — do not expand here:

- [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)  
- `*_KNOWN_LIMITATIONS.md`, `L1_2_*`, `EQ1_*`, `M1_*`, `M2_*`, [V1_SPRINT2_DCF.md](V1_SPRINT2_DCF.md)

---

## 6. Related

[DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) · [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) · [DSP_ROADMAP.md](DSP_ROADMAP.md) · [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) · [VERSION_MATRIX.md](VERSION_MATRIX.md)
