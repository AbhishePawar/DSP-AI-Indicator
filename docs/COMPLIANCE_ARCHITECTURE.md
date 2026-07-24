# Compliance Architecture

**Package:** `packages/compliance` **0.1.0**  
**Epic:** PR1.0  
**Deps:** `core` only

---

## Why a new bounded context

Product modes, disclosures, and SEBI activation are **cross-cutting product
concerns**. They must not leak into valuation / recommendation engines.

```text
Clients (flags + terminology)
        │
        ▼
compliance  (flags, terminology, ports)
        │  (does not call engines)
        ▼
presentation / future API wrappers
```

---

## Modules

| Module | Role |
|---|---|
| `feature_flags` | Research / Recommendation / SEBI / UI gates |
| `terminology` | Action & field label presentation |
| `disclosures` | Disclosure ports |
| `disclaimer_engine` | Contextual disclaimers |
| `conflicts` | Conflict-of-interest ports |
| `audit` | Compliance audit ports |
| `recommendation_history` | SEBI history archive ports |
| `methodology` | Methodology disclosure stubs |
| `research_archive` | Retention ports |
| `ai_governance` | AI Challenge Mode ports |
| `analyst_consensus` | Street consensus ports (no providers) |
| `metric_presentation` | Metric card schema |
| `analysis_sections` | Canonical analysis IA |
| `interfaces` | Re-exports |

---

## Non-goals

- No SEBI registration workflow implementation  
- No vendor consensus providers  
- No mutation of `recommendation` / `valuation` packages  
- No OMS  

---

## Tests

`packages/compliance/tests/test_compliance.py` — flags, terminology, IA order,
boundary checks.
