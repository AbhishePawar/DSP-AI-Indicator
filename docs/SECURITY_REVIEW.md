# Security Review — Web 0.8.0

## Scope

Frontend Private Beta hardening. Backend security remains API-owned (`DSP_ENABLE_SECURITY`).

## Findings

| Area | Status | Notes |
|------|--------|-------|
| XSS | Pass | Prefer text nodes; no product `dangerouslySetInnerHTML` |
| HTML sanitize | Pass | `escapeHtml` helper available |
| Clipboard | Pass | No secret clipboard writes |
| Downloads | Pass | Filename sanitization on export |
| Markdown | Pass | Downloaded, not executed as HTML by default |
| CSP | Warn | Report-Only headers shipped — enforce later |
| Dependencies | Pending | `npm audit` in CI |
| Console logs | Warn | Boundaries log messages only — avoid tokens in errors |
| Artifacts | Pass | No debugger leftovers in Sprint 9 |

## Recommendations

1. Promote CSP to enforcing after violation review  
2. Add Dependabot/npm audit gate  
3. Ensure thrown errors never include access tokens  
