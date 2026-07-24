# DSP Architecture

| Field | Value |
|---|---|
| **Version** | `1.1.0` |
| **Status** | **Stable** |
| **Last updated** | 2026-07-23 |
| **Audience** | Architects · engineers · AI agents |

## Purpose

**Canonical** system structure and **dependency rules**. Deep freeze matrices stay in [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) and [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md) — summarized here, not copied.

---

## 1. System overview

Layered investment research platform: ingest → modular engines → cite evidence → `/api/v1` → thin clients.

```text
Clients (web / future mobile)
        ↓
api_platform (+ security_platform)
        ↓
dsp_platform (composition root / façade)
        ↓
Orchestration + domain engines
        ↓
contracts / core / data_engine
```

`dsp_platform` remains **independent of authentication**. Security wraps HTTP, not domain.

---

## 2. Styles (mandatory)

Clean Architecture · DDD bounded contexts · Modular engines · Evidence-first · Hexagonal ports.

---

## 3. Ownership rules

1. Exactly one owner package per durable artifact.  
2. Consumers **cite** (ids/digests/refs) — never re-home aggregates.  
3. UI never owns scoring / valuation / recommendation math.  
4. `api_platform` / `security_platform` / `production_platform` orchestrate — do not recalculate finance.  
5. `compliance` owns mode policy & terminology ports — not investment math.

Full matrix → baseline §2.

---

## 4. Qualitative stack (dependency direction)

```text
contracts / core / data_engine
  → analysis engines (fundamental, economic, valuation, dsp, …)
  → decision_intelligence
  → industry / comparison
  → portfolio / risk
  → research
  → recommendation / workflow / knowledge_graph / copilot  (additive)
```

Nothing may depend **upward** against this order.

---

## 5. Dependency rules (canonical)

### 5.1 Allowed

| From | May depend on |
|---|---|
| Domain package | `contracts`, `core`, **lower** stack packages via **public façades** |
| `dsp_platform` | Domain façades (composition only) |
| `api_platform` | `dsp_platform` / security integration patterns as designed |
| `apps/web` | `/api/v1` clients · local view-models · UI libs |
| Adapters | Ports they implement + vendor SDKs **at the edge** |

### 5.2 Forbidden

| Forbidden | Why |
|---|---|
| Domain → `apps/web` | UI must not own domain |
| Domain → `api_platform` / `security_platform` | Edge depends on domain, not reverse |
| Domain → `dsp_platform` | Façade is composition root; domains must not import it |
| Web → Python package internals | Thin client; HTTP only |
| Web investment math / scoring engines | Violates thin client + single ownership |
| Deep imports of another package’s private modules | Breaks modularity |
| Embedding upstream aggregates | Cite, don’t own |

### 5.3 Circular dependency policy

- **Circular imports between packages are forbidden.**  
- If a cycle appears: extract shared types to `contracts`, or invert via a port, or split the package.  
- Do not “break” cycles by moving logic into the web client.  
- Detected cycles → STOP → ADR ([DSP_DECISION_RECORDS.md](DSP_DECISION_RECORDS.md)).

---

## 6. Client architecture (`apps/web`)

| Allowed | Forbidden |
|---|---|
| Envelope → view-model mapping | DCF / MOS / domain scoring in browser |
| Research Mode label remaps | Fabricated Street consensus |
| Labeled localStorage UX | Claiming cloud sync |
| Presentation builders | New Decision Engine in TS |

Governance → [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md).

---

## 7. API

| Item | Value |
|---|---|
| HTTP | `/api/v1` |
| Backend RC | `v1.0.0-rc1` → [VERSION_MATRIX.md](VERSION_MATRIX.md) |
| Contract | [PUBLIC_API_REFERENCE.md](PUBLIC_API_REFERENCE.md) |

Breaking changes require new RC / major epic — not a UI sprint.

---

## 8. Extension & scale (1M+ LOC)

- New capability = new adapter/package against existing ports.  
- Package boundary = primary modularity unit.  
- Docs stay indexed (`DSP_*`) so AI loads slices.  
- Prefer additive packages over god-modules.

---

## 9. Related

[DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) · [DSP_STATUS.md](DSP_STATUS.md) · [DSP_FOLDER_STRUCTURE.md](DSP_FOLDER_STRUCTURE.md) · [DSP_DECISION_RECORDS.md](DSP_DECISION_RECORDS.md)  
Historical essay (prefer this file + baseline): [DSP_AI_INDICATOR_ARCHITECTURE.md](DSP_AI_INDICATOR_ARCHITECTURE.md) — treat as **Historical**; do not default-load.
