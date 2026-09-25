"""SIMPLE-26 — universal DCF assumption research and validation. Fail-closed is success."""

from __future__ import annotations

import ast
import importlib.util
import inspect
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from time import perf_counter

from api_platform.api.composition_schemas import AnalyseRequest
from data_engine.official_research.assumption_contract import (
    DATA_CLASS_ASSUMPTION,
    DATA_CLASS_DERIVED,
    DATA_CLASS_FACT,
    assumption,
    classify_data_class,
)
from data_engine.official_research.assumption_research import (
    ASSUMPTION_FRESHNESS_DAYS,
    VALIDATOR_VERSION,
    HistoricalObservation,
    dcf_assumption_candidate,
    research_dcf_assumptions,
)
from data_engine.official_research.assumption_validator import refuse_ai_fact
from data_engine.official_research.dsp_calculation import (
    MOS_FORMULA,
    describe_dcf_blockers,
    run_dsp_calculations,
)
from data_engine.official_research.end_to_end import analyse_listing
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import EvidenceItem, new_evidence_id
from data_engine.official_research.orchestrator import ResearchOrchestrator
from data_engine.official_research.research_plan import classify_research_capability
from data_engine.security_master import SecurityMasterService, load_default_catalog
from data_engine.security_master.models import SecurityListing
from llm_adapters.config import load_llm_config

_ENGINE = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
_NAMED = (
    ("TCS", "INE467B01029", "XNSE"),
    ("INFY", "INE009A01021", "XNSE"),
    ("RELIANCE", "INE002A01018", "XNSE"),
    ("WIPRO", "INE075A01022", "XNSE"),
    ("20MICRONS", "INE144J01027", "XNSE"),
    ("21STCENMGM", "INE253B01015", "XNSE"),
)
_NOW = datetime(2026, 9, 11, tzinfo=UTC)
_AS_OF = date(2026, 3, 31)


def _simple18():
    path = Path(__file__).with_name("test_simple18.py")
    spec = importlib.util.spec_from_file_location("simple18_helpers_s26", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _master() -> SecurityMasterService:
    return SecurityMasterService(load_default_catalog())


def _listing(ticker: str, isin: str, mic: str = "XNSE") -> SecurityListing:
    resolved = _master().resolve(isin, isin=isin, mic=mic)
    assert resolved.status == "RESOLVED" and resolved.identity is not None
    return resolved.identity


def _pack():
    return (
        assumption("discount_rate", "0.10", source="primary_research", evidence_ids=("ev-wacc",)),
        assumption(
            "fcf_growth_rate",
            "0.04",
            source="historical_company_performance",
            evidence_ids=("ev-g",),
        ),
        assumption("terminal_growth_rate", "0.03", source="macro_data", evidence_ids=("ev-tg",)),
        assumption("projection_years", "5", unit="years", evidence_ids=("ev-y",)),
    )


def _history(listing: SecurityListing, *, fcf_positive: bool = True) -> tuple[HistoricalObservation, ...]:
    cfo_end = Decimal("20") if fcf_positive else Decimal("4")
    capex_end = Decimal("5") if fcf_positive else Decimal("10")
    return (
        HistoricalObservation(
            field="cfo", value=Decimal("16"), as_of=date(2024, 3, 31),
            isin=listing.isin, mic=listing.mic, currency="INR", unit="actual",
            statement_basis="consolidated", evidence_id="cfo-24",
        ),
        HistoricalObservation(
            field="cfo", value=cfo_end, as_of=_AS_OF,
            isin=listing.isin, mic=listing.mic, currency="INR", unit="actual",
            statement_basis="consolidated", evidence_id="cfo-26",
        ),
        HistoricalObservation(
            field="capex", value=Decimal("4"), as_of=date(2024, 3, 31),
            isin=listing.isin, mic=listing.mic, currency="INR", unit="actual",
            statement_basis="consolidated", evidence_id="capex-24",
        ),
        HistoricalObservation(
            field="capex", value=capex_end, as_of=_AS_OF,
            isin=listing.isin, mic=listing.mic, currency="INR", unit="actual",
            statement_basis="consolidated", evidence_id="capex-26",
        ),
        HistoricalObservation(
            field="revenue", value=Decimal("80"), as_of=date(2024, 3, 31),
            isin=listing.isin, mic=listing.mic, currency="INR", unit="actual",
            statement_basis="consolidated", evidence_id="rev-24",
        ),
        HistoricalObservation(
            field="revenue", value=Decimal("100"), as_of=_AS_OF,
            isin=listing.isin, mic=listing.mic, currency="INR", unit="actual",
            statement_basis="consolidated", evidence_id="rev-26",
        ),
    )


def test_no_company_specific_assumption_branches() -> None:
    source = (_ENGINE / "assumption_research.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned = {row[0] for row in _NAMED} | {"HDFCBANK", "NIFTYBEES"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and comparator.value in banned:
                    raise AssertionError(f"company-specific branch on {comparator.value}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in banned:
            raise AssertionError(f"ticker literal {node.value} in assumption research")


def test_dcf_contract_required_optional_and_defaults() -> None:
    assert classify_data_class("discount_rate") == DATA_CLASS_ASSUMPTION
    assert classify_data_class("wacc") == DATA_CLASS_ASSUMPTION
    assert classify_data_class("fcf_growth_rate") == DATA_CLASS_ASSUMPTION
    assert classify_data_class("terminal_growth_rate") == DATA_CLASS_ASSUMPTION
    assert classify_data_class("projection_years") == DATA_CLASS_ASSUMPTION
    assert classify_data_class("revenue") == DATA_CLASS_FACT
    assert classify_data_class("fcf") == DATA_CLASS_DERIVED
    source = (_ENGINE / "dsp_calculation.py").read_text(encoding="utf-8")
    assert "years = 5 if years_row is None" not in source
    assert "projection_years is an explicit assumption" in source
    assert "0.10" not in source.split("def _run_dcf")[1].split("def ")[0]
    assert MOS_FORMULA == (
        "(intrinsic_value_per_share - market_price_per_share) / intrinsic_value_per_share"
    )


def test_universal_named_dynamic_bank_etf_and_history() -> None:
    s18 = _simple18()
    catalog = load_default_catalog()
    dynamic = next(
        item
        for item in catalog.all()
        if item.eligibility
        and item.mic == "XNSE"
        and item.security_type == "equity"
        and item.ticker not in {row[0] for row in _NAMED}
        and "bank" not in item.company_name.lower()
    )
    for ticker, isin, mic in _NAMED + ((dynamic.ticker, dynamic.isin, dynamic.mic),):
        listing = _listing(ticker, isin, mic)
        dataset = s18._happy(listing)
        empty = research_dcf_assumptions(dataset, listing, now=_NOW)
        assert empty.wacc_status == "UNKNOWN"
        assert empty.terminal_growth_status == "UNKNOWN"
        assert empty.dcf_eligibility == "DCF_BLOCKED"
        assert empty.ai_status == "NOT_CONFIGURED"
        accepted = research_dcf_assumptions(dataset, listing, proposals=_pack(), now=_NOW)
        assert accepted.status == "ACCEPTED"
        assert accepted.dcf_eligibility == "ELIGIBLE"
        assert all(
            item.accepted_by == VALIDATOR_VERSION
            for item in accepted.candidate_assumptions
            if item.status == "ACCEPTED"
        )
        dsp = run_dsp_calculations(dataset, assumptions=accepted.accepted_pack, listing=listing)
        assert dsp.dcf.status == "CALCULATED"
        assert dsp.dcf.formula_version == "valuation.methods.dcf"
        assert dsp.margin_of_safety.formula == MOS_FORMULA
    bank = _listing("HDFCBANK", "INE040A01034")
    bank_result = research_dcf_assumptions(s18._happy(bank), bank, proposals=_pack(), now=_NOW)
    assert bank_result.dcf_eligibility == "BANK_VALUATION_METHOD_REQUIRED"
    assert bank_result.accepted_pack == ()
    etf = SecurityListing(
        ticker="NIFTYBEES",
        company_name="ETF",
        isin="INF204KB14I2",
        exchange="NSE",
        mic="XNSE",
        security_type="etf",
        eligibility=False,
    )
    etf_result = research_dcf_assumptions(None, etf, now=_NOW)
    assert etf_result.dcf_eligibility == "UNSUPPORTED"
    thin = _listing("TCS", "INE467B01029")
    one_year = research_dcf_assumptions(
        s18._happy(thin),
        thin,
        history=_history(thin)[:1],
        now=_NOW,
    )
    assert one_year.historical_growth_metrics["fcf_cagr"]["status"] == "UNKNOWN"
    assert one_year.wacc_status == "UNKNOWN"


def test_accepted_by_is_never_proposed_by() -> None:
    listing = _listing("TCS", "INE467B01029")
    result = research_dcf_assumptions(_simple18()._happy(listing), listing, proposals=_pack(), now=_NOW)
    for item in result.candidate_assumptions:
        if item.status == "ACCEPTED":
            assert item.accepted_by == VALIDATOR_VERSION
            assert item.proposed_by != item.accepted_by
            assert item.proposed_by != "assumption_validator"


def test_adversarial_fake_wacc_and_terminal() -> None:
    listing = _listing("INFY", "INE009A01021")
    dataset = _simple18()._happy(listing)
    fake_wacc = dcf_assumption_candidate(
        listing, "wacc", "0.12", proposed_by="AI_RESEARCH", source="ai_synthesis"
    )
    fake_g = dcf_assumption_candidate(
        listing, "terminal_growth_rate", "0.03", proposed_by="AI_RESEARCH", source="ai_synthesis"
    )
    result = research_dcf_assumptions(dataset, listing, proposals=(fake_wacc, fake_g), now=_NOW)
    assert result.wacc_status == "UNKNOWN"
    assert result.terminal_growth_status == "UNKNOWN"
    assert result.dcf_eligibility == "DCF_BLOCKED"
    assert any("AI_REJECTED" in item for item in result.validation_reasons)
    dsp = run_dsp_calculations(dataset, assumptions=result.accepted_pack, listing=listing)
    assert dsp.dcf.status == "BLOCKED"


def test_adversarial_wacc_conflict_not_averaged() -> None:
    listing = _listing("RELIANCE", "INE002A01018")
    dataset = _simple18()._happy(listing)
    low = dcf_assumption_candidate(listing, "wacc", "0.08", evidence_ids=("a",), rationale="low")
    high = dcf_assumption_candidate(listing, "wacc", "0.18", evidence_ids=("b",), rationale="high")
    growth = dcf_assumption_candidate(
        listing, "fcf_growth_rate", "0.04", source="historical_company_performance", evidence_ids=("g",)
    )
    terminal = dcf_assumption_candidate(
        listing, "terminal_growth_rate", "0.03", source="macro_data", evidence_ids=("t",)
    )
    result = research_dcf_assumptions(
        dataset, listing, proposals=(low, high, growth, terminal), now=_NOW
    )
    assert result.status == "REVIEW_REQUIRED"
    assert result.dcf_eligibility == "DCF_BLOCKED"
    assert result.wacc is None
    values = {item.value for item in result.candidate_assumptions if item.name == "wacc"}
    assert values == {Decimal("0.08"), Decimal("0.18")}
    assert all("not averaged" in item.detail for item in result.candidate_assumptions if item.name == "wacc")


def test_adversarial_growth_ge_wacc() -> None:
    listing = _listing("WIPRO", "INE075A01022")
    dataset = _simple18()._happy(listing)
    result = research_dcf_assumptions(
        dataset,
        listing,
        proposals=(
            dcf_assumption_candidate(listing, "discount_rate", "0.05", evidence_ids=("w",)),
            dcf_assumption_candidate(
                listing, "fcf_growth_rate", "0.02",
                source="historical_company_performance", evidence_ids=("g",),
            ),
            dcf_assumption_candidate(
                listing, "terminal_growth_rate", "0.06", source="macro_data", evidence_ids=("t",)
            ),
        ),
        now=_NOW,
    )
    assert result.dcf_eligibility == "DCF_BLOCKED"
    assert any("WACC must exceed terminal growth" in item.detail for item in result.candidate_assumptions)


def test_adversarial_wrong_company_stale_currency_missing() -> None:
    tcs = _listing("TCS", "INE467B01029")
    infy = _listing("INFY", "INE009A01021")
    dataset = _simple18()._happy(tcs)
    wrong = dcf_assumption_candidate(
        tcs, "wacc", "0.10", evidence_ids=("x",), isin=infy.isin
    )
    dual = dcf_assumption_candidate(tcs, "wacc", "0.11", evidence_ids=("y",), mic="XBOM")
    identity = research_dcf_assumptions(dataset, tcs, proposals=(wrong, dual), now=_NOW)
    assert identity.dcf_eligibility == "DCF_BLOCKED"
    assert "IDENTITY_FAIL" in identity.validation_reasons
    stale = dcf_assumption_candidate(
        tcs,
        "wacc",
        "0.10",
        evidence_ids=("old",),
        retrieved_at=_NOW - timedelta(days=ASSUMPTION_FRESHNESS_DAYS + 1),
        freshness="CURRENT",
    )
    stale_result = research_dcf_assumptions(dataset, tcs, proposals=(stale,), now=_NOW)
    assert any(item.status == "STALE" for item in stale_result.rejected_assumptions)
    assert "STALE" in stale_result.validation_reasons
    assert stale_result.dcf_eligibility == "DCF_BLOCKED"
    fx = dcf_assumption_candidate(
        tcs, "wacc", "0.10", evidence_ids=("fx",), currency="USD"
    )
    fx_result = research_dcf_assumptions(dataset, tcs, proposals=(fx,), now=_NOW)
    assert any("currency mismatch" in item for item in fx_result.validation_reasons)
    missing = research_dcf_assumptions(dataset, tcs, now=_NOW)
    assert missing.status == "UNKNOWN"
    assert missing.dcf_eligibility == "DCF_BLOCKED"
    assert "WACC:UNKNOWN" in missing.dcf_blockers


def test_adversarial_ai_vs_primary_and_verified_dataset() -> None:
    listing = _listing("TCS", "INE467B01029")
    dataset = _simple18()._happy(listing)
    primary_capex = dataset.verified_decimal("capex")
    ai_capex = dcf_assumption_candidate(
        listing, "capex", "999", proposed_by="AI_RESEARCH", source="ai_synthesis"
    )
    primary_wacc = dcf_assumption_candidate(listing, "wacc", "0.10", evidence_ids=("nse",))
    ai_wacc = dcf_assumption_candidate(
        listing, "wacc", "0.18", proposed_by="AI_RESEARCH", source="ai_synthesis"
    )
    result = research_dcf_assumptions(
        dataset, listing, proposals=(ai_capex, primary_wacc, ai_wacc), now=_NOW
    )
    assert any("PRIMARY_WINS" in item for item in result.validation_reasons)
    assert any("AI_REJECTED" in item for item in result.validation_reasons)
    assert result.wacc == Decimal("0.10")
    assert dataset.verified_decimal("capex") == primary_capex
    ai_item = EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field="revenue",
        value="1",
        as_of=_AS_OF,
        retrieved_at=_NOW,
        source="OpenAI",
        source_type="llm",
        source_url=None,
        document_date=_AS_OF,
        evidence_locator="ai",
        currency="INR",
        unit="actual",
        statement_basis="consolidated",
        agent="openai_nse_mcp",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence="high",
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
    )
    assert EvidenceJudge().promote(ai_item).status != "VERIFIED"
    assert refuse_ai_fact("revenue", proposed_by="openai") == "REJECTED"


def test_no_ai_path_historical_cagr_is_not_terminal() -> None:
    listing = _listing("20MICRONS", "INE144J01027")
    dataset = _simple18()._happy(listing)
    result = research_dcf_assumptions(
        dataset, listing, history=_history(listing), now=_NOW
    )
    assert result.historical_growth_metrics["revenue_cagr"]["status"] == "CALCULATED"
    assert result.historical_growth_metrics["fcf_cagr"]["status"] == "CALCULATED"
    assert result.terminal_growth_status == "UNKNOWN"
    assert result.wacc_status == "UNKNOWN"
    assert result.dcf_eligibility == "DCF_BLOCKED"
    growth_names = {item.name for item in result.candidate_assumptions if item.status == "ACCEPTED"}
    assert "terminal_growth_rate" not in growth_names


def test_wacc_from_components_is_derived_not_a_fact() -> None:
    listing = _listing("TCS", "INE467B01029")
    dataset = _simple18()._happy(listing)
    result = research_dcf_assumptions(
        dataset,
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing, "risk_free_rate", "0.07", source="macro_data", evidence_ids=("rbi",)
            ),
            dcf_assumption_candidate(
                listing, "equity_risk_premium", "0.05", source="macro_data", evidence_ids=("erp",)
            ),
            dcf_assumption_candidate(
                listing, "beta", "1.0", source="industry_data", evidence_ids=("beta",)
            ),
            dcf_assumption_candidate(
                listing, "fcf_growth_rate", "0.04",
                source="historical_company_performance", evidence_ids=("g",),
            ),
            dcf_assumption_candidate(
                listing, "terminal_growth_rate", "0.03", source="macro_data", evidence_ids=("t",)
            ),
            dcf_assumption_candidate(
                listing, "projection_years", "5", unit="years", evidence_ids=("y",)
            ),
        ),
        now=_NOW,
    )
    assert result.wacc == Decimal("0.12")
    assert result.wacc_status == "ACCEPTED"
    assert "not an observed market fact" in result.wacc_components["wacc"]["note"]
    assert result.dcf_eligibility == "ELIGIBLE"


def test_fcf_non_positive_blocks_dcf_even_with_pack() -> None:
    listing = _listing("TCS", "INE467B01029")
    s18 = _simple18()
    dataset = s18._dataset(
        listing,
        price=s18._price(listing),
        price_status="VERIFIED",
        shares=s18._shares(listing),
        shares_status="VERIFIED",
        financials=s18._financials(
            cash=("40", "VERIFIED", _AS_OF),
            debt=("10", "VERIFIED", _AS_OF),
            cfo=("4", "VERIFIED", _AS_OF),
            capex=("10", "VERIFIED", _AS_OF),
            ebit=("8", "VERIFIED", _AS_OF),
            net_income=("12", "VERIFIED", _AS_OF),
            revenue=("100", "VERIFIED", _AS_OF),
        ),
    )
    researched = research_dcf_assumptions(dataset, listing, proposals=_pack(), now=_NOW)
    dsp = run_dsp_calculations(dataset, assumptions=researched.accepted_pack, listing=listing)
    assert dsp.derived.fcf.status == "CALCULATED"
    assert dsp.derived.fcf.value is not None and dsp.derived.fcf.value <= 0
    assert dsp.dcf.status == "BLOCKED"
    blockers = describe_dcf_blockers(
        dataset, dsp, capability="equity", assumptions_accepted=True
    )
    assert any("FCF" in item or "invalid" in item.lower() for item in blockers) or dsp.dcf.detail


def test_reproducibility_and_performance() -> None:
    listing = _listing("INFY", "INE009A01021")
    dataset = _simple18()._happy(listing)
    researched = research_dcf_assumptions(dataset, listing, proposals=_pack(), now=_NOW)
    samples: list[float] = []
    first = None
    for _ in range(5):
        started = perf_counter()
        dsp = run_dsp_calculations(
            dataset, assumptions=researched.accepted_pack, listing=listing, calculated_at=_NOW
        )
        samples.append(perf_counter() - started)
        payload = (
            dsp.dcf.value,
            dsp.intrinsic_value_per_share.value,
            dsp.margin_of_safety.value,
            dsp.derived.fcf.value,
        )
        if first is None:
            first = payload
        assert payload == first
        assert dsp.dcf.status == "CALCULATED"
    assert median(samples) < 0.05
    assert researched.timings["research"] >= 0.0


def test_production_analyse_does_not_inject_hidden_defaults() -> None:
    listing = _listing("TCS", "INE467B01029")
    dialect = (
        f"{listing.company_name}\nISIN {listing.isin}\nconsolidated audited financial statements\n"
        "unit: actual\nINR\nyear ended 31 March 2026\nas_of: 2026-03-31\n"
        "Statement of profit and loss\nRevenue from operations 100000\nProfit for the year 20000\n"
        "Balance sheet\nTotal equity 50000\nCash and cash equivalents 4000\nBorrowings 1000\n"
        "Statement of cash flows\nNet cash from operating activities 15000\nCapital expenditure 5000\n"
        "equity shares outstanding 1000000\n"
    )
    eod = EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field="eod_close",
        value="100.00",
        as_of=date(2026, 9, 11),
        retrieved_at=_NOW,
        source="NSE",
        source_type="exchange_eod",
        source_url="https://nsearchives.nseindia.com/annual.pdf",
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
    result = analyse_listing(
        listing,
        mode="MOCK",
        document_text=dialect,
        document_url="https://nsearchives.nseindia.com/annual.pdf",
        candidates={"eod_close": (eod,)},
    )
    assert result.assumption_research is not None
    assert result.assumption_research.wacc_status == "UNKNOWN"
    assert result.assumption_research.dcf_eligibility == "DCF_BLOCKED"
    if result.dsp is not None:
        assert result.dsp.dcf.status != "CALCULATED"
    replay = analyse_listing(
        listing,
        mode="MOCK",
        document_text=dialect,
        document_url="https://nsearchives.nseindia.com/annual.pdf",
        candidates={"eod_close": (eod,)},
        assumptions=_pack(),
    )
    assert replay.assumption_research is not None
    assert replay.assumption_research.dcf_eligibility == "ELIGIBLE"
    assert replay.assumption_research.wacc_status == "ACCEPTED"
    assert replay.dsp is not None
    if replay.dsp.derived.fcf.status == "CALCULATED":
        assert replay.dsp.dcf.status == "CALCULATED"
    else:
        assert replay.dsp.dcf.status == "BLOCKED"


def test_security_client_and_ai_cannot_bypass_validator() -> None:
    assert "assumptions" not in AnalyseRequest.model_fields
    assert "wacc" not in AnalyseRequest.model_fields
    assert "discount_rate" not in AnalyseRequest.model_fields
    assert "terminal_growth_rate" not in inspect.signature(ResearchOrchestrator.analyse).parameters
    listing = _listing("TCS", "INE467B01029")
    sneaked = assumption(
        "wacc",
        "0.10",
        source="ai_synthesis",
        proposed_by="openai",
        validation_status="ACCEPTED",
    )
    result = research_dcf_assumptions(
        _simple18()._happy(listing), listing, proposals=(sneaked,), now=_NOW
    )
    assert result.wacc_status == "UNKNOWN"
    assert all(item.validation_status != "ACCEPTED" or item.validated_by for item in result.accepted_pack)
    cfg = load_llm_config()
    assert result.ai_status == "NOT_CONFIGURED"
    assert not bool(cfg.openai_api_key) or result.ai_status == "NOT_CONFIGURED"


def test_hidden_default_forensic_official_path() -> None:
    research = (_ENGINE / "assumption_research.py").read_text(encoding="utf-8")
    calc = (_ENGINE / "dsp_calculation.py").read_text(encoding="utf-8")
    gate = (_ENGINE / "dsp_gate.py").read_text(encoding="utf-8")
    for token in ("0.08", "0.10", "0.12", "0.15", "0.18"):
        assert token not in research
    assert "ValuationAssumptions.default" in gate
    assert "value=None" in gate
    assert "required DCF assumptions are not ACCEPTED" in calc
