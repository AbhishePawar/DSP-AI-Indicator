# DSP Changelog (Index)

| Field | Value |
|---|---|
| **Version** | `1.3.33` |
| **Status** | **Active** (Living) |
| **Last updated** | 2026-07-26 |
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
| 2026-07-26 | **1.3.33** | EPIC-003 Intelligence Workspace: `dsp-web` **2.5.0** `/intelligence` over `/api/v1` only; Vitest **14 PASS**; backend unchanged |
| 2026-07-26 | **1.3.32** | EPIC-002 `/api/v1` composition: `api_platform` **0.2.0** + `dsp_platform` **0.7.1** adapter; DTOs over `compose_intelligence`; no engine changes |
| 2026-07-26 | **1.3.31** | EPIC-001 Platform Composition Phase 1: `dsp_platform` **0.7.0** internal orchestration of FEATURE packages; `/api/v1` unchanged |
| 2026-07-26 | **1.3.30** | FEATURE-008 Investment Committee Phase 1: `investment_committee` **0.1.0** deterministic five-reviewer consensus; distinct from frozen `ai_committee`; package-only |
| 2026-07-26 | **1.3.29** | FEATURE-007 Investment Recommendation Phase 1: `investment_recommendation` **0.1.0** deterministic MoS-gated decision engine; distinct from G1.3 recommendation; package-only |
| 2026-07-26 | **1.3.28** | FEATURE-006 Business Quality Aggregator Phase 1: `business_quality_aggregator` **0.1.0** cross-domain explainable composition; distinct from F3.7 Aggregator; package-only |
| 2026-07-26 | **1.3.27** | FEATURE-005 Growth Quality Phase 1: `growth_quality` **0.1.0** six-dimension explainable engine; Buffett-aligned reinvestment focus; package-only |
| 2026-07-26 | **1.3.26** | FEATURE-004 Earnings Quality Phase 1: `earnings_quality` **0.1.0** six-dimension explainable engine; distinct from BQ F3.2 module; package-only |
| 2026-07-26 | **1.3.25** | FEATURE-003 Financial Strength Phase 1: `financial_strength` **0.1.0** six-dimension explainable engine; package-only; `/api/v1` unchanged |
| 2026-07-26 | **1.3.24** | FEATURE-002 Management Quality Phase 1: `management_quality` **0.1.0** six-dimension explainable engine; package-only; `/api/v1` unchanged |
| 2026-07-26 | **1.3.23** | FEATURE-001 Economic Moat Phase 1: `economic_moat` **0.2.0** six-dimension explainable engine; package-only; `/api/v1` unchanged |
| 2026-07-26 | **1.3.22** | REP-001 Release Engineering & Repository Cleanup: hygiene, packaging policy, sensitive-path purge; Professionalism **95/100**; no product/API change |
| 2026-07-26 | **1.3.21** | ASI-008 Final Repository Audit & ASI closure; certificate issued; Overall Health **90/100**; feature freeze remains default |
| 2026-07-26 | **1.3.20** | ASI-007 CI Quality: integrity/arch/smoke/full monorepo gates in GitHub Actions; `dev` extras for HTTP tests; `docs/CI.md`; no product code |
| 2026-07-26 | **1.3.19** | ASI-006 Testing Excellence: arch tests for `dsp`/`economic`/`fundamental`/`snapshot_bridge`; monorepo façade smoke + determinism (**25 PASS**); no product code |
| 2026-07-26 | **1.3.18** | ASI-005 Documentation Excellence: 100% package README coverage (standard 12-section card); documentation matrix; C4 stale portfolio notes; docs only |
| 2026-07-26 | **1.3.17** | ASI-004 Package Governance: thin pyprojects for 8 foundation packages; `compliance` unused dep removed; ownership matrix; no API/behaviour change |
| 2026-07-26 | **1.3.16** | ASI-003 Architecture Verification: additive `test_architecture.py` for 13 mandatory packages + cycle guard (**40 PASS**); no business logic |
| 2026-07-26 | **1.3.15** | ASI-002 Repository Integrity: register `economic_moat`; align `ai_committee`/`economic` metadata; version-truth ADRs; orphan `data-ingestion` deferred; no business logic |
| 2026-07-26 | **1.3.14** | ASI-001A enterprise Implementation Framework (ADR/rollback/health/debt/dashboard; revised phase order); docs only; no package code |
| 2026-07-25 | **1.3.13** | F3.7 Business Quality Aggregator (`business_quality` 0.7.0); **Phase 3 complete**; Phase 1–2 frozen |
| 2026-07-25 | **1.3.12** | F3.6 Business Quality Engine (`business_quality` 0.6.0); Phase 1–2 frozen |
| 2026-07-25 | **1.3.11** | F3.5 Competitive Position Indicators (`business_quality` 0.5.0); Phase 1–2 frozen |
| 2026-07-25 | **1.3.10** | F3.4 Business Characteristics Intelligence (`business_quality` 0.4.0); Phase 1–2 frozen |
| 2026-07-24 | **1.3.9** | F3.3 Capital Allocation Intelligence (`business_quality` 0.3.0); Phase 1–2 frozen |
| 2026-07-24 | **1.3.8** | F3.2 Earnings Quality Intelligence (`business_quality` 0.2.0); Phase 1–2 frozen |
| 2026-07-24 | **1.3.7** | F3.1 Business Quality Framework (`business_quality` 0.1.0); Phase 1–2 frozen |
| 2026-07-24 | **1.3.6** | F2.7 Financial Statement Aggregator (`financial` 0.7.0); Phase 2 Financial Intelligence complete; Phase 1 Valuation untouched |
| 2026-07-24 | **1.3.5** | F2.6 Trend & Time-Series Intelligence (`financial` 0.6.0); Phase 1 Valuation untouched |
| 2026-07-24 | **1.3.4** | F2.5 Financial Ratio Engine (`financial` 0.5.0); Phase 1 Valuation untouched |
| 2026-07-24 | **1.3.3** | F2.4 Cash Flow Intelligence (`financial` 0.4.0); Phase 1 Valuation untouched |
| 2026-07-24 | **1.3.2** | F2.3 Balance Sheet Intelligence (`financial` 0.3.0); Phase 1 Valuation untouched |
| 2026-07-24 | **1.3.1** | F2.2 Income Statement Intelligence (`financial` 0.2.0); Phase 1 Valuation untouched |
| 2026-07-24 | **1.3.0** | F2.1 Financial Data Domain (`financial` 0.1.0); Phase 1 Valuation untouched; Phase 2 begun |
| 2026-07-24 | **1.2.14** | V1.12 Overall Valuation Aggregator (`valuation` 0.12.0); **Phase 1 Valuation Suite COMPLETE**; suite git tag pending approval |
| 2026-07-24 | **1.2.13** | V1.11 Cross-Method Consensus (`valuation` 0.11.0); Overall Valuation still disabled; no suite git tag yet |
| 2026-07-24 | **1.2.12** | V1.10 Relative Valuation Suite (`valuation` 0.10.0); Overall Valuation still disabled; no suite git tag yet |
| 2026-07-24 | **1.2.11** | V1.9 Asset-Based & Liquidation (`valuation` 0.9.0); Overall Valuation still disabled; no suite git tag yet |
| 2026-07-24 | **1.2.10** | V1.8 Dividend Discount Model (`valuation` 0.8.0); Overall Valuation still disabled; no suite git tag yet |
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
| Backend API RC | `v1.0.0-rc1` | [VERSION_MATRIX.md](VERSION_MATRIX.md) |
| PR1 | Research Mode + PXB + VLIS frozen | Governance |
| L1.2 | Company Analysis through Saved Workspace | `L1_2_SPRINT*.md` |
| V2 | Advisor platform | `V2_SPRINT*.md` |
| M1 / M2 / EQ1 | MIE / EMI / EQI — treat certified as protected | STATUS §Protected |

---

## 4. Related

[CHANGELOG.md](CHANGELOG.md) · [DSP_STATUS.md](DSP_STATUS.md) · [DSP_ROADMAP.md](DSP_ROADMAP.md) · [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md)
