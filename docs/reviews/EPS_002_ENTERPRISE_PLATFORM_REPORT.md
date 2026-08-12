# EPS-002 — Enterprise Commercial Platform (EPIC-016+017+018+019) v2.0

**Status:** FOUNDATION COMPLETE (not Commercial GA)  
**Date:** 2026-08-02  
**Branch:** `cursor/p6-1-commercial-readiness`  
**Programme:** Enterprise platform (not research)

---

## 1. Executive Summary

DSP now has a coherent **Enterprise Commercial Platform foundation**: multi-tenant organizations/teams, permission-based enterprise RBAC, licensing, billing ports (Null adapter), customer/ops portals, sessions, immutable audit, API keys, usage analytics (honest zeros), incident/ops dashboard, and collaboration architecture ports.

Research engines, valuation, BQ, Moat, Risk, AI Committee, Explainability, Research Intelligence, Comparison, Portfolio, Research Canvas, REP-002, Trust, and GOV-001 were **not modified**.

**Honest readiness:** Foundation and testable vertical slice shipped. Production billing provider, durable Postgres enterprise store, SSO/MFA, and realtime collaboration remain **remaining commercial work**. Commercial GA is **not** unlocked.

---

## 2. Organizations / Teams / RBAC

| Capability | Implementation |
|---|---|
| Organizations | Profile, settings, branding, prefs, metadata, seat limits, ownership, status |
| Invitations | Pending invitations with expiry |
| Members | Add, role change, seat-limit enforcement, org isolation |
| Teams | Kinds: department / research / investment / analyst / read_only / committee / custom; parent_team_id hierarchy-ready |
| Roles | Owner, Administrator, Research Director, Senior Analyst, Analyst, Portfolio Manager, Investment Committee, Viewer, Guest + custom roles |
| Authorization | **Permission keys only** (`org.view`, `members.manage`, …) — UI/nav must not hardcode role checks for enterprise gates |

**Package:** `packages/enterprise`  
**Prior wiring:** A009 institutional auth + A010 admin routers registered; `require_admin_access` restored.

---

## 3. Licensing / Billing / Customer Portal

| Area | Status |
|---|---|
| License tiers | trial · research · professional · institutional · enterprise |
| Validation | Expiration + status checks; honest “No license assigned.” |
| Seats / usage limits | Seat limit on org; usage_limits metadata on license |
| Billing | `BillingPort` + `NullBillingAdapter` only — **no fake checkout** |
| Customer Portal | `/portal` → org, license, members, usage, invoices, API keys, settings |

Invoices/subscription surfaces show **“Billing unavailable.”** until a real provider adapter is configured.

---

## 4. Security (sessions, audit, API keys)

| Control | Behaviour |
|---|---|
| Sessions | Create, list active, revoke (device label + hints) |
| Audit | Append-only immutable records; DELETE returns 403 |
| API keys | Generate / rotate / disable; scopes; expiration; secret shown once; **hash never listed** |
| Secrets | Server-side only; frontend never receives `secret_hash` or env secrets |

Also wired: institutional `/auth/rbac/*` and `/admin/*` (A009/A010) with P1.2 admin auth dependency.

---

## 5. Operations / Observability / Admin

| Surface | Route / API |
|---|---|
| Admin Console (existing) | `/admin` + `/api/v1/admin/*` (now registered) |
| Enterprise admin overview | `GET /api/v1/enterprise/admin/overview` |
| Ops / Incident Center | `/ops` + `GET /api/v1/enterprise/ops/*` |
| Usage analytics | DAU / orgs / research / exports / comparisons / storage / API — honest zeros |
| Observability | Reuses EPIC-011A infrastructure hooks when present; unknown components → “Data unavailable.” |

---

## 6. Collaboration Architecture

Ports/models only (`CollaborationPort`, `SharedResearchRef`, `Comment`, `ApprovalRequest`).  
**Realtime is not implemented.** Documented via `GET /api/v1/enterprise/collaboration/architecture`.

Reserved: shared research, comments, mentions, approvals, review, committee approval, ownership transfer.

---

## 7. Validation Results

| Suite | Result |
|---|---|
| `packages/enterprise/tests/test_enterprise.py` | Org isolation, RBAC permissions, license/billing empties, audit immutability, API key scopes, session revoke, portal/ops, teams |
| `packages/api_platform/tests/test_enterprise_api.py` | Schema, portal, secret non-leakage, session revoke, audit DELETE 403, ops/collab, RBAC gate, admin router wired |
| Research engines | Untouched (by design) |

---

## 8. Remaining Commercial Work

1. Production billing provider adapter (Stripe/etc.) behind `BillingPort`
2. Durable Postgres/Redis enterprise store (beyond in-memory foundation)
3. SSO / OIDC / MFA for institutional IdP
4. HttpOnly cookie sessions (browser token storage still open from P1.2)
5. Realtime collaboration transport
6. Deployment registry / alerting integrations for ops dashboard
7. CERT-In retention-backed durable audit sink
8. Seat metering wired to live analyse/export counters

---

## 9. Enterprise Readiness / Release Recommendation

| Question | Answer |
|---|---|
| Foundation ready for institutional onboarding pilots? | **YES** (with in-memory / Null billing caveats) |
| Commercial GA / paid checkout? | **NO** |
| Research platform risk? | **None** — research frozen |
| Recommendation | **SHIP FOUNDATION** on this branch; do not market as Commercial GA |

---

## 10. Architecture Impact

- **Added:** `packages/enterprise` domain + `/api/v1/enterprise/*` router
- **Wired:** institutional auth/admin/beta routers previously unregistered
- **Restored:** `require_admin_access` dependency
- **Frontend:** `/portal`, `/ops`, feature flags, nav entries
- **Security middleware:** enterprise + beta zones delegated like institutional admin
- **Not changed:** research engines, analyse contracts, thin-client rules

### Components Added
- `packages/enterprise/*`
- `packages/api_platform/.../routers/enterprise.py`
- `apps/web` portal + ops surfaces + `lib/enterprise/*`

### Pages Updated / Added
- `/portal` (Customer Portal)
- `/ops` (Operations)
- `/admin` (now live against registered A010 APIs)
- Nav: Customer Portal, Operations

### Feature Flags
- `NEXT_PUBLIC_ENTERPRISE_PORTAL` (default true)
- `NEXT_PUBLIC_ENTERPRISE_ADMIN` (default true)
- `NEXT_PUBLIC_ENTERPRISE_OPS` (default true)

### Accessibility / Performance / Responsive
- Semantic headings, `role="status"` / `role="alert"`, labelled org select
- Dynamic imports / code-split for portal & ops
- Responsive grids (`sm:grid-cols-*`)
- Dark/light via existing CSS variables

### Known Limitations
- In-memory enterprise store (process-local)
- Null billing only
- Actor identity via `X-User-Id` on enterprise routes (foundation; production should bind to JWT subject)
- Collaboration architecture only

### Future Enhancements
See §8 Remaining Commercial Work.

### Regression Summary
Enterprise + admin wiring tests green; research untouched.

---

## 11. Key Routes & Packages

### HTTP (additive `/api/v1`)
- `/api/v1/enterprise/schema`
- `/api/v1/enterprise/organizations*`
- `/api/v1/enterprise/organizations/{id}/portal`
- `/api/v1/enterprise/organizations/{id}/license|billing|invoices|members|teams|sessions|audit|api-keys|usage`
- `/api/v1/enterprise/ops/incident-center|dashboard|usage`
- `/api/v1/enterprise/admin/overview`
- `/api/v1/enterprise/collaboration/architecture`
- `/api/v1/auth/rbac/*` (wired)
- `/api/v1/admin/*` (wired)
- `/api/v1/beta/*` (wired)

### Packages
- `packages/enterprise` — domain
- `packages/auth` / `packages/admin` — prior A009/A010 (wired)
- `packages/api_platform` — routers + `require_admin_access`
- `apps/web` — portal / ops UX

### Secrets policy
- Never put billing/provider secrets in frontend env (`NEXT_PUBLIC_*`)
- API key plaintext returned once on create/rotate only
- Prefer `DSP_*` server env for JWT, DB, Redis, billing credentials

---

## 12. Implementation Return Format Checklist

| Item | Status |
|---|---|
| Architecture Impact | Documented |
| Components Added | Documented |
| Pages Updated | Documented |
| Feature Flags Used | Documented |
| Accessibility Validation | Semantic/a11y patterns applied |
| Performance Validation | Lazy/dynamic imports |
| Responsive Validation | Grid breakpoints |
| Known Limitations | Documented |
| Future Enhancements | Documented |
| Regression Summary | Documented |
