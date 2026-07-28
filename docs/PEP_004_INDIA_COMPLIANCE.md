# PEP-004 — India Compliance Foundation

| Field | Value |
|---|---|
| **Status** | **COMPLETE** |
| **Date** | 2026-07-28 |
| **Package** | `compliance` **0.1.0 → 0.2.0** |
| **Depends on** | PEP-000 · PEP-001 · PEP-002 · PEP-003 |

## Summary

India-first compliance foundation: DPDP consent versioning, Research Mode disclosure templates (IST/INR), recommendation/research history, research archive, immutable audit references with CERT-In retention floor, and export interfaces — composed via `ComplianceBundle`. Engines, thin client, and API contracts unchanged. SEBI adviser workflows / Aadhaar / PAN / DigiLocker / UPI **not** implemented.

## Architecture

See [COMPLIANCE_ARCHITECTURE.md](COMPLIANCE_ARCHITECTURE.md), [DPDP_ARCHITECTURE.md](DPDP_ARCHITECTURE.md), [DISCLOSURE_GUIDE.md](DISCLOSURE_GUIDE.md).

Ports: `CompliancePort`, `ConsentPort`, `DisclosurePort`, `RecommendationHistoryPort`, `ResearchArchivePort`, `AuditRetentionPort`, `ComplianceExportPort`.

Persistence: optional duck-typed SQL adapters accept PEP-002 `DatabasePort` without importing `production_platform`.

## Files added

- `consent.py`, `retention.py`, `disclosure_templates.py`, `history_adapters.py`, `export.py`, `persistence.py`, `bundle.py`
- `tests/test_pep004.py`
- Docs: COMPLIANCE_ARCHITECTURE (rewrite), DPDP_ARCHITECTURE, DISCLOSURE_GUIDE, PEP_004_INDIA_COMPLIANCE

## Files modified

- `__init__.py`, `interfaces.py`, `recommendation_history.py`, `pyproject.toml`, architecture test version
- VERSION_MATRIX

## Tests

Contract suite `test_pep004.py` — **PASS**.  
Full monorepo pytest: **2655 / 2655 PASS**.

## Risks

| Risk | Mitigation |
|---|---|
| Dual consent stores (security + compliance) | **Resolved in PEP-004.1** — composed SoT is `compliance.ConsentPort` via bridge |
| Erasure vs CERT-In retention | Policy documents override; jobs deferred |
| SEBI Mode misuse | Flags remain gated; extra disclosure |

## Final assessment

**PASS** — India compliance foundation ready for institutional pilots under Research Mode.
