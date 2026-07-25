# Business Quality

Canonical **Business Quality** intelligence for DSP AI Indicator (**Phase 3**).

Version: **0.7.0**

- **F3.1:** Framework
- **F3.2:** Earnings Quality Intelligence
- **F3.3:** Capital Allocation Intelligence
- **F3.4:** Business Characteristics Intelligence
- **F3.5:** Competitive Position Indicators
- **F3.6:** Business Quality Engine
- **F3.7:** Business Quality Aggregator (**Phase 3 complete**)

Consumes **`FinancialAnalysis`** (engine) and packages **`BusinessQualityAnalysis`** (aggregator).

Primary entries:
- `BusinessQualityEngine.analyze()` — compose EQ + CA + BC + CP
- `BusinessQualityAggregator.aggregate()` — consumer report packaging

See `docs/F3_SPRINT*.md`.
