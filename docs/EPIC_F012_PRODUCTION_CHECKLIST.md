# EPIC-F012 — Production Checklist

**Frontend:** v1.0.0 · **Foundation:** F012 `production_release`  
**Backend:** `dsp_platform@1.0.0` (unchanged) · **API:** `v1.0.0-rc1` (unchanged)

## Pre-release

- [x] Align `apps/web/package.json` version to `1.0.0`
- [x] Align `FRONTEND_FOUNDATION_VERSION` / `env.frontendVersion` to `1.0.0`
- [x] Update `VERSION_MANIFEST.json` + `VERSION_MATRIX.md`
- [x] Update release notes (`RELEASE_NOTES_v1.0.0.md`)
- [x] Gate logger `debug`/`info` in production (`NODE_ENV === "production"`)
- [x] Confirm no `console.log` / `debugger` in `src/`
- [x] Confirm `next.config.ts`: CSP enforced, `poweredByHeader: false`, no production source maps, `output: "standalone"`

## Routes (thin client)

| Route | Status |
|---|---|
| `/login` | Verified in freeze + E2E |
| `/dashboard` | Verified |
| `/analysis` | Verified |
| `/portfolio` | Verified |
| `/research` | Verified |
| `/admin` | Verified |
| `/settings` | Verified |
| `/profile` | Spec in freeze (F009) |

## Environment

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Public `/api/v1` base (default local `127.0.0.1:8000`) |
| `NEXT_PUBLIC_APP_NAME` | Display name |
| `NEXT_PUBLIC_AI_PROVIDER` | Presentation flag only (`mock` \| `deterministic` \| `backend`) |
| `NEXT_PUBLIC_ADVISOR_DEMO` | Demo placeholder flag |
| `NEXT_PUBLIC_BUILD_TIMESTAMP` | Optional CI build stamp |
| `NEXT_PUBLIC_MARKET_CACHE_TTL_MS` / `REFRESH_MS` | Quote presentation TTL |

No client secrets. Tokens stay in auth session handling only.

## Quality gates

| Gate | Expected | Result |
|---|---|---|
| `npm run build` | PASS | **PASS** (Next.js 15.5.21 standalone, 95 routes) |
| `npm test` | PASS | See release summary |
| `npm run test:e2e` | PASS | See release summary |
| Accessibility (F010 suite) | PASS | Retained |
| Performance smoke (F011) | PASS | Retained; first-load shared ~103 kB |
| Security headers (CSP, nosniff, frame deny) | PASS | Enforced in `next.config.ts` |
| Dependency audit (`npm audit --omit=dev`) | Review | **3 high** via Next/postcss/sharp transitive — `npm audit fix --force` would downgrade Next (rejected). Track for Next patch upgrade post-cert. |

## Deploy smoke

1. `npm ci` in `apps/web`
2. Set `NEXT_PUBLIC_API_BASE_URL` to production API `/api/v1`
3. `npm run build` && `npm start` (or standalone Node server)
4. Hit `/login` → authenticate → `/dashboard`
5. Spot-check Analysis / Portfolio / Research / Admin / Settings
6. Confirm missing feeds show **Data unavailable.** (honest empty)

## Out of scope (do not change)

- Backend / engines / API contracts
- New product features
- Decision Engine / Research Mode unlock flags
- Browser-side valuation or AI generation
