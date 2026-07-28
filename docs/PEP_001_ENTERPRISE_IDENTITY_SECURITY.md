# PEP-001 — Enterprise Identity & Security

| Field | Value |
|---|---|
| **Status** | **COMPLETE** (foundation) |
| **Date** | 2026-07-28 |
| **Package** | `security_platform` **0.1.0 → 0.2.0** |
| **Depends on** | [PEP-002](PEP_002_ENTERPRISE_INFRASTRUCTURE_FOUNDATION.md) |
| **Authority** | [PEP_000](PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md) · ADR-PEP-0006 |

---

## 1. Executive Summary

PEP-001 adds durable identity, password authentication, refresh-token rotation, session tracking, RBAC continuity, audit/consent foundations, and India KYC **ports** — all without changing investment engines, thin client behaviour, or breaking `/api/v1` contracts. Passwordless username login remains for accounts without a password hash (RC compatibility). Optional password + `refresh_token` are additive.

## 2. Identity Architecture

Documented in [IDENTITY_ARCHITECTURE.md](IDENTITY_ARCHITECTURE.md): lifecycle, org model, recovery, MFA/OIDC/SCIM ports, DPDP consent.

## 3. Security Architecture

[SECURITY_GUIDE.md](SECURITY_GUIDE.md): Argon2-preferred hashing (scrypt reference), lockout, rate limits via PEP-002 `RateLimitPort`, secrets via settings/`SecretsPort`, audit events.

## 4. RBAC Model

[RBAC_MODEL.md](RBAC_MODEL.md): frozen roles/permissions unchanged; `extra_permissions` + org membership architecture for future delegated admin.

## 5. Session Architecture

`SessionTrackerPort` with in-memory reference and `Pep002SessionTracker` over `SessionPort`. Login creates session metadata; logout/password change revokes sessions + refresh tokens.

## 6. Token Lifecycle

Access JWT (HS256, `jti`, optional `sid`) + opaque refresh tokens with rotation and revocation. See [AUTHENTICATION_FLOW.md](AUTHENTICATION_FLOW.md).

## 7. Files Added

- `packages/security_platform/src/security_platform/security/identity/` (ports, password, repository, tokens, service, india)
- `packages/security_platform/tests/test_identity.py`
- `docs/IDENTITY_ARCHITECTURE.md`, `RBAC_MODEL.md`, `SECURITY_GUIDE.md`, `AUTHENTICATION_FLOW.md`, `PEP_001_ENTERPRISE_IDENTITY_SECURITY.md`

## 8. Files Modified

- `security_platform` auth/users/rate_limit/`__init__`/pyproject/tests
- `api_platform` `routers/auth.py` (additive password/refresh)
- `docs/VERSION_MATRIX.md`

## 9. Test Results

**2636 / 2636 PASS** (full monorepo pytest).  
Identity contract suite: `packages/security_platform/tests/test_identity.py`.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Passwordless still enabled by default | `allow_passwordless` + production hardening guide |
| Refresh store still in-memory even with infra | Session on Redis/SessionPort; refresh SQL store deferred |
| MFA not enforced | NullMfaPort until enterprise GA |
| Aadhaar misuse | Port raises; legal epic required |

## 11. Migration Notes

1. Upgrade `security_platform` to 0.2.0  
2. Keep `SecurityBundle.create()` for CI  
3. Staging: `SecurityBundle.create_with_infrastructure(infra)`  
4. Seed admin with password via `seed_admin_password`  
5. Clients may ignore new `refresh_token` field  
6. Additive `POST /auth/refresh`

## 12. Final Assessment

| Criterion | Result |
|---|---|
| Persistent identities | **PASS** (SQL via DatabasePort + memory) |
| Secure password storage | **PASS** |
| Session management | **PASS** |
| Refresh tokens | **PASS** |
| RBAC | **PASS** (unchanged matrix) |
| Audit trail | **PASS** |
| Uses PEP-002 ports | **PASS** |
| Business logic unchanged | **PASS** |
| Thin client unchanged | **PASS** |
| Existing APIs preserved | **PASS** (additive only) |
