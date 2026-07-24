# Performance Report — Web 0.8.0

## Sampling

`/launch/performance` reads browser Performance APIs when available:

- FCP (paint)  
- LCP (observer)  
- CLS (layout-shift)  
- TTI approx (domInteractive)  
- Route timing (navigation)  
- Memory (Chromium `performance.memory`)  

INP and React render counts remain manual/DevTools.

## Audits completed (presentation)

- Route-level code splitting via App Router  
- Copilot lazy import  
- Memoized heavy workspaces  
- `next/font` with `display: swap`  
- Documented bundle analyzer script stub  

## Targets

| Metric | Target |
|--------|--------|
| FCP | < 1800 ms |
| LCP | < 2500 ms |
| INP | < 200 ms |
| CLS | < 0.1 |
| Soft route | < 1000 ms |

## Follow-up

Wire Lighthouse CI budgets in the release pipeline.
