"""SIMPLE-27 — live component acquisition; DSP calculates WACC/growth. Fail-closed."""

from __future__ import annotations

import ast
import importlib.util
import inspect
from dataclasses import FrozenInstanceError, replace as dc_replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from time import perf_counter

from data_engine.official_research.agents import GeminiFindAgent, UnavailableAgent
from data_engine.official_research.assumption_contract import (
    DATA_CLASS_ASSUMPTION,
    DATA_CLASS_DERIVED,
    DATA_CLASS_FACT,
    classify_data_class,
)
from api_platform.api.composition_schemas import AnalyseRequest
from data_engine.official_research.assumption_research import (
    HistoricalObservation,
    dcf_assumption_candidate,
    research_dcf_assumptions,
)
from data_engine.official_research.orchestrator import ResearchOrchestrator
from data_engine.security_master.models import SecurityListing
from pydantic import ValidationError
from data_engine.official_research.component_research import (
    AI_FORBIDDEN_RESULT_FIELDS,
    evidence_item_from_component,
    ingest_researched_components,
    live_macro_acquisition_status,
    research_components_from_agent,
)
from data_engine.official_research.dsp_calculation import MOS_FORMULA, run_dsp_calculations
from data_engine.official_research.dsp_wacc import (
    DSP_WACC_ENGINE,
    DSP_WACC_VERSION,
    calculate_dsp_wacc,
    compare_external_wacc,
)
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import EvidenceItem, new_evidence_id
from data_engine.official_research.xbrl import extract_xbrl_fields
from data_engine.security_master import SecurityMasterService, load_default_catalog
from valuation.dcf_intelligence.assumptions import CapmInputs, CapitalStructure, CostOfDebtInputs
from valuation.dcf_intelligence.wacc import compute_wacc

_ENGINE = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
_NOW = datetime(2026, 9, 11, tzinfo=UTC)
_AS_OF = date(2026, 3, 31)
_RBI = "https://www.rbi.org.in/Scripts/BS_ViewBulletin.aspx"
_YAHOO = "https://finance.yahoo.com/quote/TCS.NS"
_NSE = "https://nsearchives.nseindia.com/annual.pdf"
_NAMED = (
    ("TCS", "INE467B01029", "XNSE"),
    ("INFY", "INE009A01021", "XNSE"),
    ("RELIANCE", "INE002A01018", "XNSE"),
    ("WIPRO", "INE075A01022", "XNSE"),
    ("20MICRONS", "INE144J01027", "XNSE"),
    ("21STCENMGM", "INE253B01015", "XNSE"),
)


def _simple18():
    path = Path(__file__).with_name("test_simple18.py")
    spec = importlib.util.spec_from_file_location("simple18_helpers_s27", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _master() -> SecurityMasterService:
    return SecurityMasterService(load_default_catalog())


def _listing(ticker: str, isin: str, mic: str = "XNSE"):
    resolved = _master().resolve(isin, isin=isin, mic=mic)
    assert resolved.status == "RESOLVED" and resolved.identity is not None
    return resolved.identity


def _growth_pack(listing):
    return (
        dcf_assumption_candidate(
            listing,
            "fcf_growth_rate",
            "0.04",
            source="historical_company_performance",
            evidence_ids=("g",),
        ),
        dcf_assumption_candidate(
            listing,
            "terminal_growth_rate",
            "0.03",
            source="macro_data",
            evidence_ids=("t",),
        ),
        dcf_assumption_candidate(
            listing, "projection_years", "5", unit="years", evidence_ids=("y",)
        ),
    )


def _evidence(listing, field: str, value: str, *, url: str, source_type: str, agent: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field=field,
        value=value,
        as_of=_AS_OF,
        retrieved_at=_NOW,
        source="RBI" if "rbi.org.in" in url else "research",
        source_type=source_type,
        source_url=url,
        document_date=_AS_OF,
        evidence_locator=field,
        currency="INR",
        unit="decimal",
        statement_basis=None,
        agent=agent,
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence="high",
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
    )


def _component_payload(listing, field: str, value: str, *, url: str = _RBI) -> dict:
    return {
        "field": field,
        "value": value,
        "source": "RBI",
        "source_type": "regulator",
        "source_url": url,
        "retrieved_at": _NOW,
        "as_of": _AS_OF,
        "document_date": _AS_OF,
        "isin": listing.isin,
        "mic": listing.mic,
        "unit": "decimal",
        "currency": "INR",
        "period": "FY2026",
        "evidence_locator": field,
        "confidence": "high",
        "identity": listing.isin,
    }


def _history(listing, *, fcf_positive: bool = True) -> tuple[HistoricalObservation, ...]:
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
        HistoricalObservation(
            field="net_income", value=Decimal("10"), as_of=date(2024, 3, 31),
            isin=listing.isin, mic=listing.mic, currency="INR", unit="actual",
            statement_basis="consolidated", evidence_id="ni-24",
        ),
        HistoricalObservation(
            field="net_income", value=Decimal("12"), as_of=_AS_OF,
            isin=listing.isin, mic=listing.mic, currency="INR", unit="actual",
            statement_basis="consolidated", evidence_id="ni-26",
        ),
    )


def _promote_components(listing, fields: dict[str, str]) -> tuple:
    judge = EvidenceJudge()
    return tuple(
        judge.promote(
            _evidence(listing, name, value, url=_RBI, source_type="regulator", agent="official_filing_detail")
        )
        for name, value in fields.items()
    )


def _levered_dataset(s18, listing, evidence=()):
    dataset = s18._dataset(
        listing,
        price=s18._price(listing),
        price_status="VERIFIED",
        shares=s18._shares(listing, value="1"),
        shares_status="VERIFIED",
        financials=s18._financials(
            cash=("0", "VERIFIED", _AS_OF),
            debt=("100", "VERIFIED", _AS_OF),
            equity=("100", "VERIFIED", _AS_OF),
            cfo=("20", "VERIFIED", _AS_OF),
            capex=("5", "VERIFIED", _AS_OF),
            ebit=("8", "VERIFIED", _AS_OF),
            net_income=("12", "VERIFIED", _AS_OF),
            revenue=("100", "VERIFIED", _AS_OF),
        ),
    )
    return dc_replace(dataset, evidence=evidence)


def _horizon(listing):
    return (
        dcf_assumption_candidate(
            listing, "terminal_growth_rate", "0.03", source="macro_data", evidence_ids=("t",)
        ),
        dcf_assumption_candidate(
            listing, "projection_years", "5", unit="years", evidence_ids=("y",)
        ),
    )


def test_no_company_specific_wacc_branches() -> None:
    banned = {row[0] for row in _NAMED}
    for name in ("dsp_wacc.py", "component_research.py", "assumption_research.py"):
        tree = ast.parse((_ENGINE / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in banned:
                raise AssertionError(f"{name} contains ticker {node.value}")


def test_input_inventory_classes() -> None:
    assert classify_data_class("revenue") == DATA_CLASS_FACT
    assert classify_data_class("finance_costs") == DATA_CLASS_FACT
    assert classify_data_class("fcf") == DATA_CLASS_DERIVED
    assert classify_data_class("cost_of_equity") == DATA_CLASS_DERIVED
    assert classify_data_class("wacc") == DATA_CLASS_ASSUMPTION
    assert "wacc" in AI_FORBIDDEN_RESULT_FIELDS
    assert "fcf_growth_rate" in AI_FORBIDDEN_RESULT_FIELDS


def test_dsp_wacc_reuses_existing_engine() -> None:
    expected = compute_wacc(
        capm=CapmInputs(0.07, 1.0, 0.05),
        debt=CostOfDebtInputs(0.10),
        structure=CapitalStructure(equity_market_value=100.0, debt_market_value=100.0),
        tax_rate=0.25,
    )
    calculated = calculate_dsp_wacc(
        risk_free_rate=Decimal("0.07"),
        beta=Decimal("1"),
        equity_risk_premium=Decimal("0.05"),
        equity_market_value=Decimal("100"),
        debt_market_value=Decimal("100"),
        pre_tax_cost_of_debt=Decimal("0.10"),
        tax_rate=Decimal("0.25"),
        evidence_ids=("rf", "beta", "erp", "rd", "t"),
    )
    assert calculated.engine == DSP_WACC_ENGINE
    assert calculated.status == "CALCULATED"
    assert calculated.cost_of_equity == Decimal(str(round(expected.cost_of_equity.value, 10)))
    assert calculated.wacc == Decimal(str(round(expected.wacc.value, 10)))
    assert calculated.wacc == Decimal("0.0975")


def test_ai_may_not_return_wacc_or_growth() -> None:
    listing = _listing("TCS", "INE467B01029")
    result = ingest_researched_components(
        (
            {
                "field": "wacc",
                "value": "0.11",
                "source": "gemini",
                "source_type": "llm",
                "source_url": _RBI,
                "retrieved_at": _NOW,
                "as_of": _AS_OF,
                "isin": listing.isin,
                "mic": listing.mic,
                "unit": "decimal",
                "currency": "INR",
                "period": "2026",
                "evidence_locator": "model",
            },
            {
                "field": "fcf_growth_rate",
                "value": "0.10",
                "source": "gemini",
                "source_type": "llm",
                "source_url": _RBI,
                "retrieved_at": _NOW,
                "as_of": _AS_OF,
                "isin": listing.isin,
                "mic": listing.mic,
                "unit": "decimal",
                "currency": "INR",
                "period": "2026",
                "evidence_locator": "model",
            },
        ),
        listing,
        proposed_by="AI_RESEARCH",
    )
    assert result.status == "REJECTED"
    assert result.accepted == ()


def test_unavailable_agent_is_not_configured() -> None:
    listing = _listing("WIPRO", "INE075A01022")
    result = research_components_from_agent(UnavailableAgent(role="gemini_find"), listing)
    assert result.ai_status == "NOT_CONFIGURED"
    assert GeminiFindAgent().available() is False


def test_judge_rejects_wacc_and_yahoo_beta() -> None:
    listing = _listing("TCS", "INE467B01029")
    judge = EvidenceJudge()
    wacc = judge.promote(
        _evidence(listing, "wacc", "0.11", url=_NSE, source_type="regulator", agent="official_nse_primary")
    )
    assert wacc.status != "VERIFIED"
    yahoo = judge.promote(
        _evidence(listing, "beta", "1.05", url=_YAHOO, source_type="secondary", agent="gemini_find")
    )
    assert yahoo.status != "VERIFIED"
    rbi = judge.promote(
        _evidence(
            listing,
            "risk_free_rate",
            "0.07",
            url=_RBI,
            source_type="regulator",
            agent="official_filing_detail",
        )
    )
    assert rbi.status == "VERIFIED"


def test_dsp_calculates_from_verified_components_not_ai_wacc() -> None:
    s18 = _simple18()
    listing = _listing("TCS", "INE467B01029")
    happy = s18._happy(listing)
    rbi = EvidenceJudge().promote(
        _evidence(
            listing,
            "risk_free_rate",
            "0.07",
            url=_RBI,
            source_type="regulator",
            agent="official_filing_detail",
        )
    )
    beta = EvidenceJudge().promote(
        _evidence(listing, "beta", "1.0", url=_RBI, source_type="regulator", agent="official_filing_detail")
    )
    erp = EvidenceJudge().promote(
        _evidence(
            listing,
            "equity_risk_premium",
            "0.05",
            url=_RBI,
            source_type="regulator",
            agent="official_filing_detail",
        )
    )
    dataset = dc_replace(happy, evidence=(rbi, beta, erp))
    ai_wacc = dcf_assumption_candidate(
        listing,
        "wacc",
        "0.11",
        proposed_by="AI_RESEARCH",
        source="ai_synthesis",
        evidence_ids=("fake",),
    )
    result = research_dcf_assumptions(
        dataset, listing, proposals=(ai_wacc, *_growth_pack(listing)), now=_NOW
    )
    assert result.dsp_wacc is not None
    assert result.dsp_wacc.engine == DSP_WACC_ENGINE
    assert result.wacc == Decimal("0.12")
    assert result.wacc_status == "ACCEPTED"
    assert any("AI_CALCULATED_OUTPUT_REJECTED" in item.detail for item in result.rejected_assumptions)
    dsp = run_dsp_calculations(dataset, assumptions=result.accepted_pack, listing=listing)
    assert dsp.dcf.status == "CALCULATED"
    assert dsp.margin_of_safety.formula == MOS_FORMULA


def test_levered_wacc_from_debt_cost_and_tax() -> None:
    s18 = _simple18()
    listing = _listing("RELIANCE", "INE002A01018")
    dataset = s18._dataset(
        listing,
        price=s18._price(listing),
        price_status="VERIFIED",
        shares=s18._shares(listing, value="1"),
        shares_status="VERIFIED",
        financials=s18._financials(
            cash=("0", "VERIFIED", _AS_OF),
            debt=("100", "VERIFIED", _AS_OF),
            cfo=("20", "VERIFIED", _AS_OF),
            capex=("5", "VERIFIED", _AS_OF),
            ebit=("8", "VERIFIED", _AS_OF),
            net_income=("12", "VERIFIED", _AS_OF),
            revenue=("100", "VERIFIED", _AS_OF),
        ),
    )
    result = research_dcf_assumptions(
        dataset,
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing, "risk_free_rate", "0.07", source="macro_data", evidence_ids=("rf",)
            ),
            dcf_assumption_candidate(
                listing, "beta", "1.0", source="industry_data", evidence_ids=("b",)
            ),
            dcf_assumption_candidate(
                listing, "equity_risk_premium", "0.05", source="macro_data", evidence_ids=("erp",)
            ),
            dcf_assumption_candidate(
                listing, "pre_tax_cost_of_debt", "0.10", source="company_filings", evidence_ids=("rd",)
            ),
            dcf_assumption_candidate(
                listing, "tax_rate", "0.25", source="company_filings", evidence_ids=("tax",)
            ),
            *_growth_pack(listing),
        ),
        now=_NOW,
    )
    assert result.dsp_wacc is not None
    assert result.dsp_wacc.wacc == Decimal("0.0975")
    assert result.wacc == Decimal("0.0975")
    assert result.dcf_eligibility == "ELIGIBLE"


def test_finance_costs_xbrl_is_not_wacc() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in-bse-fin="http://www.bseindia.com/xbrl/fin">
  <xbrli:context id="FourDConsolidated">
    <xbrli:entity>
      <xbrli:identifier scheme="http://www.nseindia.com/isin">INE467B01029</xbrli:identifier>
    </xbrli:entity>
    <xbrli:period>
      <xbrli:startDate>2025-04-01</xbrli:startDate>
      <xbrli:endDate>2026-03-31</xbrli:endDate>
    </xbrli:period>
  </xbrli:context>
  <xbrli:unit id="INR"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>
  <in-bse-fin:FinanceCosts contextRef="FourDConsolidated" unitRef="INR">10</in-bse-fin:FinanceCosts>
  <in-bse-fin:Borrowings contextRef="FourDConsolidated" unitRef="INR">100</in-bse-fin:Borrowings>
</xbrl>
"""
    parsed = extract_xbrl_fields(xml, isin="INE467B01029")
    assert Decimal(str(parsed.fields["finance_costs"].value)) == Decimal("10")
    assert Decimal(str(parsed.fields["debt"].value)) == Decimal("100")
    assert "wacc" not in parsed.fields


def test_universal_named_securities_without_components_stay_blocked() -> None:
    s18 = _simple18()
    for ticker, isin, mic in _NAMED:
        listing = _listing(ticker, isin, mic)
        empty = research_dcf_assumptions(s18._happy(listing), listing, now=_NOW)
        assert empty.wacc_status == "UNKNOWN"
        assert empty.dcf_eligibility == "DCF_BLOCKED"
        assert empty.ai_status == "NOT_CONFIGURED"


def test_terminal_growth_not_invented_from_history_or_ai() -> None:
    s18 = _simple18()
    listing = _listing("20MICRONS", "INE144J01027")
    result = research_dcf_assumptions(
        s18._happy(listing),
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing,
                "terminal_growth_rate",
                "0.04",
                proposed_by="AI_RESEARCH",
                source="ai_synthesis",
            ),
        ),
        now=_NOW,
    )
    assert result.terminal_growth_status == "UNKNOWN"
    assert result.dcf_eligibility == "DCF_BLOCKED"


def test_live_macro_acquisition_is_unknown_without_new_provider() -> None:
    status = live_macro_acquisition_status()
    assert status["risk_free_rate"]["status"] == "UNKNOWN"
    assert status["risk_free_rate"]["rate"] is None
    assert status["beta"]["status"] == "UNKNOWN"
    assert status["equity_risk_premium"]["status"] == "UNKNOWN"


def test_complete_data_replay_calculates_wacc_growth_and_dcf() -> None:
    s18 = _simple18()
    listing = _listing("INFY", "INE009A01021")
    evidence = _promote_components(
        listing,
        {
            "risk_free_rate": "0.07",
            "beta": "1.0",
            "equity_risk_premium": "0.05",
            "pre_tax_cost_of_debt": "0.10",
            "tax_rate": "0.25",
        },
    )
    dataset = _levered_dataset(s18, listing, evidence)
    t0 = perf_counter()
    researched = research_dcf_assumptions(
        dataset, listing, proposals=_horizon(listing), history=_history(listing), now=_NOW
    )
    research_ms = (perf_counter() - t0) * 1000
    assert researched.dsp_wacc is not None
    assert researched.dsp_wacc.wacc == Decimal("0.0975")
    assert researched.dsp_wacc.calculation_version == DSP_WACC_VERSION
    assert researched.dsp_wacc.cost_of_equity == Decimal("0.12")
    assert researched.historical_growth_metrics["fcf_cagr"]["status"] == "CALCULATED"
    assert researched.historical_growth_metrics["revenue_cagr"]["status"] == "CALCULATED"
    assert researched.wacc_status == "ACCEPTED"
    assert researched.dcf_eligibility == "ELIGIBLE"
    t1 = perf_counter()
    dsp = run_dsp_calculations(dataset, assumptions=researched.accepted_pack, listing=listing)
    dcf_ms = (perf_counter() - t1) * 1000
    assert dsp.dcf.status == "CALCULATED"
    assert dsp.dcf.extras["wacc"] == Decimal("0.0975")
    assert dsp.dcf.extras["projection_years"] == Decimal("5")
    assert dsp.margin_of_safety.formula == MOS_FORMULA
    assert researched.timings["dsp_wacc"] >= 0
    assert research_ms >= 0 and dcf_ms >= 0


def test_ai_retrieval_replay_evidence_then_dsp() -> None:
    s18 = _simple18()
    listing = _listing("WIPRO", "INE075A01022")
    ingest = ingest_researched_components(
        (
            _component_payload(listing, "risk_free_rate", "0.07"),
            _component_payload(listing, "beta", "1.0"),
            _component_payload(listing, "equity_risk_premium", "0.05"),
            _component_payload(listing, "pre_tax_cost_of_debt", "0.10"),
            _component_payload(listing, "tax_rate", "0.25"),
        ),
        listing,
        proposed_by="AI_RESEARCH",
    )
    assert ingest.status == "PROPOSED"
    judge = EvidenceJudge()
    verified = tuple(
        judge.promote(evidence_item_from_component(row, listing, agent="gemini_find"))
        for row in ingest.accepted
    )
    assert all(item.status == "VERIFIED" for item in verified)
    dataset = _levered_dataset(s18, listing, verified)
    result = research_dcf_assumptions(
        dataset, listing, proposals=_growth_pack(listing), now=_NOW
    )
    assert result.dsp_wacc is not None
    assert result.dsp_wacc.wacc == Decimal("0.0975")
    assert result.wacc_reconstruction.get("status") in {"NOT_APPLICABLE", "MATCH"}
    dsp = run_dsp_calculations(dataset, assumptions=result.accepted_pack, listing=listing)
    assert dsp.dcf.status == "CALCULATED"


def test_external_wacc_reconstruction_conflict_is_not_averaged() -> None:
    s18 = _simple18()
    listing = _listing("RELIANCE", "INE002A01018")
    evidence = _promote_components(
        listing,
        {
            "risk_free_rate": "0.07",
            "beta": "1.0",
            "equity_risk_premium": "0.05",
            "pre_tax_cost_of_debt": "0.10",
            "tax_rate": "0.25",
        },
    )
    dataset = _levered_dataset(s18, listing, evidence)
    external = dcf_assumption_candidate(
        listing, "wacc", "0.11", source="industry_data", evidence_ids=("ext",)
    )
    result = research_dcf_assumptions(
        dataset, listing, proposals=(external, *_horizon(listing)), now=_NOW
    )
    assert compare_external_wacc(Decimal("0.0975"), Decimal("0.11")) == "REVIEW_REQUIRED"
    assert result.wacc_reconstruction["status"] == "REVIEW_REQUIRED"
    assert result.dcf_eligibility == "DCF_BLOCKED"
    assert result.wacc_status != "ACCEPTED" or result.status == "REVIEW_REQUIRED"


def test_adversarial_matrix_a_to_l() -> None:
    s18 = _simple18()
    listing = _listing("TCS", "INE467B01029")
    # A — AI WACC only
    a = ingest_researched_components(
        (_component_payload(listing, "wacc", "0.11"),), listing, proposed_by="AI_RESEARCH"
    )
    assert a.status == "REJECTED"
    # B — AI WACC + unsupported field
    b = ingest_researched_components(
        (
            _component_payload(listing, "wacc", "0.11"),
            {**_component_payload(listing, "made_up_input", "1"), "field": "made_up_input"},
        ),
        listing,
        proposed_by="AI_RESEARCH",
    )
    assert b.status == "REJECTED"
    assert not b.accepted
    # C — valid underlying evidence (covered by AI retrieval replay; components accepted)
    c = ingest_researched_components(
        (_component_payload(listing, "risk_free_rate", "0.07"),),
        listing,
        proposed_by="AI_RESEARCH",
    )
    assert c.status == "PROPOSED"
    # D — AI fake ERP injected as assumption
    d = research_dcf_assumptions(
        s18._happy(listing),
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing,
                "equity_risk_premium",
                "0.18",
                proposed_by="AI_RESEARCH",
                source="ai_synthesis",
                evidence_ids=("fake-erp",),
            ),
        ),
        now=_NOW,
    )
    assert all(item.name != "equity_risk_premium" or item.status == "REJECTED" for item in d.rejected_assumptions) or d.wacc_status == "UNKNOWN"
    assert d.dcf_eligibility == "DCF_BLOCKED"
    # E — wrong-company beta
    other = _listing("INFY", "INE009A01021")
    e = research_dcf_assumptions(
        s18._happy(listing),
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing, "beta", "1.4", source="industry_data", evidence_ids=("b",), isin=other.isin
            ),
            *_growth_pack(listing),
        ),
        now=_NOW,
    )
    assert any(item.detail == "IDENTITY_FAIL" for item in e.rejected_assumptions)
    # F — stale risk-free
    f = research_dcf_assumptions(
        s18._happy(listing),
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing,
                "risk_free_rate",
                "0.07",
                source="macro_data",
                evidence_ids=("rf",),
                retrieved_at=_NOW - timedelta(days=400),
            ),
        ),
        now=_NOW,
    )
    assert any(item.freshness == "STALE" or item.status == "STALE" for item in f.rejected_assumptions)
    # G — conflicting ERP
    g = research_dcf_assumptions(
        s18._happy(listing),
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing, "equity_risk_premium", "0.05", source="macro_data", evidence_ids=("e1",)
            ),
            dcf_assumption_candidate(
                listing, "equity_risk_premium", "0.08", source="macro_data", evidence_ids=("e2",)
            ),
        ),
        now=_NOW,
    )
    assert g.status == "REVIEW_REQUIRED" or "REVIEW_REQUIRED" in g.dcf_blockers
    assert g.dcf_eligibility == "DCF_BLOCKED"
    # H — WACC <= terminal growth
    h = research_dcf_assumptions(
        s18._happy(listing),
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing, "discount_rate", "0.03", source="primary_research", evidence_ids=("w",)
            ),
            dcf_assumption_candidate(
                listing, "terminal_growth_rate", "0.04", source="macro_data", evidence_ids=("t",)
            ),
            dcf_assumption_candidate(
                listing, "fcf_growth_rate", "0.02", source="historical_company_performance", evidence_ids=("g",)
            ),
            dcf_assumption_candidate(
                listing, "projection_years", "5", unit="years", evidence_ids=("y",)
            ),
        ),
        now=_NOW,
    )
    assert h.dcf_eligibility == "DCF_BLOCKED"
    # I — currency mismatch
    i = research_dcf_assumptions(
        s18._happy(listing),
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing,
                "fcf_growth_rate",
                "0.04",
                source="historical_company_performance",
                evidence_ids=("g",),
                currency="USD",
            ),
        ),
        now=_NOW,
    )
    assert any("currency" in item.detail for item in i.rejected_assumptions)
    # J — period mismatch
    j = research_dcf_assumptions(
        s18._happy(listing),
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing, "risk_free_rate", "0.07", source="macro_data", evidence_ids=("rf",), period="Q1 FY2024"
            ),
            dcf_assumption_candidate(
                listing, "beta", "1.0", source="industry_data", evidence_ids=("b",), period="Q1 FY2026"
            ),
            dcf_assumption_candidate(
                listing, "equity_risk_premium", "0.05", source="macro_data", evidence_ids=("e",), period="Q1 FY2024"
            ),
            *_horizon(listing),
        ),
        now=_NOW,
    )
    assert j.dsp_wacc is not None
    assert "period mismatch" in j.dsp_wacc.detail
    assert j.dcf_eligibility == "DCF_BLOCKED"
    # K — AI intrinsic value
    k = ingest_researched_components(
        (_component_payload(listing, "intrinsic_value", "1234"),),
        listing,
        proposed_by="AI_RESEARCH",
    )
    assert k.status == "REJECTED"
    # L — AI cannot mutate VerifiedDataset
    frozen = s18._happy(listing)
    try:
        frozen.evidence = ()  # type: ignore[misc]
        raise AssertionError("VerifiedDataset must be frozen")
    except FrozenInstanceError:
        pass


def test_client_cannot_inject_authoritative_dcf_inputs() -> None:
    for payload in (
        {"ticker": "TCS", "wacc": 0.11},
        {"ticker": "TCS", "terminal_growth": 0.03},
        {"ticker": "TCS", "intrinsic_value": 100},
        {"ticker": "TCS", "verified_financials": {"revenue": 1}},
        {"ticker": "TCS", "accepted_assumptions": [{"wacc": 0.1}]},
    ):
        try:
            AnalyseRequest(**payload)
            raise AssertionError(f"client injection must fail: {payload}")
        except ValidationError:
            pass
    params = inspect.signature(ResearchOrchestrator.analyse).parameters
    assert "wacc" not in params
    assert "terminal_growth" not in params
    assert "accepted_assumptions" not in params


def test_projection_years_has_no_hidden_production_default() -> None:
    s18 = _simple18()
    listing = _listing("TCS", "INE467B01029")
    evidence = _promote_components(
        listing, {"risk_free_rate": "0.07", "beta": "1.0", "equity_risk_premium": "0.05"}
    )
    dataset = dc_replace(s18._happy(listing), evidence=evidence)
    result = research_dcf_assumptions(
        dataset,
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing, "fcf_growth_rate", "0.04", source="historical_company_performance", evidence_ids=("g",)
            ),
            dcf_assumption_candidate(
                listing, "terminal_growth_rate", "0.03", source="macro_data", evidence_ids=("t",)
            ),
        ),
        now=_NOW,
    )
    assert "PROJECTION_YEARS:UNKNOWN" in result.dcf_blockers
    assert result.dcf_eligibility == "DCF_BLOCKED"
    dsp = run_dsp_calculations(dataset, assumptions=result.accepted_pack, listing=listing)
    assert dsp.dcf.status == "BLOCKED"
    assert "hidden horizon default" in dsp.dcf.detail


def test_finance_costs_derive_cost_of_debt_and_statutory_is_not_substituted() -> None:
    s18 = _simple18()
    listing = _listing("RELIANCE", "INE002A01018")
    components = _promote_components(
        listing, {"risk_free_rate": "0.07", "beta": "1.0", "equity_risk_premium": "0.05", "tax_rate": "0.25"}
    )
    finance = EvidenceJudge().promote(
        _evidence(listing, "finance_costs", "10", url=_NSE, source_type="regulator", agent="official_filing_detail")
    )
    derived_rd = research_dcf_assumptions(
        _levered_dataset(s18, listing, (*components, finance)),
        listing,
        proposals=_horizon(listing),
        now=_NOW,
    )
    assert derived_rd.dsp_wacc is not None
    assert derived_rd.dsp_wacc.inputs.get("pre_tax_cost_of_debt_origin") == "finance_costs / debt"
    assert derived_rd.dsp_wacc.wacc == Decimal("0.0975")
    statutory_only = ingest_researched_components(
        (_component_payload(listing, "statutory_tax_rate", "0.25"),),
        listing,
        proposed_by="DETERMINISTIC_RESEARCH",
    )
    assert statutory_only.status == "PROPOSED"
    no_tax = research_dcf_assumptions(
        _levered_dataset(
            s18,
            listing,
            _promote_components(
                listing, {"risk_free_rate": "0.07", "beta": "1.0", "equity_risk_premium": "0.05"}
            ),
        ),
        listing,
        proposals=_horizon(listing),
        now=_NOW,
    )
    assert no_tax.dsp_wacc is not None
    assert no_tax.dsp_wacc.inputs.get("tax_rate") in {None, "None"}
    assert no_tax.dsp_wacc.wacc == Decimal("0.12")


def test_universal_matrix_dynamic_bank_etf_and_edge_cases() -> None:
    s18 = _simple18()
    catalog = load_default_catalog()
    named = {row[0] for row in _NAMED}
    dynamic = [
        item
        for item in catalog.all()
        if item.eligibility
        and item.mic == "XNSE"
        and item.security_type == "equity"
        and item.ticker not in named
        and "bank" not in item.company_name.lower()
    ][:5]
    assert len(dynamic) == 5
    for item in dynamic:
        listing = _listing(item.ticker, item.isin, item.mic)
        empty = research_dcf_assumptions(s18._happy(listing), listing, now=_NOW)
        assert empty.dcf_eligibility == "DCF_BLOCKED"
        evidence = _promote_components(
            listing, {"risk_free_rate": "0.07", "beta": "1.0", "equity_risk_premium": "0.05"}
        )
        filled = research_dcf_assumptions(
            dc_replace(s18._happy(listing), evidence=evidence),
            listing,
            proposals=_growth_pack(listing),
            now=_NOW,
        )
        assert filled.dcf_eligibility == "ELIGIBLE"
        dsp = run_dsp_calculations(
            dc_replace(s18._happy(listing), evidence=evidence),
            assumptions=filled.accepted_pack,
            listing=listing,
        )
        assert dsp.dcf.status == "CALCULATED"
    bank = _listing("HDFCBANK", "INE040A01034")
    bank_result = research_dcf_assumptions(s18._happy(bank), bank, proposals=_growth_pack(bank), now=_NOW)
    assert bank_result.dcf_eligibility == "BANK_VALUATION_METHOD_REQUIRED"
    etf = SecurityListing(
        ticker="NIFTYBEES",
        company_name="ETF",
        isin="INF204KB14I2",
        exchange="NSE",
        mic="XNSE",
        security_type="etf",
        eligibility=False,
    )
    assert research_dcf_assumptions(None, etf, now=_NOW).dcf_eligibility == "UNSUPPORTED"
    thin = _listing("TCS", "INE467B01029")
    one_year = research_dcf_assumptions(
        s18._happy(thin), thin, history=_history(thin)[:1], now=_NOW
    )
    assert one_year.historical_growth_metrics["fcf_cagr"]["status"] == "UNKNOWN"
    negative = research_dcf_assumptions(
        s18._happy(thin),
        thin,
        proposals=_growth_pack(thin),
        history=_history(thin, fcf_positive=False),
        now=_NOW,
    )
    assert negative.historical_growth_metrics["fcf_cagr"]["status"] == "UNKNOWN"
    missing = research_dcf_assumptions(s18._happy(thin), thin, now=_NOW)
    assert missing.dcf_eligibility == "DCF_BLOCKED"


def test_hidden_default_audit_on_official_wacc_path() -> None:
    banned_rates = {0.08, 0.09, 0.10, 0.11, 0.12, 0.15, 0.18}
    for name in ("dsp_wacc.py", "assumption_research.py", "component_research.py"):
        tree = ast.parse((_ENGINE / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in banned_rates:
                raise AssertionError(f"{name} hardcodes rate {node.value}")
    source = (_ENGINE / "dsp_calculation.py").read_text(encoding="utf-8")
    dcf_fn = source.split("def _run_dcf")[1].split("def ")[0]
    assert "years = 5" not in dcf_fn
    assert "0.10" not in dcf_fn
    assert "0.12" not in dcf_fn
    assert "0.08" not in dcf_fn
