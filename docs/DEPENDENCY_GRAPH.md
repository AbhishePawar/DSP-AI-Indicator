# Dependency Graph

**Platform API RC:** **v1.0.0-rc1**  
**Freeze:** [K1.4](K1_4_PLATFORM_FREEZE.md)  
**FEATURE-001:** `economic_moat` **0.2.0** analytics enabled.  
**FEATURE-002:** `management_quality` **0.1.0** depends on `core`, `financial`, `business_quality`.  
**FEATURE-003:** `financial_strength` **0.1.0** depends on `core`, `financial`, `business_quality`.  
**FEATURE-004:** `earnings_quality` **0.1.0** depends on `core`, `financial`, `business_quality` (distinct from F3.2 module).
**FEATURE-005:** `growth_quality` **0.1.0** depends on `core`, `financial`, `business_quality`.
**FEATURE-006:** `business_quality_aggregator` **0.1.0** depends on five FEATURE domain packages (+ `core`/`financial`/`business_quality` for convenience path). Distinct from F3.7 Aggregator.
**FEATURE-007:** `investment_recommendation` **0.1.0** depends on `valuation` + five domains + aggregator. Distinct from G1.3 `recommendation`.
**FEATURE-008:** `investment_committee` **0.1.0** depends on IR + BQA + five domains + valuation. Distinct from frozen `ai_committee`.  
**EPIC-001:** `dsp_platform` **0.7.1** orchestrates FEATURE packages via public APIs only (`composition/`).  
**EPIC-002:** `api_platform` **0.2.0** exposes composition via `/api/v1` DTOs; depends only on `dsp_platform` (+ contracts/FastAPI).  
Empty `packages/data-ingestion/` remains unregistered.

---

## 1. Layered dependency rules

```text
Clients (Web / Mobile)
        │
        ▼
api_platform ──► dsp_platform, contracts, (optional) security_platform
        │
        ▼
security_platform ──► core, starlette
        │
        ▼
dsp_platform ──► orchestration + frozen façades + FEATURE public engines (EPIC-001)
        │              financial → valuation → domains → aggregator → IR → committee
        ▼
production_platform ──► core          (ops; composed at deploy edge)
        │
        ▼
compliance ──► core   (PR1.0 flags / terminology / ports; no engines)
        │
        ▼
Business packages ──► core (+ contracts where applicable)
        │
        ▼
core
```

**Forbidden:**

- Reverse imports from domains into `api_platform` / `security_platform` /
  `production_platform` internals for business logic.  
- Vendor SDKs (Redis, Prometheus, OTel, S3, Celery, …) inside
  `production_platform`.  
- Authentication imports inside `dsp_platform` domain orchestration core.  
- Application imports of `data_engine`, engines, etc. (see
  `dsp_platform.boundaries`).

---

## 2. Epic K package dependencies

| Package | Runtime deps (declared) |
|---|---|
| `production_platform` | `core` |
| `security_platform` | `core`, `starlette` |
| `api_platform` | `dsp_platform`, `contracts`, `fastapi`, `uvicorn`, `httpx` |
| `dsp_platform` | Epic K peers + FEATURE composition packages (EPIC-001; public APIs only) |
| `copilot` | `core` |
| `knowledge_graph` | `core` |
| `workflow` | `core` |
| `recommendation` | `core` |
| `compliance` | `core` |

---

## 3. Business context citation rule

Platform and Copilot **cite** immutable report references; they do not embed
upstream report payloads or re-run valuation / risk math inside API/security
layers.

```text
Recommendation / Workflow / Quant / Qualitative reports
        │  (immutable refs)
        ▼
Knowledge Graph / Copilot / DSPPlatform methods
```

---

## 4. Cycle status

Architecture boundary tests across domains enforce forbidden upstream imports.
Epic K packages do not introduce dependency cycles with business contexts.

**Status at freeze:** **PASS** (no cycles).
