# Auth Testing Playbook — Email & Password (security_platform JWT)

Auth is gated by `DSP_ENABLE_SECURITY=true`. The FastAPI app is `api_platform.api.app:create_app`.
Routes are mounted at both `/` and `/api/v1`.

## Env
```
DSP_ENABLE_SECURITY=true
DSP_JWT_SECRET=<64-char-hex>
DSP_ADMIN_EMAIL=admin@dsp.ai
DSP_ADMIN_PASSWORD=DspAdminPass2026
DSP_COOKIE_AUTH=true
```

## Seeded admin
- email `admin@dsp.ai` / password `DspAdminPass2026` / role `admin`

## Flows to verify (in-process TestClient or live)
1. Register: `POST /api/v1/auth/register` {email,password(>=12, upper+lower+digit)} -> 200, returns access_token + role=viewer.
2. Weak password rejected: register with "short" -> 4xx with policy message (fail-closed).
3. Duplicate email -> 409.
4. Login as seeded admin: `POST /api/v1/auth/login` {username: "admin@dsp.ai", password: "DspAdminPass2026"} -> 200 access_token, role=admin.
5. Me: `GET /api/v1/auth/me` with `Authorization: Bearer <access_token>` -> 200, email + role.
6. Me without token -> 401.
7. Bad password login -> 401; repeated failures -> lockout (429/401 "account locked").

## curl (live, once app served)
```
curl -X POST $URL/api/v1/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"user1@example.com","password":"UserPass12345"}'
curl -X POST $URL/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin@dsp.ai","password":"DspAdminPass2026"}'
curl $URL/api/v1/auth/me -H "Authorization: Bearer <token>"
```
