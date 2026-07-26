# Package Testing Matrix

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | Living |
| **Last updated** | 2026-07-26 |
| **Authority** | ASI-006 Testing Excellence |

Permanent testing index for `packages/*`. Update after testing ASI tasks.

| Package | Unit | Smoke | API | Architecture | Regression | Status |
|---|---|---|---|---|---|---|
| `ai_committee` | Yes | Via monorepo | Yes (`test_public_api`) | Yes | Yes | Strong |
| `api_platform` | Yes | Via monorepo + composition suite | Yes (`test_api` + composition) | Yes | Yes | Strong (EPIC-002) |
| `business_quality` | Yes | Via monorepo | Façade spot-check | Yes | Yes | Strong |
| `comparison` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `compliance` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `contracts` | Yes | Via monorepo | Façade spot-check | Yes | Yes | Strong |
| `copilot` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `core` | Yes | Via monorepo | Façade spot-check | Yes | Yes | Strong |
| `data_engine` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Strong |
| `decision_intelligence` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `dsp` | Yes | Via monorepo | Yes (`test_public_api`) | Yes (ASI-006) | Yes | Strong |
| `dsp_platform` | Yes | **Monorepo smoke** + composition suite | Façade + `compose_intelligence` | Yes + cycles | Yes | Strong (EPIC-001/002) |
| `economic` | Yes | Via monorepo | Yes (`test_public_api`) | Yes (ASI-006) | Yes | Strong |
| `economic_moat` | Yes | Package suite (32) + monorepo | Engine + scoring + arch | Yes | Yes | Good (FEATURE-001) |
| `management_quality` | Yes | Package suite (22) + monorepo | Engine + scoring + arch | Yes | Yes | Good (FEATURE-002) |
| `financial_strength` | Yes | Package suite (22) + monorepo | Engine + scoring + arch | Yes | Yes | Good (FEATURE-003) |
| `earnings_quality` | Yes | Package suite (23) + monorepo | Engine + scoring + arch | Yes | Yes | Good (FEATURE-004) |
| `growth_quality` | Yes | Package suite (23) + monorepo | Engine + scoring + arch | Yes | Yes | Good (FEATURE-005) |
| `business_quality_aggregator` | Yes | Package suite (31) + monorepo | Engine + conflicts + arch | Yes | Yes | Good (FEATURE-006) |
| `investment_recommendation` | Yes | Package suite (33) + monorepo | Engine + rules + arch | Yes | Yes | Good (FEATURE-007) |
| `investment_committee` | Yes | Package suite (15) + monorepo | Reviewers + consensus + arch | Yes | Yes | Good (FEATURE-008) |
| `financial` | Yes | Via monorepo | Façade spot-check | Yes | Yes | Strong |
| `fundamental` | Yes | Via monorepo | Yes (`test_public_api`) | Yes (ASI-006) | Yes | Strong |
| `industry` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `knowledge_graph` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `orchestration` | Yes | Via monorepo | Façade spot-check | Yes | Yes | Strong |
| `portfolio` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `production_platform` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `quantitative_risk` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `recommendation` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `research` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `risk` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `security_platform` | Yes | Via monorepo | Via arch / security tests | Yes | Yes | Good |
| `snapshot_bridge` | Yes | Via monorepo | Via arch `__all__` | Yes (ASI-006) | Yes | Good |
| `universe` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `valuation` | Yes | Via monorepo | Yes (`test_public_api`) | Yes | Yes | Strong |
| `workflow` | Yes | Via monorepo | Via arch `__all__` | Yes | Yes | Good |
| `data-ingestion` | No | N/A | N/A | N/A | Orphan excluded | Orphan |

**Registered packages with tests:** **30 / 30**  
**Registered packages with architecture tests:** **30 / 30**  
**Monorepo smoke:** `packages/dsp_platform/tests/test_asi_monorepo_smoke.py`

## Related

[ASI_006_TESTING_EXCELLENCE.md](ASI_006_TESTING_EXCELLENCE.md) · [asi/ENGINEERING_METRICS_DASHBOARD.md](asi/ENGINEERING_METRICS_DASHBOARD.md)
