# Compliance (PR1.0)

Bounded context for **product operating modes**, **presentation terminology**,
**disclosures**, and **future SEBI activation architecture**.

**Version:** `0.1.0`  
**Status:** Architecture scaffold — **no SEBI recommendation UI is active**.

## Role

| Owns | Does not own |
|---|---|
| Feature flags / mode policy | Valuation / risk / recommendation engines |
| Research-mode terminology mapping | API contracts / OMS |
| Disclosure & disclaimer interfaces | Market data providers |
| AI governance / audit interfaces | Business report payloads |
| Analyst consensus **ports** (future) | Consensus provider integrations |

## Default mode (Phase 1)

```text
RESEARCH_MODE=true
RECOMMENDATION_MODE=false
SEBI_MODE=false
```

In Research Mode, hard-coded BUY / SELL / HOLD / Target Price labels must not
appear in user-facing UI. Use `terminology.present_action(...)` instead.

## Phase 2 (architecture only)

When SEBI registration is complete, operators flip flags:

```text
RESEARCH_MODE=true
RECOMMENDATION_MODE=true
SEBI_MODE=true
ShowBuySell / ShowTargetPrice / … = true
```

Engines stay frozen; only presentation and compliance surfaces activate.

## Modules

| Module | Purpose |
|---|---|
| `feature_flags` | Mode and UI capability flags |
| `terminology` | Research ↔ SEBI presentation vocabulary |
| `disclosures` | Mandatory disclosure interfaces |
| `disclaimer_engine` | Contextual disclaimer selection |
| `conflicts` | Conflict-of-interest records |
| `audit` | Compliance audit event ports |
| `recommendation_history` | SEBI-mode history archive ports |
| `methodology` | Methodology disclosure stubs |
| `research_archive` | Research artifact retention ports |
| `ai_governance` | AI Challenge Mode + governance ports |
| `analyst_consensus` | Market consensus ports (no providers) |
| `metric_presentation` | UX metric card schema |
| `analysis_sections` | Canonical analysis page order |
| `interfaces` | Shared protocol exports |

## Dependency rule

`compliance` → `core` only.  
No imports from `recommendation`, `valuation`, `dsp_platform`, or API layers.
Presentation adapters **read** engine enums as strings; they never mutate engines.
