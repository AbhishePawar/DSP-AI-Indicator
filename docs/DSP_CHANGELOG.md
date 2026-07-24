# DSP Changelog (Index)

| Field | Value |
|---|---|
| **Version** | `1.2.9` |
| **Status** | **Active** (Living) |
| **Last updated** | 2026-07-24 |
| **Audience** | Release managers · AI orientation |

## Purpose

**Canonical index** of suite + cross-epic pointers. Full sprint bullets → [CHANGELOG.md](CHANGELOG.md) / epic changelogs. Versioning rules → [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) §8.

---

## 1. How to record a change

1. Detail in [CHANGELOG.md](CHANGELOG.md) or epic changelog.  
2. One-line pointer in §3 if freeze/architecture-facing.  
3. Flip [DSP_STATUS.md](DSP_STATUS.md) / [DSP_ROADMAP.md](DSP_ROADMAP.md) when epic status changes.  
4. Refresh STATUS **Project Health** (checkpoint, regression, health).  
5. Obsolete long specs → move to [archive/](archive/), do not delete.

---

## 2. Documentation suite

| Date | Suite | Change |
|---|---|---|
| 2026-07-24 | **1.2.9** | V1.7 Graham Intrinsic Value (`valuation` 0.7.0); original + modern heuristics; Overall Valuation still disabled |
| 2026-07-24 | **1.2.8** | V1.6 Earnings Power Value (`valuation` 0.6.0); Core-integrated; Overall Valuation still disabled |
| 2026-07-24 | **1.2.7** | V1.5 Valuation Core Framework (`valuation` 0.5.0); shared engines only; no method math change |
| 2026-07-24 | **1.2.6** | V1.4 Residual Income best-practice enhancement (`valuation` 0.4.1); 100% RIV coverage |
| 2026-07-24 | **1.2.5** | V1.4 Residual Income Valuation (`valuation` 0.4.0); STATUS regression 1626 PASS |
| 2026-07-24 | **1.2.4** | V1.3 Reverse DCF Intelligence (`valuation` 0.3.0); STATUS regression 1595 PASS |
| 2026-07-24 | **1.2.3** | V1.2 Domain DCF Intelligence in `packages/valuation` 0.2.0; STATUS regression 1561 PASS |
| 2026-07-23 | **1.2.1** | PROJECT PROTECTION RULE (pre-sprint gate; integrity > features) in Protection §0 · Master · AI Collaboration · ADR-0020 |
| 2026-07-23 | 1.2.0 | Permanent [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md); STATUS Project Health dashboard; ADRs 0017–0019; Master/AI Collaboration wired to protection |
| 2026-07-23 | 1.1.0 | Load order P1–P5 · context priority · protected modules · scope classes · dependency rules · AI safety checklist · GREEN · versioning · lifecycle · archive · token rules |
| 2026-07-23 | 1.0.0 | Introduced `docs/DSP_*.md` master suite |

### Migration notes (1.0 → 1.1)

| From (v1.0 habit) | To (v1.1) |
|---|---|
| Default load emphasized Architecture early | **P1 Protocol → P2 Status → P3 Architecture → P4 Roadmap** |
| Freeze list informal in STATUS | **Protected production modules** permanent section |
| GREEN implied as “tests pass” | **Six-dimension GREEN** in Coding Standards |
| No formal archive | **`docs/archive/`** + Historical context class |
| Topics partially duplicated across files | **Canonical source map** in Master Protocol §11 |

No application code, APIs, or engine behavior changed by this docs bump.

---

## 3. Platform highlights (pointers)

| Area | Highlight | Detail |
|---|---|---|
| Backend RC | `v1.0.0-rc1` | [VERSION_MATRIX.md](VERSION_MATRIX.md) |
| PR1 | Research Mode + PXB + VLIS frozen | Governance |
| L1.2 | Company Analysis through Saved Workspace | `L1_2_SPRINT*.md` |
| V2 | Advisor platform | `V2_SPRINT*.md` |
| M1 / M2 / EQ1 | MIE / EMI / EQI — treat certified as protected | STATUS §Protected |

---

## 4. Related

[CHANGELOG.md](CHANGELOG.md) · [DSP_STATUS.md](DSP_STATUS.md) · [DSP_ROADMAP.md](DSP_ROADMAP.md) · [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md)
