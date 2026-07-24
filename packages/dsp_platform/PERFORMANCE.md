# DSP Platform — Performance Observations (Sprint 7.3)

Measured offline with fake market / bridges / engines through the real
`InvestmentAnalysisService` + committee + recommendation mapper.
No live HTTP. Validated by `packages/dsp_platform/tests/test_performance.py`
on the Sprint 7.3 green suite (Windows / Python 3.13).

| Metric | Observed (typical) | Enforced bound |
|---|---|---|
| Platform startup (DI wiring of fakes) | well under 100 ms | &lt; 2.0 s |
| Single `analyze()` latency | well under 50 ms | &lt; 1.0 s |
| Single `analyze_decision_pack()` latency | pipeline + O(members) DI rules | same bound; DI overhead negligible vs engines |
| Peak traced memory (one analyze) | well under 10 MiB | &lt; 50 MiB |

Decision Intelligence is pure in-memory rule evaluation over an existing
`CommitteeReport` + `Recommendation`. It does not re-run engines. Expected
incremental cost is microseconds–low milliseconds relative to orchestration.

Full `dsp_platform` suite (47 tests including E2E + perf) completed in
~0.22 s wall time in the integration run — no regressions found.
No optimization work was required.

Re-run:

```powershell
.\.venv\Scripts\python.exe -m pytest packages/dsp_platform/tests/test_performance.py -v
```
