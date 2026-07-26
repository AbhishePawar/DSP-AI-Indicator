<!-- ASI-005-PACKAGE-CARD -->
# compliance

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

DSP Compliance & Product Mode architecture — feature flags, disclosures, presentation terminology (PR1.0)

## 2. Responsibilities

Provide the stable `compliance` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Production · Frozen (PR1.0)** · Version **0.1.0** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`__all__` exports (7): `ANALYSIS_PAGE_ORDER`, `AnalysisSection`, `FeatureFlags`, `ResearchLabel`, `load_feature_flags`, `present_action`, `present_field_label`

## 5. Package Structure

`packages/compliance/src/compliance/` · `packages/compliance/tests/` · local `pyproject.toml` when present.

## 6. Dependencies

*(none declared)*

## 7. Architecture Notes

Architecture allowlists / freeze policy apply. See appendix and [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
import compliance
print(compliance.__version__)
```

Worked examples live in `packages/compliance/tests/`.

## 9. Testing

```bash
pytest packages/compliance/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

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
