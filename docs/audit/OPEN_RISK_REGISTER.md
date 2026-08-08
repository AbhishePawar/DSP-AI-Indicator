# OPEN RISK REGISTER — EPIC-018

| Field | Value |
|---|---|
| Date | 2026-08-03 |
| Product | DSP AI Indicator 2.0.0-rc.1 |
| Decision context | Unrestricted Commercial General Availability |
| Linked matrix | `MASTER_AUDIT_MATRIX.md` |

Risks still open or only partially mitigated. Closed items are omitted (see matrix CLOSED rows).

| Risk ID | Matrix ID | Title | Severity | Likelihood | Impact | Owner domain | Residual mitigation | Blocks GA? |
|---|---|---|---|---|---|---|---|---|
| R-001 | AUD-001 | Billing unavailable / non-purchasable packaging | CRITICAL | Certain | Cannot sell self-serve | Product / Commerce | Honest **Billing provider unavailable.**; Null adapters | **Yes** |
| R-002 | AUD-006 | Live IdP SSO/MFA not integrated | CRITICAL | Certain | Public identity model incomplete | Security / Identity | Ports + Local/Null adapters only | **Yes** |
| R-003 | AUD-002 | Headed Visual QA archive missing | CRITICAL | Certain | Public visual certification false | QA | Matrix documented only | **Yes** |
| R-004 | AUD-004 | Firefox + Safari physical smoke pending | CRITICAL | Certain | Four-browser GA claim unevidenced | QA | Chrome/Edge live PASS | **Yes** |
| R-005 | AUD-003 | Trust ladder not universal | CRITICAL | High | Trust Standard gap on public claim | Trust / UX | Strong on CA + Inst. Reports | **Yes** |
| R-006 | AUD-005/034 | No unrestricted GA commercial policy / board unlock | CRITICAL | Certain | Governance forbids GA language | Release Board | Pilot APPROVED only | **Yes** |
| R-007 | AUD-010 | Soak 8–24h unevidenced | HIGH | High | Latent reliability defects | SRE | PARTIAL ~107m synthetic | Reinforcing |
| R-008 | AUD-011 | Production load unevidenced | HIGH | High | Capacity unknown | SRE / Perf | Synthetic 100–5000 VU | Reinforcing |
| R-009 | AUD-012/031 | Live deploy / BG / canary not executed | HIGH | High | Ops procedures unproven in situ | Release / SRE | Manifests + docs dry-run | Reinforcing |
| R-010 | AUD-020/032 | Managed PITR / restore drill not executed | HIGH | Medium | RPO/RTO claims incomplete | SRE / DB | Scripts + DR docs | Reinforcing |
| R-011 | AUD-013 | Next.js CSP unsafe-inline/eval | HIGH | Medium | XSS residual surface | Security | API CSP hardened | Reinforcing |
| R-012 | AUD-014 | npm 4 high advisories (Next transitive) | HIGH | Medium | Supply-chain / DoS / XSS class | Security | No safe non-breaking force fix | Reinforcing |
| R-013 | AUD-018 | Enterprise actor header spoofable | HIGH | Medium | AuthZ bypass if exposed | Security | Bind to JWT subject | Reinforcing |
| R-014 | AUD-016/017 | Field CWV / full a11y incomplete | HIGH | Medium | Public quality claims weak | QA / Perf | Automation established | Reinforcing |
| R-015 | AUD-015 | Trivy/syft/CycloneDX unavailable here | MEDIUM | Medium | Image/SBOM scan gap | Security / CI | Lite SBOM only | No (process) |
| R-016 | AUD-019 | InMemory job queue | MEDIUM | Medium | Job durability | Platform | Documented RC limit | No for pilot |
| R-017 | AUD-029 | Multi-replica rate limit needs Redis | MEDIUM | Medium | Fairness under scale | Security / SRE | DistributedRateLimiter port | Reinforcing |
| R-018 | AUD-030 | Placeholder support DNS | MEDIUM | Certain | Public support posture incomplete | Ops / GTM | `.example` domains | Reinforcing |
| R-019 | AUD-009 | Durable enterprise store not live-validated | HIGH | Medium | Multi-replica enterprise data risk | Platform | DatabaseEnterpriseStore code exists | Reinforcing |

## Summary

| Class | Count |
|---|---|
| CRITICAL open (GA-blocking) | **6** (R-001…R-006) |
| HIGH open/partial | 8 |
| MEDIUM | 5 |

**Commercial GA cannot proceed while any CRITICAL row remains open.**
