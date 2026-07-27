# Public API Reference

**Platform Release Candidate:** **v1.0.0-rc1**  
**Freeze:** [K1.4](K1_4_PLATFORM_FREEZE.md)

This document inventories **stable public entry points** for application and
channel developers. Prefer package top-level imports. Breaking removals require
a freeze amendment.

---

## 1. DSP Platform (`dsp_platform` 0.7.1)

```python
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
```

| API | Purpose |
|---|---|
| `DSPPlatform.from_config` / `builder` | Composition |
| `analyze` / `analyze_decision_pack` / `analyze_universe` | Legacy analysis |
| `analyze_company` | Orchestrated company analysis → `PlatformResult` |
| `compare_companies` / `compare_universe` | Comparison orchestration |
| `run_workflow` | Workflow engine delegation |
| `build_knowledge_graph` | KG assemble/synthesize delegation |
| `ask_copilot` | Conversation → Explanation → Reporter |
| `export_report` | Presentation envelope |
| `get_platform_info` / `health_check` | Metadata / readiness |

Also re-exports frozen domain types for application convenience (see package
`__all__`). Applications should still respect import-boundary rules in
`dsp_platform.boundaries` (apps: `dsp_platform` + `contracts`).

---

## 2. API Platform (`api_platform` 0.2.0)

```python
from api_platform import create_app, app
```

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Health envelope |
| GET | `/platform` | Platform metadata |
| POST | `/analyze/company` | Company analysis |
| POST | `/compare` | Pack validation / orchestration envelope |
| POST | `/workflow/run` | Requires `context_ref` |
| POST | `/copilot/chat` | Requires `context_ref` |
| GET | `/report/{id}` | Ephemeral registry |

Versioned aliases: `/api/v1/*`  
OpenAPI: `/openapi.json` · Swagger: `/docs`

Optional: `create_app(security=SecurityBundle.create(...))`.

---

## 3. Security Platform (`security_platform` 0.1.0)

```python
from security_platform import (
    SecurityBundle, SecuritySettings, JWTManager,
    Permission, Role, SecurityMiddleware,
)
```

| API | Purpose |
|---|---|
| `SecurityBundle.create` | In-memory composition root |
| `AuthenticationManager` | JWT / API key / guest / OAuth2 port |
| `AuthorizationManager` | Permission checks |
| `JWTManager.issue` / `verify` | HS256 JWT |
| `ApiKeyManager.issue` / `verify` | Hashed API keys |
| `SecurityMiddleware` | Starlette/FastAPI protection |
| `SecurityContext` | Request principal |

**Roles:** ADMIN · ADVISOR · CLIENT · RESEARCHER · API · GUEST  
**Permissions:** AnalyzeCompany · CompareCompanies · RunWorkflow · AskCopilot ·
ViewReports · ManageUsers · ManagePlatform

---

## 4. Production Platform (`production_platform` 0.1.0)

```python
from production_platform import ProductionBundle, ProductionConfiguration
```

| API | Purpose |
|---|---|
| `ProductionBundle.create` | Ops composition with injectable ports |
| `health` / `readiness` / `liveness` | Health aggregation |
| `diagnostics` | Immutable diagnostics snapshot |
| `get_configuration` / `get_feature_flags` / `get_metrics` | Ops reads |

**Ports:** `LoggingPort` · `MetricsPort` · `TracingPort` · `CachePort` ·
`StoragePort` · `SchedulerPort` · `SecretsPort`

---

## 5. Business façades (frozen; cite via platform)

| Package | Primary entry |
|---|---|
| `copilot` | `ConversationEngine`, `ExplanationEngine`, `CopilotReporter` |
| `knowledge_graph` | Assembler / Engine / Reporter |
| `workflow` | Assembler / Engine / Reporter |
| `recommendation` | Assembler / Engine / Reporter / Mapper |
| `quantitative_risk` | Engine / Reporter |
| Qualitative stack | Per-package public `__init__` |

Channel developers should call **`dsp_platform` / `api_platform`** first;
deep domain imports are for advanced composition only.
