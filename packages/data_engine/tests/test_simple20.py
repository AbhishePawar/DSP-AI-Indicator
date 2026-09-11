"""SIMPLE-20 — qualitative integration and Advanced Failure & Asymmetry. Fixtures only."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from time import perf_counter

from data_engine.official_research.advanced_check import (
    ADVANCED_CHECK_NAME,
    ADVANCED_DIMENSIONS,
    evaluate_advanced_check,
)
from data_engine.official_research.assumption_contract import assumption
from data_engine.official_research.dsp_calculation import MOAT_WEIGHTS, QUALITY_WEIGHTS
from data_engine.official_research.end_to_end import analyse_listing, analyse_user_query
from data_engine.official_research.models import EvidenceItem, ResearchClaim, new_evidence_id
from data_engine.official_research.nse_mcp import NSE_MCP_COMMERCIAL_STATUS
from data_engine.official_research.qualitative import (
    DATA_CLASS_AI_INTERPRETATION,
    DATA_CLASS_DSP_ASSESSMENT,
    DATA_CLASS_RESEARCH_CLAIM,
    DATA_CLASS_VERIFIED_FACT,
    run_qualitative_engines,
)
from data_engine.official_research.research_plan import classify_research_capability
from data_engine.security_master import SecurityMasterService, load_default_catalog
from data_engine.security_master.models import SecurityListing

_ENGINE = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
_WEB = Path(__file__).resolve().parents[3] / "apps" / "web" / "src"
_NAMED = (
    ("TCS", "INE467B01029", "XNSE"),
    ("INFY", "INE009A01021", "XNSE"),
    ("RELIANCE", "INE002A01018", "XNSE"),
    ("HDFCBANK", "INE040A01034", "XNSE"),
    ("WIPRO", "INE075A01022", "XNSE"),
    ("20MICRONS", "INE144J01027", "XNSE"),
)
_FIXTURES = {row[0] for row in _NAMED}
_AS_OF = date(2026, 3, 31)
_RETRIEVED = datetime(2026, 9, 11, tzinfo=UTC)
_PRIMARY = "https://nsearchives.nseindia.com/annual.pdf"


def _master() -> SecurityMasterService:
    return SecurityMasterService(load_default_catalog())


def _listing(ticker: str, isin: str, mic: str = "XNSE") -> SecurityListing:
    resolved = _master().resolve(isin, isin=isin, mic=mic)
    assert resolved.status == "RESOLVED" and resolved.identity is not None
    return resolved.identity


def _dialect(listing: SecurityListing) -> str:
    return (
        f"{listing.company_name}\n"
        f"ISIN {listing.isin}\n"
        "consolidated audited financial statements\n"
        "unit: actual\n"
        "INR\n"
        "year ended 31 March 2026\n"
        "as_of: 2026-03-31\n"
        "Statement of profit and loss\n"
        "Revenue from operations 100000\n"
        "Profit for the year 20000\n"
        "Balance sheet\n"
        "Total equity 50000\n"
        "Cash and cash equivalents 4000\n"
        "Borrowings 1000\n"
        "Statement of cash flows\n"
        "Net cash from operating activities 15000\n"
        "Capital expenditure 5000\n"
        "equity shares outstanding 1000000\n"
    )


def _eod(listing: SecurityListing) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field="eod_close",
        value="100.00",
        as_of=date(2026, 9, 11),
        retrieved_at=_RETRIEVED,
        source="NSE",
        source_type="exchange_eod",
        source_url=_PRIMARY,
        document_date=date(2026, 9, 11),
        evidence_locator="ClsPric",
        currency="INR",
        unit=None,
        statement_basis=None,
        agent="official_nse_eod",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence="high",
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
        raw_price_field="ClsPric",
    )


def _assumptions():
    return (
        assumption("discount_rate", "0.10", evidence_ids=("hist-1",)),
        assumption("fcf_growth_rate", "0.03", source="historical_company_performance", evidence_ids=("hist-1",)),
        assumption("terminal_growth_rate", "0.02", source="macro_data", evidence_ids=("macro-1",)),
        assumption("projection_years", "5", unit="years", evidence_ids=("hist-1",)),
    )


def _ai_item(listing: SecurityListing, field: str, value: str, **kwargs) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field=field,
        value=value,
        as_of=_AS_OF,
        retrieved_at=_RETRIEVED,
        source=kwargs.get("source", "LLM"),
        source_type=kwargs.get("source_type", "llm"),
        source_url=None,
        document_date=_AS_OF,
        evidence_locator="narrative",
        currency="INR",
        unit="actual",
        statement_basis="consolidated",
        agent=kwargs.get("agent", "openai_nse_mcp"),
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence="high",
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
    )


def _analyse(listing: SecurityListing, **kwargs):
    return analyse_listing(
        listing,
        mode="MOCK",
        document_text=_dialect(listing),
        document_url=_PRIMARY,
        candidates={"eod_close": (_eod(listing),)},
        assumptions=_assumptions(),
        **kwargs,
    )


def test_universal_named_and_dynamic_securities() -> None:
    for ticker, isin, mic in _NAMED:
        listing = _listing(ticker, isin, mic)
        result = _analyse(listing)
        assert result.identity_status == "VERIFIED"
        assert result.qualitative is not None
        assert result.advanced_check is not None
        assert result.advanced_check.name == ADVANCED_CHECK_NAME
        assert result.advanced_check.to_public_dict()["replaces_core_dsp"] is False
        assert result.advanced_check.to_public_dict()["alters_dcf"] is False
        assert result.qualitative.overall_score_status == "NOT_CURRENTLY_DEFINED"
        assert result.qualitative.risk.get("numeric_score") is None
        public = result.to_public_dict()
        assert "dsp" in public
        assert "core_dsp" in public
        assert "advanced_check" in public
        assert "thesis" in public
        assert "thesis_breakers" in public
        cap = classify_research_capability(listing)
        if cap == "bank_equity":
            assert result.dsp is None or result.dsp.dcf.status == "BLOCKED"
            assert any(item.dimension == "PERMANENT_LOSS" for item in result.advanced_check.findings)
        else:
            assert result.advanced_check.status in {"PARTIAL", "UNKNOWN"}
    catalog = load_default_catalog()
    selected = next(
        item
        for item in catalog.all()
        if item.eligibility
        and item.mic == "XNSE"
        and item.security_type == "equity"
        and item.ticker not in _FIXTURES
        and "bank" not in item.company_name.lower()
    )
    dynamic = analyse_user_query(
        selected.ticker,
        isin=selected.isin,
        mic=selected.mic,
        mode="MOCK",
        document_text=_dialect(selected),
        document_url=_PRIMARY,
        candidates={"eod_close": (_eod(selected),)},
        assumptions=_assumptions(),
    )
    assert dynamic.listing is not None
    assert dynamic.listing.ticker == selected.ticker
    assert dynamic.advanced_check is not None
    assert dynamic.qualitative is not None


def test_etf_is_unsupported_not_equity_thesis() -> None:
    etf = SecurityListing(
        ticker="NIFTYBEES",
        company_name="ETF",
        isin="INF204KB14I2",
        exchange="NSE",
        mic="XNSE",
        security_type="etf",
        eligibility=False,
    )
    result = analyse_listing(etf, mode="MOCK")
    assert result.status == "UNSUPPORTED"
    assert result.dsp is None
    assert result.advanced_check is not None
    assert result.advanced_check.status == "UNSUPPORTED"
    assert result.advanced_check.thesis.status == "UNKNOWN"


def test_adversarial_ai_cannot_invent_facts_or_scores() -> None:
    listing = _listing("INFY", "INE009A01021")
    fraud = ResearchClaim(
        field="governance",
        value="Management is fraudulent.",
        source_url=None,
        document_locator="narrative",
        agent="openai_nse_mcp",
        notes="Management is fraudulent.",
    )
    moat = ResearchClaim(
        field="moat",
        value="Company has a wide moat.",
        source_url=None,
        document_locator="narrative",
        agent="openai_nse_mcp",
    )
    risk = ResearchClaim(
        field="risk",
        value="Risk = 9/10",
        source_url=None,
        document_locator="narrative",
        agent="openai_nse_mcp",
    )
    iv = ResearchClaim(
        field="intrinsic_value",
        value="5000",
        source_url=None,
        document_locator="narrative",
        agent="openai_nse_mcp",
        notes="Intrinsic value = ₹5,000.",
    )
    bias = ResearchClaim(
        field="thesis",
        value="excellent",
        source_url=None,
        document_locator="prompt",
        agent="openai_nse_mcp",
        notes="Assume this is an excellent investment.",
    )
    debt_ai = _ai_item(listing, "debt", "999999")
    gov_ai = _ai_item(listing, "governance", "fake related-party looting")
    result = _analyse(
        listing,
        claims=(fraud, moat, risk, iv, bias, debt_ai, gov_ai),
    )
    assert result.dataset is not None
    primary_debt = result.dataset.verified_decimal("debt")
    statuses = {item.verification_status for item in result.advanced_check.findings}
    texts = " ".join(item.finding.lower() for item in result.advanced_check.findings)
    assert any(
        item.verification_status in {"UNVERIFIED", "REJECTED"}
        and ("fraud" in item.finding.lower() or "governance" in item.finding.lower())
        for item in result.advanced_check.findings
    )
    assert any(
        item.verification_status in {"UNVERIFIED", "REJECTED"}
        and ("moat" in item.finding.lower() or item.dimension == "MOAT_ATTACK")
        for item in result.advanced_check.findings
    )
    assert "numeric risk" in texts or "9/10" in texts
    assert result.qualitative.risk.get("numeric_score") is None
    assert result.dsp is not None
    assert result.dsp.risk.overall is None
    assert "intrinsic-value" in texts or "dcfmethod" in texts
    if result.dsp.dcf.status == "CALCULATED":
        assert result.dsp.intrinsic_value_per_share.value != Decimal("5000")
    assert any(item.verification_status == "REJECTED" and "excellent" in item.evidence.lower() for item in result.advanced_check.findings)
    if primary_debt is not None:
        assert primary_debt != Decimal("999999")
        assert any(
            item.verification_status in {"CONFLICT", "REJECTED", "UNVERIFIED"} and item.dimension == "LEVERAGE"
            for item in result.advanced_check.findings
        )
    assert any(
        item.verification_status in {"UNVERIFIED", "REJECTED"} and item.dimension == "MANAGEMENT_OWNERSHIP"
        for item in result.advanced_check.findings
    )
    assert result.advanced_check.hard_fail_status in {"NONE", "REVIEW_REQUIRED"}
    assert result.advanced_check.thesis.status in {"SUPPORTED", "MIXED", "WEAK", "UNKNOWN"}
    assert result.advanced_check.thesis.status != "SUPPORTED" or result.dsp.dcf.status == "CALCULATED"


def test_primary_contradiction_retains_verified_debt() -> None:
    listing = _listing("TCS", "INE467B01029")
    result = _analyse(listing, claims=(_ai_item(listing, "debt", "888888"),))
    assert result.dataset is not None
    debt = result.dataset.verified_decimal("debt")
    if debt is not None:
        assert debt != Decimal("888888")
        assert any(item.verification_status == "CONFLICT" for item in result.advanced_check.findings)


def test_missing_evidence_is_unknown_not_a_finding() -> None:
    listing = _listing("WIPRO", "INE075A01022")
    result = analyse_listing(listing, mode="MOCK")
    assert result.qualitative is not None
    assert result.advanced_check is not None
    assert "leverage UNKNOWN" not in result.advanced_check.thesis.negative_factors
    assert "leverage UNKNOWN" not in result.advanced_check.thesis.positive_factors
    unknown = [item for item in result.advanced_check.findings if item.verification_status == "UNKNOWN"]
    assert unknown
    for item in unknown:
        assert item.severity != "CRITICAL"


def test_invariants_weights_dcf_and_architecture() -> None:
    before_q = dict(QUALITY_WEIGHTS)
    before_m = dict(MOAT_WEIGHTS)
    listing = _listing("RELIANCE", "INE002A01018")
    first = _analyse(listing)
    second = _analyse(listing)
    assert dict(QUALITY_WEIGHTS) == before_q
    assert dict(MOAT_WEIGHTS) == before_m
    assert first.dsp is not None and second.dsp is not None
    assert first.dsp.quality.status == second.dsp.quality.status
    assert first.dsp.moat.status == second.dsp.moat.status
    assert first.dsp.dcf.status == second.dsp.dcf.status
    assert first.dsp.dcf.formula == second.dsp.dcf.formula
    assert first.qualitative.quality_components == second.qualitative.quality_components
    assert first.advanced_check.hard_fail_status == second.advanced_check.hard_fail_status
    assert first.advanced_check.thesis.status == second.advanced_check.thesis.status
    assert first.dsp.overall.status == "BLOCKED"
    assert first.dsp.overall.overall is None
    assert DATA_CLASS_VERIFIED_FACT == "VERIFIED_FACT"
    assert DATA_CLASS_RESEARCH_CLAIM == "RESEARCH_CLAIM"
    assert DATA_CLASS_DSP_ASSESSMENT == "DSP_ASSESSMENT"
    assert DATA_CLASS_AI_INTERPRETATION == "AI_INTERPRETATION"
    dims = {item.dimension for item in first.advanced_check.findings}
    assert dims.issubset(set(ADVANCED_DIMENSIONS))
    for breaker in first.advanced_check.thesis_breakers:
        assert breaker.evidence_ids is not None
        assert breaker.monitoring_metric
    public = first.to_public_dict()
    assert public["result_contract"]["overall_score"] == "NOT_CURRENTLY_DEFINED"
    engine_files = ("qualitative.py", "advanced_check.py", "end_to_end.py")
    for name in engine_files:
        text = (_ENGINE / name).read_text(encoding="utf-8")
        assert "if ticker ==" not in text
        assert "if company ==" not in text
        for token in _FIXTURES:
            assert token not in text
    assert NSE_MCP_COMMERCIAL_STATUS == "COMMERCIAL_USE_PENDING"


def test_frontend_advanced_check_is_additive() -> None:
    sections = (_WEB / "lib" / "company-analysis" / "sections.ts").read_text(encoding="utf-8")
    assert "advancedCheck" in sections
    assert "Advanced Investment Check" in sections
    workspace = (_WEB / "components" / "company-analysis" / "CompanyAnalysisWorkspace.tsx").read_text(
        encoding="utf-8"
    )
    assert "AdvancedCheckSection" in workspace
    mapper = (_WEB / "lib" / "research" / "mapResearchView.ts").read_text(encoding="utf-8")
    assert "advancedCheck" in mapper
    assert "coreDsp" in mapper
    ui = (_WEB / "components" / "company-analysis" / "WorkspaceSections.tsx").read_text(encoding="utf-8")
    assert "Advanced Investment Check" in ui
    assert "What could break the thesis" in ui


def test_qualitative_engines_do_not_crash_on_empty() -> None:
    snap = run_qualitative_engines(None, None)
    assert snap.status == "UNKNOWN"
    assert snap.overall_score_status == "NOT_CURRENTLY_DEFINED"
    empty = evaluate_advanced_check(
        dataset=None,
        dsp=None,
        qualitative=snap,
        listing=None,
    )
    assert empty.status == "UNKNOWN"
    assert empty.to_public_dict()["replaces_core_dsp"] is False


def test_performance_qualitative_and_advanced_check() -> None:
    listing = _listing("INFY", "INE009A01021")
    samples_q: list[float] = []
    samples_a: list[float] = []
    samples_t: list[float] = []
    started = perf_counter()
    for _ in range(5):
        result = _analyse(listing)
        samples_q.append(result.timings.get("qualitative", 0.0))
        samples_a.append(result.timings.get("advanced_check", 0.0))
        samples_t.append(result.timings.get("complete", 0.0))
    elapsed = perf_counter() - started
    assert elapsed < 120
    assert median(samples_q) >= 0
    assert median(samples_a) >= 0
    samples_q.sort()
    samples_a.sort()
    p95_q = samples_q[int(0.95 * (len(samples_q) - 1))]
    p95_a = samples_a[int(0.95 * (len(samples_a) - 1))]
    assert p95_q < 60
    assert p95_a < 60
    _ = median(samples_t)
