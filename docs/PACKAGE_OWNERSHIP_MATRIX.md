# Package Ownership Matrix

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | Living |
| **Last updated** | 2026-07-26 |
| **Authority** | ASI-004 Package Governance |

## Purpose

Canonical ownership and status for every package directory under `packages/`.
Governance owner for all DSP packages: **DSP AI Research** (monorepo).

Status values: **Production** · **Scaffold** · **Orphan** · **Frozen**.

---

## Matrix

| Package | Import | Purpose | Status | Governance notes |
|---|---|---|---|---|
| `ai_committee` | `ai_committee` | Multi-engine deliberation | Production · Frozen | |
| `api_platform` | `api_platform` | FastAPI HTTP surface + EPIC-002 composition | Active · 0.2.0 | Epic K + EPIC-002; DTO boundary only |
| `business_quality` | `business_quality` | Business quality intelligence | Production · Frozen | Phase 3 |
| `comparison` | `comparison` | Qualitative comparison | Production · Frozen | |
| `compliance` | `compliance` | Feature flags / terminology / ports | Production · Frozen | PR1.0 |
| `contracts` | `contracts` | Shared kernel domain models | Production · Frozen | Leaf |
| `copilot` | `copilot` | Explainability assistant | Production · Frozen | |
| `core` | `core` | Technical foundation | Production · Frozen | Leaf |
| `data_engine` | `data_engine` | Providers / normalization | Production · Frozen | |
| `decision_intelligence` | `decision_intelligence` | Decision packs / briefs | Production · Frozen | |
| `dsp` | `dsp` | Indicator engine | Production · Frozen | |
| `dsp_platform` | `dsp_platform` | Composition façade + EPIC-001 pipeline + EPIC-002 adapter | Active · 0.7.1 | Epic K + EPIC-001/002 |
| `economic` | `economic` | Macroeconomic analysis | Production · Frozen | |
| `economic_moat` | `economic_moat` | Economic Moat Intelligence Phase 1 | Active · 0.2.0 | FEATURE-001; composed via EPIC-001 |
| `management_quality` | `management_quality` | Management Quality & Capital Allocation Phase 1 | Active · 0.1.0 | FEATURE-002; composed via EPIC-001 |
| `financial_strength` | `financial_strength` | Financial Strength & Balance Sheet Quality Phase 1 | Active · 0.1.0 | FEATURE-003; composed via EPIC-001 |
| `earnings_quality` | `earnings_quality` | Earnings Quality & Predictability Phase 1 | Active · 0.1.0 | FEATURE-004; composed via EPIC-001 |
| `growth_quality` | `growth_quality` | Growth Quality & Capital Reinvestment Phase 1 | Active · 0.1.0 | FEATURE-005; composed via EPIC-001 |
| `business_quality_aggregator` | `business_quality_aggregator` | Cross-domain Business Quality Aggregator Phase 1 | Active · 0.1.0 | FEATURE-006; composed via EPIC-001 |
| `investment_recommendation` | `investment_recommendation` | Deterministic Investment Recommendation Phase 1 | Active · 0.1.0 | FEATURE-007; composed via EPIC-001 |
| `investment_committee` | `investment_committee` | Deterministic AI Committee Consensus Phase 1 | Active · 0.1.0 | FEATURE-008; composed via EPIC-001 |
| `financial` | `financial` | Financial statement intelligence | Production · Frozen | Phase 2 |
| `fundamental` | `fundamental` | Company analysis | Production · Frozen | |
| `industry` | `industry` | Industry context | Production · Frozen | |
| `knowledge_graph` | `knowledge_graph` | Knowledge graph assembly | Production · Frozen | |
| `orchestration` | `orchestration` | Analysis pipeline (flow only) | Production · Frozen | |
| `portfolio` | `portfolio` | Portfolio intelligence | Production · Frozen | |
| `production_platform` | `production_platform` | Ops ports | Production · Frozen | Epic K |
| `quantitative_risk` | `quantitative_risk` | Quantitative risk | Production · Frozen | |
| `recommendation` | `recommendation` | Recommendation domain | Production · Frozen | |
| `research` | `research` | Research assembly | Production · Frozen | |
| `risk` | `risk` | Risk profiles | Production · Frozen | |
| `security_platform` | `security_platform` | Auth / RBAC | Production · Frozen | Epic K |
| `snapshot_bridge` | `snapshot_bridge` | Contracts → engine snapshots | Production · Frozen | |
| `universe` | `universe` | Universe selection | Production · Frozen | |
| `valuation` | `valuation` | Valuation engines | Production · Frozen | Phase 1 |
| `workflow` | `workflow` | Workflow domain | Production · Frozen | |
| `llm_adapters` | `llm_adapters` | External LLM provider adapters (copilot edge) | Active · 0.1.0 | Outside frozen copilot; no engine override |
| `data-ingestion` | `data_ingestion` | Empty stubs | **Orphan** | Unregistered — ADR-ASI-002-002 |

---

## Related

[PACKAGE_GOVERNANCE.md](PACKAGE_GOVERNANCE.md) · [VERSION_MATRIX.md](VERSION_MATRIX.md) · [ASI_004_PACKAGE_GOVERNANCE.md](ASI_004_PACKAGE_GOVERNANCE.md)
