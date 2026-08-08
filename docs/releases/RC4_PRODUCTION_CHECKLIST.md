# Production Checklist — Version 2.0 RC (`2.0.0-rc.1`)

| Field | Value |
|---|---|
| Programme | EPS-003 |
| Channel | `rc` |
| Complements | [`GO_LIVE_CHECKLIST.md`](./GO_LIVE_CHECKLIST.md) · [`OPERATIONS_RUNBOOK.md`](./OPERATIONS_RUNBOOK.md) |
| Date | 2026-08-02 |

Use this checklist before promoting an RC build to staging or a controlled pilot. It does **not** authorize Commercial GA.

---

## A. Identity & freeze

- [ ] `VERSION` reads `2.0.0-rc.1`
- [ ] Web `package.json` / `VERSION_MANIFEST.json` channel `rc`
- [ ] Image tags `dsp-api:2.0.0-rc.1` / `dsp-web:2.0.0-rc.1` (or equivalent)
- [ ] Messaging: **Release Candidate / Research Mode** — not Commercial GA
- [ ] Feature freeze acknowledged (no engine/UX redesign in hotfix without board)

## B. Secrets & config

- [ ] `.env.production` sourced from secret manager (not committed)
- [ ] `DSP_JWT_SECRET` ≥ 32 chars, unique per environment
- [ ] `DSP_SEED_ADMIN_PASSWORD` rotated from template
- [ ] Postgres / Redis / Grafana passwords rotated
- [ ] `DSP_CORS_ORIGINS` restricted to real app origin(s)
- [ ] `DSP_ENABLE_SECURITY=true`, admin auth required, rate limit on
- [ ] No LLM API keys in `NEXT_PUBLIC_*`

## C. Security headers & edge

- [ ] Next CSP enforced (includes `object-src 'none'`)
- [ ] Caddy/edge HSTS + TLS verified
- [ ] API security headers present on sample responses
- [ ] Admin / enterprise / portal routes not anonymously writable in prod config

## D. Enterprise foundation caveats

- [ ] Operators understand **in-memory** enterprise store limits (single process / no HA claim)
- [ ] Billing surfaces show honesty empties (Null adapter)
- [ ] Collaboration realtime **not** promised
- [ ] If multi-replica API planned → **STOP** until durable store (not RC-complete)

## E. Health & ops

- [ ] `/health` · `/health/live` · `/health/ready` green
- [ ] `/metrics` scraped (or explicitly deferred with board note)
- [ ] Backup / restore runbook owners assigned ([`ROLLBACK_PLAN.md`](./ROLLBACK_PLAN.md))
- [ ] Support path published internally ([`SUPPORT_RUNBOOK.md`](./SUPPORT_RUNBOOK.md))
- [ ] Limitations packet attached ([`RC4_KNOWN_LIMITATIONS.md`](./RC4_KNOWN_LIMITATIONS.md))

## F. Verification gates (minimum)

- [ ] Enterprise unit + API tests green in CI
- [ ] Web `test:quality` green
- [ ] Release smoke / commercial-readiness green
- [ ] Production `next build` green on clean workspace
- [ ] Smoke: login → dashboard → company analysis → report path

## G. Explicit non-goals for this promote

- [ ] No self-serve checkout enablement
- [ ] No “Commercial GA” release notes / sales sheets
- [ ] No silent demo tickers / fabricated metrics

---

**Sign-off:** Engineering ______ · Ops ______ · Trust/Governance ______ · Date ______
