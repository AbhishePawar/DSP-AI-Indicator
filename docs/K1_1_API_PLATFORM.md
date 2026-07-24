# Phase K1.1 — API Platform

**Status:** Implemented · HTTP transport only · No business logic  

**Package:** `packages/api_platform/` **0.1.0**  
**Depends on:** `dsp_platform` **0.6.0** (K1.0) · `contracts` · FastAPI  
**Suite gate:** Regression suite green at implementation

This phase exposes the DSP Platform through stable HTTP APIs. The API layer
validates requests/responses, performs dependency injection, and delegates to
``DSPPlatform`` public methods. It does **not** calculate, recommend, value,
implement workflows, persist durably, or authenticate.

---

## 1. Architecture

```text
HTTP Client
    │
    ▼
api_platform (FastAPI)     ← schemas · routers · middleware · DI
    │
    ▼
DSPPlatform (0.6.0)        ← orchestration only
    │
    ▼
Frozen bounded contexts
```

| Layer | Responsibility |
|---|---|
| Routers | Map HTTP ↔ schemas; call platform methods |
| Schemas | Pydantic request/response validation |
| Dependencies | Inject `DSPPlatform`, ephemeral stores |
| Middleware | Request id · API version headers |
| Exceptions | Map `ApiError` / `PlatformError` → HTTP |

---

## 2. Routing

| Method | Path | Handler |
|---|---|---|
| GET | `/health` | Platform health envelope |
| GET | `/platform` | Platform metadata / capabilities |
| POST | `/analyze/company` | `DSPPlatform.analyze_company` |
| POST | `/compare` | Pack validation / orchestration envelope |
| POST | `/workflow/run` | `DSPPlatform.run_workflow` (context_ref) |
| POST | `/copilot/chat` | `DSPPlatform.ask_copilot` (context_ref) |
| GET | `/report/{id}` | Ephemeral report registry + `export_report` |

Versioned aliases are mounted under `/api/v1/*` with identical handlers.

OpenAPI: `/openapi.json` · Swagger UI: `/docs` · ReDoc: `/redoc`

---

## 3. Versioning

| Surface | Value |
|---|---|
| Package | `api_platform` **0.1.0** |
| HTTP API | **v1** (`X-API-Version` response header) |
| OpenAPI `info.version` | `0.1.0` |

Additive route / schema fields only within v1. Breaking changes require a
new API version prefix.

---

## 4. Schemas

Transport models in `api/schemas.py`:

- `AnalyzeCompanyRequest` · `CompareRequest` · `WorkflowRunRequest` ·
  `CopilotChatRequest`
- `ApiResponse` · `ApiErrorBody` · `HealthResponse` · `PlatformInfoResponse` ·
  `ReportResponse`

Schemas are JSON-facing only — they never embed business engines.

---

## 5. Error handling

| Error | HTTP |
|---|---|
| `RequestValidationError` / Pydantic | 422 |
| `ApiValidationError` | 422 |
| `ApiNotFoundError` | 404 |
| `PlatformError` | 502 |
| Unhandled | 500 |

Bodies use `ApiErrorBody` (`ok=false`, `error`, `detail`, `api_version`).

---

## 6. OpenAPI

Generated automatically by FastAPI from route signatures and response models.
Swagger UI is enabled at `/docs`.

---

## 7. Dependency injection

`ApiState` on `app.state.api` holds:

- `platform: DSPPlatform`
- `reports: ReportStore` (process-local, non-durable)
- `contexts: ContextStore` (opaque workflow / copilot handles)
- `api_version`

`create_app(platform=...)` injects a test or production platform. Default
factory builds a ready platform shell with
`require_analysis_service=False` for boot without provider secrets.

---

## 8. Extension strategy

| Next | Pattern |
|---|---|
| **K1.2 Authentication** | **DONE** · see [K1.2](K1_2_AUTHENTICATION_SECURITY.md) |
| Rate limiting | Middleware |
| Durable report store | External adapter; keep API registry optional |
| Compare engine wiring | Compose `QualitativeComparisonEngine` into platform |
| Streaming / SSE | Transport adapters over Copilot envelopes |

**Forbidden:** business calculations, recommendation / valuation / workflow
implementation inside `api_platform`, durable auth stores in this phase.

---

## 9. Non-goals (this phase)

No business calculations · no recommendation logic · no valuation · no
workflow implementation · no durable persistence · no authentication.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | K1.1 API Platform |
| [K1_0_PLATFORM_INTEGRATION.md](K1_0_PLATFORM_INTEGRATION.md) | Platform integration |
| [J1_4_AI_COPILOT_VALIDATION_FREEZE.md](J1_4_AI_COPILOT_VALIDATION_FREEZE.md) | Copilot freeze |

---

## Final question

Is the API Platform complete, stable, and ready for authentication (K1.2)?

Answered in the phase RETURN.
