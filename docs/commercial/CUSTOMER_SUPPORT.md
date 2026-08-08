# Customer Support Model — DSP AI Indicator

**Epic:** P6.1

## Channels

| Channel | Use |
|---|---|
| Email `support@dsp-ai-indicator.example` | General support |
| Email `security@dsp-ai-indicator.example` | Security incidents / vulnerabilities |
| Email `sales@dsp-ai-indicator.example` | Pricing, trials, Enterprise |
| In-app Feedback | Bugs / feature requests (no secrets) |
| Docs `/docs` | Knowledge base |
| Status page | Operator-managed (external) |

In-product path: `/docs/support`.

## Hours

- **Research / Professional:** Mon–Fri 09:00–18:00 IST  
- **Enterprise:** Per contract (may include extended coverage)

## Severity matrix

| Severity | Definition | Ack target | Resolution target* |
|---|---|---|---|
| S1 Critical | Service down, data breach, auth outage | ≤1 hour | Continuous effort |
| S2 High | Major feature unusable for many users | ≤4 business hours | ≤2 business days |
| S3 Medium | Partial degradation / workaround exists | ≤1 business day | ≤5 business days |
| S4 Low | Questions, cosmetic, documentation | ≤2 business days | Best effort |

\*Enterprise SLAs may tighten; Research is best-effort.

## Escalation

1. User → Support email or Feedback  
2. L1 triage (severity + reproduce)  
3. L2 engineering (on-call via incident runbook)  
4. Security path for S1 security → `security@` + security incident runbook  
5. Product/legal for compliance / advice-boundary questions

## Knowledge base

- `/docs/quick-start` · `/docs/user-guide` · `/docs/faq` · `/docs/pricing` · `/docs/support`  
- Repo: `docs/USER_GUIDE_v1.0.0.md`, `docs/FAQ_CLOSED_BETA_RC.md`, `docs/P6_1_COMMERCIAL_READINESS.md`
