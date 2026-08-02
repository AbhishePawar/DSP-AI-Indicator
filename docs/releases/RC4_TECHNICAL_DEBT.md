# Technical Debt Register — Version 2.0 RC (`2.0.0-rc.1`)

| Field | Value |
|---|---|
| Programme | EPS-003 |
| Date | 2026-08-02 |
| Policy | Honest register — no fake “cleared” items |

---

## P0 — Blocks durable multi-tenant production claims

| ID | Debt | Impact | Suggested direction |
|---|---|---|---|
| TD-P0-01 | `InMemoryEnterpriseStore` | Data loss on restart; no HA | Postgres-backed enterprise store behind port |
| TD-P0-02 | `NullBillingAdapter` only | No real invoicing/checkout | Stripe (or equiv.) behind `BillingPort` |
| TD-P0-03 | Enterprise identity via `X-User-Id` | Spoofable if exposed | Bind actor to JWT / IdP subject |
| TD-P0-04 | Browser token storage (non-HttpOnly residual) | XSS session theft risk | HttpOnly Secure SameSite cookies |

---

## P1 — Blocks Commercial GA messaging

| ID | Debt | Notes |
|---|---|---|
| TD-P1-01 | Universal trust-ladder chrome incomplete | GA-C3 |
| TD-P1-02 | Headed Visual QA archive missing | GA-C1 |
| TD-P1-03 | Firefox/Safari physical smoke pending | GA-C2 |
| TD-P1-04 | Field LHCI / CWV unpublished | GA-C4 |
| TD-P1-05 | Self-serve entitlements absent | GA-C5 — or explicit invite-only policy |
| TD-P1-06 | SSO / OIDC / MFA not implemented | Institutional expectation |
| TD-P1-07 | Realtime collaboration not implemented | Ports only |

---

## P2 — Engineering hygiene

| ID | Debt | Notes |
|---|---|---|
| TD-P2-01 | Next transitive `postcss` / `sharp` advisories | No safe non-breaking bump at RC |
| TD-P2-02 | CSP `unsafe-inline` / `unsafe-eval` | Next practical residual |
| TD-P2-03 | AUX/Advisor DS mixed with primary `ds` | Acceptable while demoted |
| TD-P2-04 | Root `pyproject.toml` meta version `0.1.0` vs product `2.0.0-rc.1` | Monorepo meta vs product channel |
| TD-P2-05 | Package version scatter (`api_platform` 0.3.0, etc.) | Living matrix — not silently rewritten |
| TD-P2-06 | Seat metering not wired to live analyse/export counters | Honest zeros today |
| TD-P2-07 | CERT-In retention durable audit sink | Append-only in-memory ≠ retention store |
| TD-P2-08 | Unrelated dirty/untracked WIP in workspace | Keep RC commits surgically scoped |

---

## Cleared / reduced in EPS-003

| ID | Item | Status |
|---|---|---|
| GA-C6 | Stale `commercial.test.tsx` AAPL onboarding assertion | **Reduced** — test matches honest copy |
| VER | Version / channel inconsistency (1.0.0 root vs 2.0 web GA-candidate) | **Aligned** to `2.0.0-rc.1` / `rc` |

---

## Register rules

1. Do not mark P0/P1 cleared without evidence.  
2. Do not invent coverage percentages.  
3. Prefer ports/adapters over rewriting research engines.
