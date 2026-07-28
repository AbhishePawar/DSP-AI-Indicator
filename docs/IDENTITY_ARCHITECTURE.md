# Identity Architecture (PEP-001)

| Field | Value |
|---|---|
| **Status** | **FROZEN for PEP-001 scope** |
| **Authority** | [PEP_000](PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md) · ADR-PEP-0006/0007/0008 |
| **Package** | `security_platform` **0.2.0** |
| **Infra** | [PEP_002](PEP_002_ENTERPRISE_INFRASTRUCTURE_FOUNDATION.md) ports |

---

## 1. Authentication model

| Mode | Day-1 | Notes |
|---|---|---|
| Password + JWT | **Yes** | Argon2 preferred; scrypt reference when argon2 absent |
| Passwordless username (RC) | **Compat** | Allowed only when user has **no** password hash |
| API keys | **Yes** | Existing service-account style keys |
| Refresh tokens | **Yes** | Opaque tokens; rotation + revocation |
| MFA (TOTP) | Architecture | Required for ADMIN before GA enterprise; port ready |
| OIDC / SSO | Architecture | Via existing `OAuth2TokenValidator` |
| Federation / SCIM | Architecture | Future org provisioning ports |

## 2. Authorization model

RBAC at gateway (`SecurityMiddleware`) using frozen roles:

`ADMIN` · `ADVISOR` · `CLIENT` · `RESEARCHER` · `API` · `GUEST`

Permission matrix remains in `ROLE_PERMISSIONS`. Custom / org-scoped permissions are additive overlays (see [RBAC_MODEL.md](RBAC_MODEL.md)).

## 3. Identity lifecycle

```text
provision → activate → authenticate → (optional lock) → deactivate → (DPDP erase later)
```

- Provision: create user with role, optional email/org
- Activate / deactivate: `active` flag; inactive cannot authenticate
- Password set/reset: policy-validated; hashed at rest
- Email verification: token issued; verified flag (architecture + in-memory/SQL store)

## 4. Session lifecycle

```text
login → create session (SessionPort) → access JWT (+ refresh) → activity touch → expire/revoke → logout
```

Sessions store metadata only (user_id, issued_at, expires_at, remember_me, client fingerprint hash). No passwords in session blobs.

## 5. Permission model

- Role → default permission set
- Optional `extra_permissions` on user
- Future: org role bindings, delegated admin grants (ports)

## 6. Organisation model

```text
Organisation { org_id, name, status }
Membership { user_id, org_id, org_role }   # architecture; single default org in PEP-001
```

Multi-tenant RLS is **PEP-007** (after DPDP).

## 7. Role hierarchy (authority, not inheritance)

```text
ADMIN > ADVISOR ≈ RESEARCHER ≈ API > CLIENT > GUEST
```

Hierarchy is for delegated-admin checks only; permissions stay explicit matrices.

## 8. Account recovery

1. Request reset → rate-limited → issue single-use token (TTL)
2. Confirm reset → validate token → set new password hash → revoke refresh tokens + sessions
3. Audit `password_reset_*` events

Email delivery is an adapter concern (not implemented in PEP-001).

## 9. Token lifecycle

| Token | Type | TTL default | Storage |
|---|---|---|---|
| Access JWT | HS256 signed | 15–60 min (settings) | Stateless (+ optional denylist) |
| Refresh | Opaque random | 7–30 days | RefreshTokenStore (memory or DB) |
| Reset / verify | Opaque | minutes–hours | Token store |

**Rotation:** refresh exchange issues new access + new refresh; old refresh revoked.  
**Revocation:** logout / password change / admin revoke → refresh + session deleted; optional JWT `jti` denylist.

## 10. MFA architecture

```text
MfaPort.enroll(user_id) → secret
MfaPort.verify(user_id, code) → bool
```

Privileged roles (ADMIN, future COMPLIANCE_OFFICER) require MFA once adapter enabled. Null adapter = MFA not enforced (dev/CI).

## 11. Service accounts & API keys

Existing `ApiKeyManager` remains the service-account mechanism (`Role.API`). Keys are hashed secrets; owner_user_id optional.

## 12. Future SSO / OIDC / federation / SCIM

| Port | Purpose |
|---|---|
| `OAuth2TokenValidator` | Validate IdP access tokens (exists) |
| `OidcClientPort` | Authorization-code exchange (architecture) |
| `ScimProvisioningPort` | User/group sync (architecture) |
| `EnterpriseFederationPort` | SAML/OIDC multi-IdP (architecture) |

## 13. India-first (ports only)

| Port | Purpose |
|---|---|
| `ConsentRecordPort` | DPDP consent / purpose records — when composed (PEP-004.1), backed by `compliance.ConsentPort` |
| `PanVerificationPort` | Future PAN KYC (hash-only) |
| `DigiLockerPort` | Future document fetch |
| `AadhaarPort` | Future — **no storage without legal epic** |
| `EnterpriseKycPort` | Future institutional KYC |

## 14. PEP-002 wiring

| Concern | Port |
|---|---|
| User / audit / refresh persistence | `DatabasePort` |
| Session blobs | `SessionPort` |
| Login / reset rate limits | `RateLimitPort` |
| JWT signing secret | `SecretsPort` / settings |

Composition: `SecurityBundle.create()` (offline) or
`SecurityBundle.create_with_infrastructure(infra, consent_store=…)`.
Enterprise composition: `platform_runtime.EnterprisePlatform.create_offline()`.
