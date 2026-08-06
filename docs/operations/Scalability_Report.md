# Scalability Report (EPIC-017)

## Current scaling model

| Tier | Scale unit | Mechanism |
|---|---|---|
| API | Pod / container | HPA on CPU/memory; rolling deploy |
| Web | Pod / container | Replica count; CDN optional in front |
| Postgres | Vertical + managed HA | Prefer cloud primary/replica; no schema redesign |
| Redis | Managed cluster / replica | Cache + sessions + rate limits + locks |
| Jobs | Worker replicas (future) | `JobQueuePort` abstraction; in-memory until worker epic |

## Horizontal readiness

**Ready**

- Stateless API/Web containers (temp on emptyDir / volume)
- Health/readiness probes for orchestration
- Redis-backed ports for shared rate limits/sessions (when `DSP_REDIS_URL` set)
- Compose + k8s + Helm packaging

**Constrained**

- In-memory job queue fallback (not multi-node fair)
- Single StatefulSet Postgres reference (not HA)
- Synthetic load only in this epic — no 5k-user live proof

## Capacity planning (guidance, not guarantee)

| Concurrent users (order) | Suggested API replicas | Notes |
|---|---|---|
| ≤ 100 | 2 | Compose / small cluster |
| ~500 | 3–4 | Watch DB connections |
| ~1000 | 4–6 + managed Redis/PG | Load-test staging |
| ~5000 | 8–12 + read replica consideration | Requires live k6/Locust evidence |

These are **planning heuristics** derived from HPA settings and synthetic results — recalibrate after staging soak.

## Bottleneck map

```
Clients → Ingress/Caddy → Web / API
                          API → Redis (rate limit, session)
                          API → Postgres (identity, enterprise)
                          API → External market/fundamentals providers
```

Hottest production risks: DB connections, provider latency, Redis eviction under session growth.

## Scaling playbook

1. Confirm dependency SLOs (Postgres CPU, Redis memory)
2. Raise API `maxReplicas` / HPA carefully
3. Separate read-heavy reporting later (out of scope) without engine redesign
4. Canary before large replica jumps

## Verdict

Platform packaging is **horizontally oriented** for API/Web. Data plane HA depends on managed services. Scalability posture **improved for enterprise ops**; commercial capacity claims require measured staging evidence.
