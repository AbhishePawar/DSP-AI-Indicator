# Release Notes — DSP AI Indicator Version 2.0 RC (`2.0.0-rc.1`)

| Field | Value |
|---|---|
| Product version | **2.0.0-rc.1** |
| Channel | `rc` |
| API contract | `v1.0.0` (behaviour frozen) |
| Platform package | `dsp_platform@2.0.0` |
| Web package | `dsp-web@2.0.0-rc.1` |
| Programme | EPS-003 — Version 2.0 Release Candidate Hardening |
| Date | 2026-08-02 |
| Commercial GA | **Not approved** |

---

## Highlights

- Feature-frozen **Release Candidate** suitable for independent audit and deployment planning.
- Version metadata synchronized (`VERSION`, manifests, web foundation, env templates, README).
- Enterprise Commercial Platform foundation from EPS-002 included (orgs, teams, RBAC, licensing, Null billing, portal, ops, audit, API keys).
- Security hygiene: CSP `object-src 'none'`; API `X-Permitted-Cross-Domain-Policies: none`; env example guidance.
- Stale commercial onboarding test no longer requires silent `AAPL` demo ticker copy (GA-C6 hygiene).
- RC documentation pack under `docs/releases/` (RC4 report, limitations, checklist, freeze, debt, roadmap).

## What did not change

- Valuation, Business Quality, Management, Moat, Risk engines  
- AI Committee, Explainability, Research Intelligence, Comparison, Portfolio logic  
- REP-002 ontology behaviour, Trust Standard presentation rules, GOV-001  
- Thin-client rule (no browser analytical engines)  
- Historical certification documents (RC3 / GA-005 decisions not rewritten)

## Known constraints (summary)

- Null billing only — invoices show **Billing unavailable.**  
- In-memory enterprise store — not multi-replica durable  
- Admin-provisioned / Research Mode pilot posture retained for commercial messaging  
- Commercial GA conditions from GA-005 remain open  

Full detail: [`RC4_KNOWN_LIMITATIONS.md`](./RC4_KNOWN_LIMITATIONS.md).

## Upgrade / deploy notes

1. Set product version / image tags to `2.0.0-rc.1`.  
2. Copy `.env.production.example` → `.env.production`; fill secrets from a secret manager.  
3. Treat enterprise APIs as **foundation** — do not enable public self-serve billing claims.  
4. Execute [`RC4_PRODUCTION_CHECKLIST.md`](./RC4_PRODUCTION_CHECKLIST.md) before staging promote.  
5. Keep messaging as **Version 2.0 Release Candidate / Research Mode** — not Commercial GA.

## Decision

**RELEASE CANDIDATE** — proceed to independent audit.  
**Commercial GA:** still **NOT APPROVED**.

Authority: [`RC4_RELEASE_CANDIDATE_REPORT.md`](./RC4_RELEASE_CANDIDATE_REPORT.md).
