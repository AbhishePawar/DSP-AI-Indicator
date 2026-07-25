# DSP Status

| Field | Value |
|---|---|
| **Version** | `1.3.13` |
| **Status** | **Active** (Living) |
| **Last updated** | 2026-07-25 |
| **Audience** | Anyone starting work today |
| **AI load** | **P2 — always with Master Protocol** |

## Purpose

**Canonical** point-in-time truth: Project Health, protected modules, freeze surfaces.  
Protection **policy** → [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md).

---

## 0. Project Health (mandatory dashboard)

| Field | Value |
|---|---|
| **Current Version** | Backend RC **`v2.0.0`** · `valuation` **`0.12.0`** · `financial` **`0.7.0`** · `business_quality` **`0.7.0`** · Web **`2.4.0`** · Docs Suite **`1.3.13`** · API **`/api/v1`** |
| **Active Sprint** | **Phase 3 complete** — F3.7 Business Quality Aggregator (`business_quality` 0.7.0) |
| **Production Modules** | Research ✓ · MIE ✓ · EMI ✓ · EQI ✓ · VIE Foundation ✓ · Valuation Suite ✓ · Financial Domain ✓ |
| **Regression Status** | **GREEN** — **2299 PASS** (`--import-mode=importlib`) |
| **Project Health** | **Healthy** |
| **Last Safe Checkpoint** | `v2.0.0-financial-intelligence` — Phase 1–2 complete; **Phase 3 Business Quality complete (F3.1–F3.7)**; Phase 3 git milestone pending approval |

### 2b. Valuation Intelligence

| Item | Status |
|---|---|
| Phase 1 Valuation Suite | **COMPLETE** (`valuation` 0.12.0) — **FROZEN** |
| Overall Valuation | **ENABLED** (aggregator) |

### 2c. Financial Statement Intelligence

| Item | Status |
|---|---|
| Phase 2 | **COMPLETE** (`financial` 0.7.0) — **FROZEN** |
| Primary entry | `FinancialEngine.analyze_financials()` |
| Milestone | `v2.0.0-financial-intelligence` |

### 2d. Business Quality Intelligence

| Item | Status |
|---|---|
| F3.1 Framework | **Complete** |
| F3.2 Earnings Quality | **Complete** |
| F3.3 Capital Allocation | **Complete** |
| F3.4 Business Characteristics | **Complete** |
| F3.5 Competitive Position | **Complete** |
| F3.6 Business Quality Engine | **Complete** |
| F3.7 Business Quality Aggregator | **Complete** |
| Phase 3 | **COMPLETE** (git milestone pending approval) |
| Sprint briefs | [F3_SPRINT1](F3_SPRINT1_BUSINESS_QUALITY_FRAMEWORK.md) · [F3_SPRINT2](F3_SPRINT2_EARNINGS_QUALITY_INTELLIGENCE.md) · [F3_SPRINT3](F3_SPRINT3_CAPITAL_ALLOCATION_INTELLIGENCE.md) · [F3_SPRINT4](F3_SPRINT4_BUSINESS_CHARACTERISTICS_INTELLIGENCE.md) · [F3_SPRINT5](F3_SPRINT5_COMPETITIVE_POSITION_INDICATORS.md) · [F3_SPRINT6](F3_SPRINT6_BUSINESS_QUALITY_ENGINE.md) · [F3_SPRINT7](F3_SPRINT7_BUSINESS_QUALITY_AGGREGATOR.md) |

## Related

[DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) · [VERSION_MATRIX.md](VERSION_MATRIX.md)
