# Security Guide (PEP-001)

## Secrets

- Prefer `SecretsPort` / `DSP_SECRET_*` / `DSP_JWT_SECRET` from environment.
- Never log JWT secrets, password hashes, refresh tokens, or reset tokens.
- Production must not use `dev-only-change-me`.

## Password policy (defaults)

- Minimum length 12
- Require mixed case + digit
- Reject empty / whitespace-only
- Hash: Argon2id when `argon2-cffi` installed; else scrypt (stdlib reference)

## Account lockout

- Threshold: 5 failed password attempts
- Lock duration: 15 minutes
- Audit: `login_failed`, `account_locked`

## Rate limiting

- Login / refresh / reset keys via PEP-002 `RateLimitPort` when wired
- Fallback: in-process `RateLimiter`

## Audit events (minimum)

`login_success` · `login_failed` · `logout` · `token_refresh` · `token_revoke` · `password_change` · `password_reset_request` · `password_reset_confirm` · `user_activated` · `user_deactivated` · `mfa_*` · `consent_*`

Append-only when using SQL audit store; in-memory ring for CI.

## Headers

API layer continues to apply CSP / nosniff / frame-deny via existing middleware. Identity layer does not weaken headers.

## India / DPDP posture

- Store consent records via `ConsentRecordPort`
- Do not store Aadhaar numbers
- PAN verification uses hashed identifiers only (port)
- DigiLocker / KYC are ports only

## Threat notes

| Threat | Control |
|---|---|
| Credential stuffing | Lockout + rate limit |
| Refresh theft | Rotation + revoke-on-password-change |
| JWT secret leak | SecretsPort / rotate secret + invalidate |
| Privilege escalation | Frozen RBAC + admin-only ManageUsers |
