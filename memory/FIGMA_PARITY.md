# Figma parity and functionality inventory

## Authority and counting
Reference: `/app/.figma_ref/src/App.tsx`, `src/index.css`, `src/layouts/AppLayout.tsx`, `src/components/Nav.tsx`, and every file under `src/pages`.
The brief calls these 21 screens; the supplied router actually declares 27 named paths (including the `/analysis/compare` alias) plus a wildcard redirect. Existing privacy/logout routes are also retained below as application extensions. All reference paths are included; this is not a claim that every screen has completed visual acceptance.
Status here is intentionally not a claim of completed pixel parity.

| Reference route | Existing application route | Audit / remaining work |
|---|---|---|
| / | /(marketing)/page | Partial: research-first landing exists; reference navbar, real recent searches and spacing need parity |
| /about | /(marketing)/about | Partial: real public page; visual comparison outstanding |
| /contact | /(marketing)/contact | Partial: existing page; submission/provider behavior needs verification |
| /faq | /(marketing)/faq | Partial: existing page; accordion and spacing audit outstanding |
| /privacy | /(marketing)/privacy | Partial: existing legal page retained |
| /pricing | /(marketing)/pricing | Partial: existing plans retained; no billing work authorized/configured in this pass |
| /login | /(auth)/login | Existing enterprise/email/cookie auth; OAuth unavailable when unconfigured |
| /signup | /signup → /register | Existing backend registration flow; validation and parity tests outstanding |
| /verify-email | /(auth)/verify-email | Existing verification-token flow; delivery provider unconfigured |
| /forgot-password | /(auth)/forgot-password | Existing flow; delivery provider unconfigured |
| /reset-password | /(auth)/reset-password | Existing token flow; delivery must be configured |
| /logout | /(auth)/logout | Existing real logout/session revocation |
| /dashboard | /dashboard | Was a duplicate marketing landing with second sidebar. Replaced with Figma overview, device watchlist, real market health/quote requests and explicit unavailable states |
| /companies | /companies | Existing identity catalogue/search/filter UI. Contains pre-existing hardcoded screening metadata; replace financial/score fields with authoritative data before acceptance |
| /analysis | /analysis | Existing request/result workspace. Unified shell, Figma-aligned form/loading/error states. Now sends identity-only request to existing server-authoritative /analyse. Detailed result parity outstanding |
| /compare and /analysis/compare | /compare and /analysis/compare | Existing comparison page retained; validate selectors and authenticated backend compare, remove demo paths if reachable |
| /portfolio | /portfolio | Existing holdings/workbench retained; audit user data persistence, quote provenance, empty states and explicit demo import controls |
| /research | /research | Existing hub retained; data plumbing and parity outstanding |
| /research/institutional | /research/institutional | Existing report access retained; provider/storage and parity outstanding |
| /research/canvas | /research/canvas | Existing route retained; persistence and parity outstanding |
| /research/intelligence | /research/intelligence | Existing route retained; evidence/verification-only presentation audit outstanding |
| /copilot | /copilot | Existing route retained; verify evidence-grounded chat/session behavior, no invented answers |
| /advisor | /advisor | Existing collaboration tools contain legacy demo fixtures. Must replace with real records or explicit unavailable states; do not call acceptance complete |
| /profile | /profile | Existing financial profile retained; backend persistence/parity validation outstanding |
| /admin | /admin | Existing role-filtered admin tools retained; authorization and table parity testing needed |
| /control-center | /control-center | Existing authorized route retained; verify no private provider/secret content reaches ordinary clients |
| /diagnostics | /diagnostics | Existing authorized diagnostics retained; preserve permissions |
| /coupons | /coupons | Extra reference Coupons page is declared in reference App.tsx; existing route retained; verify permissions and data |

## Shared shell continuation
- One AppLayout and Sidebar across application routes, including dashboard and analysis.
- Reference 220px sidebar, 48px header, compact navigation, Research group, account footer, flagship callout.
- Role-filtered existing tools remain under More. No fabricated recent searches or signed-in user.
- Mobile drawer retains keyboard focus trap, Escape, overlay close and route close; collapse and command palette retained.
- Existing design tokens and Inter/JetBrains Mono retained.
- Unused `layout/ResearchShell.tsx` removed after verifying no imports. Advisor's unrelated `SharedResearchShell.tsx` retained.

## Blocking data/runtime findings
- API was stopped (missing `/app/backend`); thin entrypoint now loads the original DSP app and puts monorepo packages ahead of a conflicting installed `enterprise` package.
- Frontend API path was `/dspapi/v1`; corrected to routed `/api/v1`.
- Market and fundamentals connectors currently report unconfigured/unavailable. No financial fixtures were introduced in this continuation.
- `/api/v1/research/company` is intentionally blocked by existing architectural safeguards. It has NOT been enabled or replaced with an LLM.
- Existing `/api/v1/analyse` supports ticker-only requests and server-side verified source loading. Core methodology code remains untouched.
- Auth preview uses existing development seed with random local credentials. Existing A008 in-memory store is not durable and remains a production-readiness blocker.

## Validation
See `/app/test_reports` for tested scope. All screens above require visual and real-data acceptance before full completion can be claimed.
