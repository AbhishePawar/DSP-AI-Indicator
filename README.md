# DSP AI Indicator

**Complex Analysis. Simple Decisions.**  
Professional Investment Research for Everyone.

Explainable AI Investment Research Platform — **not** a stock tip service.

**Backend API:** `v1.0.0` · **Platform:** `dsp_platform 2.0.0` · **Web:** `2.0.0` · **Milestones:** `v2.0.0-financial-intelligence` · `v3.0.0-business-quality` · **Product epic:** [PR1.0](docs/PR1_0_PRODUCT_STRATEGY_AND_COMPLIANCE.md) (Research Mode default)  
**Vision:** [PRODUCT_VISION.md](docs/PRODUCT_VISION.md) · **Engineering status:** [docs/ENGINEERING_STATUS.md](docs/ENGINEERING_STATUS.md) · **Living status:** [docs/DSP_STATUS.md](docs/DSP_STATUS.md) · **Architecture Bible:** [docs/ARCHITECTURE_BIBLE.md](docs/ARCHITECTURE_BIBLE.md) · **Core values CV-001…CV-010:** [docs/CORE_VALUES.md](docs/CORE_VALUES.md) · **Research Standards RS-001…RS-010:** [docs/RESEARCH_STANDARDS.md](docs/RESEARCH_STANDARDS.md) · **Institutional dashboard:** [docs/DASHBOARD_ARCHITECTURE.md](docs/DASHBOARD_ARCHITECTURE.md) · **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md) · **Package ownership:** [docs/PACKAGE_OWNERSHIP_MATRIX.md](docs/PACKAGE_OWNERSHIP_MATRIX.md) · **Release engineering:** [docs/RELEASE_ENGINEERING.md](docs/RELEASE_ENGINEERING.md)

Institutional AI Investment Research Platform.

**Status:** ASI **CLOSED**. FEATURE-001–004 complete (Moat, Management, Financial Strength, Earnings Quality). Await approval for next feature. See [docs/FEATURE_004_EARNINGS_QUALITY.md](docs/FEATURE_004_EARNINGS_QUALITY.md).

## Public entry point

External applications should import **`dsp_platform`** and **`contracts`** only:

```python
from datetime import date

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from dsp_platform import (
    DSPPlatform,
    Environment,
    PlatformConfig,
    PlatformHealthService,
    PlatformSecrets,
    load_platform_config,
)

instrument = Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")

config = PlatformConfig(
    environment=Environment.PRODUCTION,
    secrets=PlatformSecrets(fred_api_key="…"),  # inject — never hardcode
)
# Or: config = load_platform_config()  # optional env loader

platform = DSPPlatform.from_config(config)
request = platform.make_request(instrument, date(2024, 1, 1), date(2024, 6, 30))

# Preferred investor artifact
pack = platform.analyze_decision_pack(request)
# pack.recommendation / pack.brief / pack.assurance

# Backward compatible
recommendation = platform.analyze(request)

health = PlatformHealthService(config=config, platform=platform).check()
assert health.ready
```

## Execution pipeline

```
Application
  → DSPPlatform
  → InvestmentAnalysisService (orchestration)
  → engines + AI committee
  → RecommendationMapper
  → Decision Intelligence (Brief + Assurance)
  → Decision Pack  (preferred)
  → contracts.Recommendation  (compat via analyze())
```

## Architecture (dependency direction)

```
contracts ← core ← data_engine
                 ← dsp / fundamental / economic
                 ← snapshot_bridge
                 ← ai_committee
                 ← recommendation
                 ← decision_intelligence
                 ← universe
                 ← orchestration
                 ← dsp_platform   (public façade)
```

**Application import rule:** `dsp_platform` + `contracts` only.
Internal packages must not be imported by apps (enforced via
`assert_application_imports` / platform tests).

## Packages

| Package | Role |
|---|---|
| `contracts` | Shared kernel |
| `core` | Validation, registries, exceptions |
| `data_engine` | Provider adapters + normalization |
| `snapshot_bridge` | Statements/series → engine snapshots |
| `dsp` | Indicator engine |
| `fundamental` | Fundamental engine |
| `economic` | Economic engine |
| `ai_committee` | Multi-member deliberation |
| `orchestration` | Thin pipeline |
| `recommendation` | Committee report → Recommendation |
| `decision_intelligence` | Decision Brief + Assurance → Decision Pack |
| `universe` | Investment universe + multi-stock Decision Pack aggregation |
| `industry` | Industry Identity + taxonomy mappings (AIMF) |
| `dsp_platform` | Public façade, config, health, gates |
| `valuation` | Valuation engine — Phase 1 Suite complete incl. Overall Aggregator (`0.12.0`) |
| `financial` | Canonical Financial Statement Domain + full F2.1–F2.7 Intelligence Aggregator — Phase 2 complete (`0.7.0`) |
| `business_quality` | Business Quality Intelligence — Phase 3 complete F3.1–F3.7 (`0.7.0`) |

## Health & integration

- Offline E2E tests cover BUY / SELL / HOLD, partial data, failures, disagreement, determinism.
- `PlatformHealthService` validates config, features, provider registration, and wiring — no network.
- See [packages/dsp_platform/README.md](packages/dsp_platform/README.md) and [PERFORMANCE.md](packages/dsp_platform/PERFORMANCE.md).

## Documentation

- [Architecture specification](docs/DSP_AI_INDICATOR_ARCHITECTURE.md)
- [Decision Pack](docs/DECISION_PACK.md)
- [B3 Decision Pack validation](docs/B3_DECISION_PACK_VALIDATION.md)
- [C1 Multi-stock foundation](docs/C1_MULTI_STOCK_FOUNDATION.md)
- [C2 AIMF design (audit + gaps)](docs/C2_AIMF_DESIGN.md)
- [C2 AIMF architecture freeze](docs/C2_AIMF_ARCHITECTURE_FREEZE.md)
- [C2.1 Industry Identity](docs/C2_1_INDUSTRY_IDENTITY.md)
- [C2.2 Investment Characteristics](docs/C2_2_INVESTMENT_CHARACTERISTICS.md)
- [C2.3 Industry Methodology](docs/C2_3_INDUSTRY_METHODOLOGY.md)
- [C2.4 Peer Eligibility](docs/C2_4_PEER_ELIGIBILITY.md)
- [C2.5 Qualitative Comparison](docs/C2_5_COMPARISON_ENGINE.md)
- [C3.0 Industry Evidence Framework (design review)](docs/C3_0_INDUSTRY_EVIDENCE_FRAMEWORK.md)
- [C3.0A Industry Evidence Architecture Freeze](docs/C3_0A_INDUSTRY_EVIDENCE_ARCHITECTURE_FREEZE.md)
- [C3.1 Industry Evidence Registry](docs/C3_1_INDUSTRY_EVIDENCE_REGISTRY.md)
- [C3.2 Industry Evidence Applicability](docs/C3_2_INDUSTRY_EVIDENCE_APPLICABILITY.md)
- [C3.3 Industry Evidence Providers](docs/C3_3_INDUSTRY_EVIDENCE_PROVIDERS.md)
- [C3.4 Industry Evidence Interpreters](docs/C3_4_INDUSTRY_EVIDENCE_INTERPRETERS.md)
- [C3.5 Industry Evidence Bundles](docs/C3_5_INDUSTRY_EVIDENCE_BUNDLES.md)
- [C3.6 DecisionPack Evidence Integration](docs/C3_6_DECISIONPACK_EVIDENCE_INTEGRATION.md)
- [C3.7 Comparison Evidence Integration](docs/C3_7_COMPARISON_EVIDENCE_INTEGRATION.md)
- [C4.0 Portfolio Intelligence Design](docs/C4_0_PORTFOLIO_INTELLIGENCE_DESIGN.md)
- [C4.0A Portfolio Intelligence Architecture Freeze](docs/C4_0A_PORTFOLIO_INTELLIGENCE_ARCHITECTURE_FREEZE.md)
- [C4.1 Portfolio Domain Models](docs/C4_1_PORTFOLIO_DOMAIN_MODELS.md)
- [C4.2 Portfolio Assembler](docs/C4_2_PORTFOLIO_ASSEMBLER.md)
- [C4.3 Portfolio Qualitative Analysis](docs/C4_3_PORTFOLIO_QUALITATIVE_ANALYSIS.md)
- [C4.4 Portfolio Citation Enrichment](docs/C4_4_PORTFOLIO_CITATION_ENRICHMENT.md)
- [C4.5 Portfolio Validation & Architecture Freeze](docs/C4_5_PORTFOLIO_VALIDATION_AND_FREEZE.md)
- [C4.6 Portfolio Monitoring](docs/C4_6_PORTFOLIO_MONITORING.md)
- [E0.0 Risk Intelligence Design](docs/E0_0_RISK_INTELLIGENCE_DESIGN.md)
- [E0.0A Risk Intelligence Architecture Freeze](docs/E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md)
- [E1.0 Risk Domain Models](docs/E1_0_RISK_DOMAIN_MODELS.md)
- [E1.1 Risk Assembler](docs/E1_1_RISK_ASSEMBLER.md)
- [E1.2 Risk Analyzer](docs/E1_2_RISK_ANALYZER.md)
- [C2 InvestmentCharacteristics decision](docs/C2_INVESTMENT_CHARACTERISTICS.md)
- [Decision Intelligence package](packages/decision_intelligence/README.md)
- [Typing policy (mypy)](docs/TYPING.md)
- [Platform façade](packages/dsp_platform/README.md)

## Development

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\mypy.exe
```

Static typing (Phase A5) covers `contracts`, `core`, `orchestration`, and
`dsp_platform`. See [docs/TYPING.md](docs/TYPING.md).
