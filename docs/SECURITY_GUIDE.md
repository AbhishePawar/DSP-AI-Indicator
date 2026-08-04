# EPIC-A009 — Security Guide

## Passwords

- Never stored in plaintext
- Format: `pbkdf2$iterations$salt$digest` (SHA-256, 120k iterations)
- Verification uses constant-time compare

## Tokens

- Access JWT: short-lived (`token_use=access`)
- Refresh JWT: longer-lived (`token_use=refresh`), bound to session `jti`
- Logout revokes the session → subsequent access/refresh fail

## Sessions

- Concurrent sessions allowed
- Per-session revocation does not invalidate sibling sessions
- Expired sessions reject token use

## Validation

Rejects: duplicate username/email, invalid credentials, malformed/expired tokens,
unknown roles, missing permissions.

## Compliance posture

Supports CV-001 / CV-002 / CV-003 identity controls without altering research
immutability (RS-001…RS-010). Auth stores identity metadata only.
