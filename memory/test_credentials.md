# Test Credentials — DSP AI Indicator

## Auth (email + password, JWT via security_platform)

Enable auth by setting env before app boot:
```
DSP_ENABLE_SECURITY=true
DSP_JWT_SECRET=<64-char-hex>        # required non-default in production
DSP_ADMIN_EMAIL=admin@dsp.ai       # optional (default shown)
DSP_ADMIN_PASSWORD=DspAdminPass2026 # optional (default shown; must satisfy policy)
DSP_COOKIE_AUTH=true               # optional: also set httpOnly session cookies
```

### Seeded admin account
- email:    `admin@dsp.ai`
- password: `DspAdminPass2026`
- role:     `admin`

(Password policy: min 12 chars, must include upper + lower + digit.)

### Auth endpoints (mounted at both `/` and `/api/v1`)
- `POST /api/v1/auth/register`  { email, password, display_name? } -> JWT (+cookies)
- `POST /api/v1/auth/login`     { username=<email>, password }      -> JWT (+cookies)
- `GET  /api/v1/auth/me`        (cookie or `Authorization: Bearer`) -> profile
- `POST /api/v1/auth/refresh`   { refresh_token } or cookie         -> rotated JWT
- `POST /api/v1/auth/logout`                                        -> clears cookies
- `GET  /api/v1/auth/session`                                       -> session metadata

Note: email is the login identifier (stored as username). Login sends the email
in the `username` field.
