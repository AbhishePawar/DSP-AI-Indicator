# PEP-004.1 — Platform Integration & Readiness

| Field | Value |
|---|---|
| **Status** | **COMPLETE** |
| **Date** | 2026-07-28 |
| **Package** | `platform_runtime` **0.1.0** (new) |
| **Depends on** | PEP-000 · PEP-001 · PEP-002 · PEP-003 · PEP-004 |

## Goal

Validate and compose completed enterprise PEPs into a single offline-capable
composition root. Align Identity ↔ Compliance consent. Verify infrastructure,
observability, health/readiness, dependency rules, and documentation consistency.

## Non-goals (honoured)

- No investment engine changes
- No `/api/v1` contract changes
- No thin-client changes
- No new business features

## Integration summary

| Bundle | Package | Wired how |
|---|---|---|
| Infrastructure | `production_platform` | `InfrastructureBundle.create_offline` |
| Observability | `production_platform` | `ProductionBundle.create(..., with_observability=True)` |
| Identity | `security_platform` | `SecurityBundle.create_with_infrastructure(infra, consent_store=…)` |
| Compliance | `compliance` | `ComplianceBundle.create(database=infra.database)` |
| Composition | `platform_runtime` | `EnterprisePlatform.create_offline()` |

**Consent source of truth:** `compliance.ConsentPort` via
`ComplianceBackedConsentStore` (identity records through the bridge; no dual
durable stores when composed).

## Architecture review

| Rule | Result |
|---|---|
| Hexagonal ports; adapters only | **PASS** |
| Engines not imported by composition | **PASS** (architecture test) |
| `compliance` ↛ `security_platform` / engines | **PASS** (composition only in `platform_runtime`) |
| `security_platform` ↛ `compliance` | **PASS** (duck-typed consent_store injection) |
| Thin client / API contracts untouched | **PASS** |
| Research Mode default; SEBI off | **PASS** (startup check) |
| CERT-In retention floor ≥180d | **PASS** (obs + audit retention checks) |

## Startup validation

`validate_enterprise_startup` / `EnterprisePlatform.readiness()` check:

infrastructure ping · observability present · CERT-In log retention ·
security identity · research-mode defaults · audit retention floor ·
research disclosures · production liveness/readiness · consent alignment.

## Files changed / added

### Added

- `packages/platform_runtime/` (composition, consent bridge, readiness, tests)
- `docs/PEP_004_1_PLATFORM_INTEGRATION_READINESS.md`

### Modified

- `packages/security_platform/.../auth.py` — optional `consent_store=` on create paths
- Root `pyproject.toml` — register `platform_runtime`
- `packages/dsp_platform/.../boundaries.py` — `PLATFORM_PACKAGES`
- `docs/VERSION_MATRIX.md`, `docs/DPDP_ARCHITECTURE.md`, `docs/PEP_004_INDIA_COMPLIANCE.md`
- `docs/PEP_ARCHITECTURE_DECISIONS.md`, `docs/PEP_DEPENDENCY_RULES.md`

## Tests

- `packages/platform_runtime/tests/test_architecture.py`
- `packages/platform_runtime/tests/test_integration.py`

Contract suite: **8 / 8 PASS**.  
Full monorepo pytest: **2663 / 2663 PASS**.

## Risks

| Risk | Mitigation |
|---|---|
| Uncomposed apps still use local identity consent | Document SoT; composition required for DPDP export alignment |
| `platform_runtime` not yet wired into `api_platform` | Intentional — ADR forbids engine/API redesign under this PEP |
| Offline adapters ≠ production vendors | Production swaps adapters via existing infra profiles |

## Final readiness assessment

**READY** for institutional pilots under Research Mode for **PEP-001…004
composition**. API gateway wiring remains a later epic; engines and thin client
remain frozen.
