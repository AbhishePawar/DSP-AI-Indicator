# P1-09 fixture authentication

P1-09 uses one canonical credential variable:

`DSP_SEED_ADMIN_PASSWORD`

The real value must never be committed, documented, printed, or embedded in a test. Keep it in the ignored local environment file:

`apps/web/.env.local`

Example shape (leave the value private):

```dotenv
DSP_SEED_ADMIN_PASSWORD=<your-local-fixture-password>
DSP_P109_LOGIN=admin
DSP_P109_TICKER=DSPFIX
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000/api/v1
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000
```

`apps/web/playwright.config.ts` explicitly loads this file before reading Playwright configuration. Shell/CI environment variables take precedence over values in the file.

The P1-09 validator resolves the password as:

1. `DSP_SEED_ADMIN_PASSWORD`
2. `DSP_P109_PASSWORD` (legacy fallback only)
3. a clear configuration error before the browser journey starts

The backend development seed must receive the same `DSP_SEED_ADMIN_PASSWORD` environment variable. The seed has no checked-in default password.

## Failure classification

- **Missing configuration:** `P109ConfigError` before browser fixtures are requested.
- **Backend unavailable:** P1-09 health checks fail against `/health/live` or `/health/ready`.
- **Frontend unavailable:** the configured frontend URL cannot be reached.
- **Authentication failure:** the login request or authenticated account assertion fails.

## Local validation

From `apps/web`:

```bash
pnpm exec vitest run e2e/browser/p109/env.test.ts
pnpm run test:p109
```

P1-09 is considered PASS only after the real Chromium journey executes successfully against the running backend and frontend. A configuration/unit-test pass is not a P1-09 journey pass.
