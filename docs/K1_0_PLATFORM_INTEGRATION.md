# Phase K1.0 — DSP Platform Integration

**Status:** Implemented · Orchestration only · No business logic  

**Package:** `packages/dsp_platform/` **0.6.0**  
**Prerequisite:** AI Copilot J1.4 frozen · Knowledge Graph I1.4 · Workflow H1.4 ·
Recommendation G1.4 · Quantitative / Qualitative stacks frozen  
**Suite gate:** Regression suite green at implementation

This phase adds the **platform integration layer** — a single public entry
point that registers and orchestrates frozen bounded-context façades without
owning financial analysis, valuation, recommendation logic, workflow
implementation, persistence, REST, authentication, or frontend concerns.

---

## 1. Platform architecture

```text
Application
        │
        ▼
   DSPPlatform  (packages/dsp_platform — K1.0)
        │
        ├── analyze_company / analyze / analyze_decision_pack
        ├── compare_companies / compare_universe
        ├── run_workflow
        ├── build_knowledge_graph
        ├── ask_copilot
        ├── export_report
        ├── get_platform_info
        └── health_check
                │
                ▼
   Frozen public APIs only
   (Foundation · Qualitative · Quant · Recommendation ·
    Workflow · Knowledge Graph · AI Copilot)
```

**Composition helpers:** `PlatformBuilder` · `ServiceRegistry` ·
`PlatformConfiguration` · `PlatformLifecycle`

**Result envelope:** `PlatformResult` + immutable `PlatformMetadata`

---

## 2. Service registry

`ServiceRegistry` registers named façade instances with capability labels:

| Concern | Behavior |
|---|---|
| Registration | `register(name, service, capability=, version=)` |
| Lookup | `get` / `get_descriptor` / `get_by_capability` |
| Discovery | `list_services` / `list_capabilities` |
| Validation | Rejects empty names, `None` services, duplicate names |

Default wiring registers `analysis_service` under capability
`analyze_company`. Workflow / KG / Copilot engines are resolved lazily and
cached in the registry on first use.

---

## 3. Lifecycle

`PlatformStatus`: `created` → `initializing` → `ready` ↔ `degraded` →
`stopping` → `stopped` (plus `failed`).

`PlatformLifecycle` enforces legal transitions and exposes
`ensure_ready` / `ensure_operational`. `PlatformBuilder.build()` initializes
and marks **READY** by default.

---

## 4. Dependency graph

```text
dsp_platform ──orchestrates──► frozen public façades
dsp_platform ──depends──► core (+ composition deps already used by façade)
bounded contexts ──✕──► dsp_platform   (no reverse imports)
```

Platform methods only invoke public package APIs (`orchestration`,
`comparison`, `workflow`, `knowledge_graph`, `copilot`, …). No deep imports of
internal engine modules beyond each package’s public façade. No provider SDKs
and no business calculations inside K1.0 modules.

---

## 5. Public API

### Entry point

`DSPPlatform` · `PlatformBuilder` · `DSPPlatform.from_config` ·
`DSPPlatform.builder`

### Configuration / registry / lifecycle

`PlatformConfiguration` · `DEFAULT_CAPABILITIES` · `ServiceRegistry` ·
`ServiceDescriptor` · `PlatformLifecycle` · `PlatformStatus`

### Results / metadata

`PlatformResult` · `PlatformMetadata`

### Exceptions

`PlatformError` · `PlatformConfigurationError` · `ServiceRegistryError` ·
`PlatformLifecycleError`

### Orchestration methods

| Method | Delegates to |
|---|---|
| `analyze_company` | Orchestration / Decision Pack public APIs |
| `compare_companies` | `QualitativeComparisonEngine.compare_packs` |
| `run_workflow` | `WorkflowEngine.run` |
| `build_knowledge_graph` | `KnowledgeGraphAssembler` + `KnowledgeGraphEngine` |
| `ask_copilot` | Conversation → Explanation → `CopilotReporter` |
| `export_report` | Immutable envelope (presentation metadata only) |
| `get_platform_info` | `PlatformMetadata` |
| `health_check` | `PlatformHealthService` (offline) |

Legacy methods retained: `analyze`, `analyze_decision_pack`,
`analyze_universe`, `compare_universe`, `make_request`.

Version: **`0.6.0`**.

---

## 6. Configuration

`PlatformConfiguration` wraps provider / cache / timeout / feature / secret
settings (compatible with legacy `PlatformConfig`) and adds:

- `enabled_capabilities` — capability allow-list  
- `platform_name` — descriptive identity  
- `require_analysis_service` — builder validation  

Projection: `to_platform_config()` / `from_platform_config()`.

---

## 7. Validation

Validated by unit tests and architecture constraints:

- Service registration / duplicate rejection  
- Capability allow-list consistency  
- Lifecycle transitions  
- Health status envelope  
- Immutable metadata / `PlatformResult`  
- Legacy façade regression (`analyze` DI path)  

---

## 8. Extension strategy

Additive only for API / auth layers and later:

| Extension | Pattern |
|---|---|
| **K1.1 API Platform** | **DONE** · see [K1.1](K1_1_API_PLATFORM.md) |
| **K1.2 Authentication** | Gateway / middleware outside platform core |
| GraphQL | Channel adapters over `DSPPlatform` methods |
| Persistence | Adapters; platform remains stateless orchestration |
| Streaming / voice | Transport adapters over Copilot / report envelopes |
| New capabilities | Additive capability strings + registry entries |

**Forbidden:** embedding business engines inside `dsp_platform`; reverse
imports from domains into platform internals; persistence / auth / UI in
K1.0 modules.

---

## 9. Non-goals (this phase)

No financial calculations · no recommendation logic · no valuation · no
workflow implementation · no persistence · no REST API · no authentication ·
no frontend.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | K1.0 Platform Integration |
| [J1_4_AI_COPILOT_VALIDATION_FREEZE.md](J1_4_AI_COPILOT_VALIDATION_FREEZE.md) | Copilot freeze |
| [I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md](I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md) | KG freeze |
| [H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md) | Workflow freeze |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline |

---

## Final question

Is the DSP Platform integration complete, stable, and ready for API Platform
development (K1.1)?

Answered in the phase RETURN.
