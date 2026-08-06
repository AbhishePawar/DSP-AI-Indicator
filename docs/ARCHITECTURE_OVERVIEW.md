# Architecture Overview

**Platform Release Candidate:** **v1.0.0-rc1**  
**Freeze:** [K1.4 Platform Freeze](K1_4_PLATFORM_FREEZE.md)  
**Baseline:** [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md)

---

## 1. System stack

```text
┌─────────────────────────────────────────┐
│  Website  ·  Mobile App                 │  Phase L (clients)
└──────────────────┬──────────────────────┘
                   │ HTTPS
┌──────────────────▼──────────────────────┐
│  REST API          api_platform 0.1.0   │
│  (+ OpenAPI / Swagger)                  │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  Authentication    security_platform    │
│  JWT · API keys · RBAC · rate limit     │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  API Platform / DSP Platform            │
│  dsp_platform 0.6.0  (orchestration)    │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  Production Services                    │
│  production_platform 0.1.0 (ports)      │
└──────────────────┬──────────────────────┘
                   │ cite / façade only
┌──────────────────▼──────────────────────┐
│  AI Copilot · Knowledge Graph · Workflow│
│  Recommendation · Quant · Qualitative   │
│  Foundation (core, contracts, data…)    │
└─────────────────────────────────────────┘
```

---

## 2. Bounded contexts (business)

| Context | Package | Role |
|---|---|---|
| Foundation | `core`, `contracts`, `data_engine`, … | Shared primitives / data |
| Qualitative | `fundamental`, `economic`, `valuation`, `ai_committee`, `decision_intelligence`, `industry`, `comparison`, `portfolio`, `risk`, `research`, … | Analysis & qualitative intelligence |
| Quantitative Risk | `quantitative_risk` | Additive risk metrics |
| Recommendation | `recommendation` | Cite-backed recommendation reports |
| Workflow | `workflow` | Execution orchestration |
| Knowledge Graph | `knowledge_graph` | Relationship / lineage index |
| AI Copilot | `copilot` | Conversation / explanation |
| **Compliance (PR1.0)** | `compliance` | Feature flags, Research/SEBI terminology, disclosure & consensus **ports** |

Business contexts **own** their reports and engines. Platform layers
**orchestrate** and **present**; they do not recalculate finance.
Compliance owns **product mode policy and presentation vocabulary**, not
investment math.


**RC1 Milestone 11 — Super Admin Control Center (final RC1 feature):** Platform
Operating System via `/api/v1/admin/*` control-center routes and
`/control-center`. Central Configuration Registry with versioning/rollback,
branding/CMS/flags/AI/valuation/risk/market overlays, business rules, and
façades over Admin/SaaS/Ops. See
[SUPER_ADMIN_CONTROL_CENTER.md](SUPER_ADMIN_CONTROL_CENTER.md).

---

## 3. Platform layers (Epic K)

| Layer | Package | Owns |
|---|---|---|
| Integration | `dsp_platform` | `DSPPlatform`, registry, lifecycle, channel methods |
| HTTP | `api_platform` | FastAPI routes, schemas, DI |
| Security | `security_platform` | AuthN/Z, JWT, API keys, RBAC, audit |
| Production | `production_platform` | Logging/metrics/tracing/cache/storage/scheduler ports |

**Critical rule:** `dsp_platform` remains **independent of authentication**.
Security wraps the API, not the domain façade.

---

## 4. Extension points (frozen pattern)

| Concern | Extension |
|---|---|
| LLM providers | `LanguageModelPort` adapters |
| Observability | `MetricsPort` / `TracingPort` / `LoggingPort` adapters |
| Cache / object store | `CachePort` / `StoragePort` adapters |
| Jobs | `SchedulerPort` adapters |
| Identity | Durable `UserStore` / IdP via `OAuth2TokenValidator` |
| Clients | Web (L1.0) / Mobile over versioned REST `/api/v1` |

---

## 5. Non-goals of the frozen backend

No first-party web UI · no mobile app · no deploy manifests · no vendor SDKs
inside production/security cores · no business logic in API/security/production
packages.
