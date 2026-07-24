# Dependency Graph

**Platform Release Candidate:** **v1.0.0-rc1**  
**Freeze:** [K1.4](K1_4_PLATFORM_FREEZE.md)

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
dsp_platform ──► orchestration + frozen domain public façades + core
        │
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
| `dsp_platform` | Monorepo composition (orchestration + domain façades) |
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
