# EPIC-A009 — Security Guide

## Passwords

- Never stored in plaintext
- Format: `pbkdf2$iterations$salt$digest` (SHA-256, 120k iterations)
- Verification uses constant-time compare

## Tokens

- Access JWT: short-lived (`token_use=access`)
- Refresh JWT: longer-lived (`token_use=refresh`), bound to session `jti`
- Logout revokes the session → subsequent access/refresh fail

## Refresh token rotation & reuse detection (OAuth 2.0 Security BCP)

Every successful `POST /auth/rbac/refresh` (institutional/RBAC) call —
and the enterprise platform's `EnterpriseAuthPlatform.refresh_session`
bridge over the same underlying service — **rotates** the refresh token:

- The presented refresh token is single-use. On success, the session's
  active `refresh_token_id` (`jti`) *and* a SHA-256 digest of the raw
  token are atomically swapped for new ones under a per-session lock
  (`auth.sessions.SessionManager.rotate_refresh_token`) — the previous
  token is invalidated in the same operation that mints the new one.
- **Reuse detection**: presenting a refresh token whose `jti`/digest no
  longer matches the session's current record — because it was already
  rotated away and is being replayed, because it was forged, or because
  a concurrent request won the rotation race microseconds earlier —
  immediately revokes the **entire session** (`auth.exceptions.
  RefreshTokenReuseError`). In this architecture a session *is* the
  refresh-token family (one lineage per session), so "revoke the family"
  means "revoke the session" — no parallel token-family table is needed.
- **Concurrent refresh protection** is intentionally strict: if two
  requests present the same still-valid refresh token at the same time,
  at most one succeeds; the other is treated as reuse and the whole
  session — including the winner's brand-new tokens — is torn down. This
  favors detecting credential theft over tolerating client-side races
  (e.g. duplicate submits); clients should treat a `401` from `/auth/
  rbac/refresh` as "re-authenticate", not "retry".
- **Secure hashing**: the raw refresh JWT is never persisted. Only its
  SHA-256 digest is stored on the session row, alongside the existing
  `jti` check, as defense in depth. Session API responses never echo
  this digest back (`AuthSession.to_public_dict()`).
- **Audit trail**: `refresh.issued` (initial login), `refresh.rotated`
  (each successful refresh), `refresh.reused` + `refresh.revoked` +
  `session.revoked` (reuse detected) are recorded via the same
  `AuditLogger` used for every other authentication event — see
  `docs/AUTH_ENTERPRISE_PLATFORM.md` and `docs/security/
  ENTERPRISE_AUTH_PLATFORM.md` for the full event catalogue.
- **Configurable expiration**: refresh TTL remains governed by the
  existing `access_ttl`/`refresh_ttl` on `AuthenticationService`
  (extended by `EnterpriseAuthPlatform._issue_session` for
  `remember_me`), unchanged by rotation — each rotation reissues with a
  fresh sliding expiry from the existing TTL configuration.

## Sessions

- Concurrent sessions allowed
- Per-session revocation does not invalidate sibling sessions
- Expired sessions reject token use
- Explicit session revocation (logout, admin deactivate/revoke, password
  reset, refresh-token reuse detection) is recorded as a `session.revoked`
  audit event

## Validation

Rejects: duplicate username/email, invalid credentials, malformed/expired tokens,
unknown roles, missing permissions.

## Compliance posture

Supports CV-001 / CV-002 / CV-003 identity controls without altering research
immutability (RS-001…RS-010). Auth stores identity metadata only.
