# Release Notes — Web v0.8.0

**Epic:** P1.0 Sprint 9 — Production Readiness & Launch Hardening  
**Audience:** Internal deployment / Private Beta operators

## Summary

DSP Research Platform and Investor Workspace remain functionally complete. This release hardens reliability, accessibility, security posture, observability, and launch gating — without changing investment logic.

## Highlights

- Launch Readiness scoreboard with architecture, performance, a11y, security, testing, docs, and deployment gates
- Client performance sampling (FCP/LCP/CLS/TTI approximations) and documented bundle/lazy/memo audits
- Error boundaries, offline banner, session recovery metadata, 404/500/maintenance surfaces
- CSP Report-Only + standard security headers
- Full QA checklists for smoke, regression, a11y, responsive, security, browsers, and release gates

## What did not change

- Decision / Research / Valuation / Compliance engines
- Knowledge Graph model
- Copilot answer engine
- Portfolio aggregation formulas
- Feature flags & Research Mode terminology
- API contracts

## Upgrade

1. Deploy API RC with security enabled  
2. Deploy `apps/web@0.8.0`  
3. Open `/launch` and confirm score ≥ Private Beta threshold  
4. Run `pytest --import-mode=importlib` (expect GREEN)

## Known follow-ups

See `KNOWN_LIMITATIONS.md` and remaining issues on `/launch`.
