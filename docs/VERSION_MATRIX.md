# Version Matrix

**Platform API / HTTP contract RC:** **`v1.0.0-rc1`** (frozen — [K1.4](K1_4_PLATFORM_FREEZE.md))  
**Freeze date (RC):** 2026-07-21  
**Historical RC regression gate:** **1538 / 1538** PASS (do not rewrite history)  
**Living monorepo regression (STATUS):** see [DSP_STATUS.md](DSP_STATUS.md) (**2299 PASS** as of ASI-002)  
**ASI integrity pass:** ASI-002 (2026-07-26)  
**ASI governance pass:** ASI-004 (2026-07-26) — thin `pyproject.toml` for former root-owned packages  
**Release engineering:** REP-001 (2026-07-26) — [RELEASE_ENGINEERING.md](RELEASE_ENGINEERING.md)  
**Feature:** FEATURE-001…008 · EPIC-001 · EPIC-002 · EPIC-003 · Docs Suite **1.3.33**

Semantic versioning: package versions below are the **authoritative living baseline**.
`pyproject.toml` `[project].version` must match package `__version__`.

Domain milestone tags (not a new HTTP RC):
`v2.0.0-financial-intelligence` · `v3.0.0-business-quality`

---

## 1. Platform release

| Artifact | Version |
|---|---|
| **DSP AI Indicator Backend API RC** | **v1.0.0-rc1** |
| Root project (`dsp-ai-indicator`) | 0.1.0 (monorepo meta) |
| Financial Intelligence milestone | `v2.0.0-financial-intelligence` |
| Business Quality milestone | `v3.0.0-business-quality` |

---

## 2. Epic K packages

| Package | Version | Phase |
|---|---|---|
| `dsp_platform` | **0.7.1** | K1.0 + EPIC-001 + EPIC-002 adapter |
| `api_platform` | **0.2.0** | K1.1 + EPIC-002 composition routes |
| `security_platform` | **0.1.0** | K1.2 |
| `production_platform` | **0.1.0** | K1.3 |

---

## 3. Frozen business / foundation packages

| Package | Version | Notes |
|---|---|---|
| `copilot` | 0.5.0 | |
| `knowledge_graph` | 0.4.0 | |
| `workflow` | 0.4.0 | |
| `recommendation` | 0.4.0 | |
| `quantitative_risk` | 0.3.0 | |
| `research` | 0.4.0 | |
| `risk` | 0.5.0 | |
| `portfolio` | 0.5.0 | |
| `comparison` | 0.2.0 | |
| `decision_intelligence` | 0.2.0 | |
| `industry` | 0.9.0 | |
| `universe` | 0.1.0 | |
| `orchestration` | 0.2.0 | |
| `contracts` | 0.3.0 | |
| `core` | 0.2.0 | |
| `data_engine` | 0.6.0 | |
| `dsp` | 0.2.0 | |
| `fundamental` | 0.1.0 | |
| `economic` | **0.1.1** | pyproject aligned ASI-002 |
| `financial` | 0.7.0 | Phase 2 frozen |
| `business_quality` | 0.7.0 | Phase 3 frozen |
| `economic_moat` | **0.2.0** | FEATURE-001 Phase 1 core analytics; [FEATURE_001_ECONOMIC_MOAT.md](FEATURE_001_ECONOMIC_MOAT.md) |
| `management_quality` | **0.1.0** | FEATURE-002 Phase 1 core analytics; [FEATURE_002_MANAGEMENT_QUALITY.md](FEATURE_002_MANAGEMENT_QUALITY.md) |
| `financial_strength` | **0.1.0** | FEATURE-003 Phase 1; [FEATURE_003_FINANCIAL_STRENGTH.md](FEATURE_003_FINANCIAL_STRENGTH.md) |
| `earnings_quality` | **0.1.0** | FEATURE-004 Phase 1; [FEATURE_004_EARNINGS_QUALITY.md](FEATURE_004_EARNINGS_QUALITY.md) |
| `growth_quality` | **0.1.0** | FEATURE-005 Phase 1; [FEATURE_005_GROWTH_QUALITY.md](FEATURE_005_GROWTH_QUALITY.md) |
| `business_quality_aggregator` | **0.1.0** | FEATURE-006 Phase 1; [FEATURE_006_BUSINESS_QUALITY_AGGREGATOR.md](FEATURE_006_BUSINESS_QUALITY_AGGREGATOR.md) |
| `investment_recommendation` | **0.1.0** | FEATURE-007 Phase 1; [FEATURE_007_INVESTMENT_RECOMMENDATION.md](FEATURE_007_INVESTMENT_RECOMMENDATION.md) |
| `investment_committee` | **0.1.0** | FEATURE-008 Phase 1; [FEATURE_008_INVESTMENT_COMMITTEE.md](FEATURE_008_INVESTMENT_COMMITTEE.md) |
| `valuation` | 0.12.0 | Phase 1 frozen |
| `ai_committee` | **0.3.0** | pyproject aligned ASI-002 |
| `snapshot_bridge` | 0.1.0 | |
| `llm_adapters` | **0.1.0** | Edge LLM adapters (EPIC-014 integrity) |
| `compliance` | **0.1.0** | PR1.0 — flags / terminology / ports; unused `core` dep removed ASI-004 |

### Intentionally unregistered (orphan scaffold)

| Path | Status |
|---|---|
| `packages/data-ingestion/` | Empty scaffold (`data_ingestion` stubs only). **Not** registered. See ADR-ASI-002-002. |

---

## 4. HTTP / API versioning

| Surface | Version |
|---|---|
| HTTP API | **v1** (`/api/v1`, `X-API-Version`) |
| OpenAPI `info.version` | 0.2.0 (`api_platform`) |

---

## 5. Compatibility policy

- **RC → GA (`v1.0.0`):** documentation / adapter / bugfix only unless
  freeze amendment.  
- **Clients:** pin against RC tag; treat public façades in
  [PUBLIC_API_REFERENCE.md](PUBLIC_API_REFERENCE.md) as the contract.  
- **Providers:** swap via ports without bumping domain package majors.
- **Domain milestones** after RC do **not** change `/api/v1` unless a new API RC is declared.
