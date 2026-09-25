"""SIMPLE-29 — DCF tenor policy + approved beta/ERP research. Fail-closed."""

from __future__ import annotations

import ast
import importlib.util
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from api_platform.api.composition_schemas import AnalyseRequest
from data_engine.official_research.agents import UnavailableAgent
from data_engine.official_research.assumption_research import (
    dcf_assumption_candidate,
    research_dcf_assumptions,
)
from data_engine.official_research.capm_components import (
    qualify_capm_component,
    research_live_capm_components,
)
from data_engine.official_research.component_research import (
    AI_FORBIDDEN_RESULT_FIELDS,
    evidence_item_from_component,
    ingest_researched_components,
    live_macro_acquisition_status,
    research_components_from_agent,
)
from data_engine.official_research.dcf_tenor_policy import (
    DCF_RISK_FREE_MATURITY_POLICY,
    DCF_RISK_FREE_PREFERRED_MATURITY,
    evaluate_risk_free_binding,
    tenor_policy_public_dict,
)
from data_engine.official_research.dsp_calculation import MOS_FORMULA, run_dsp_calculations
from data_engine.official_research.dsp_wacc import (
    DSP_WACC_ENGINE,
    calculate_dsp_wacc,
    compare_external_wacc,
)
from data_engine.official_research.end_to_end import analyse_listing
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.rbi_risk_free import (
    RBI_NSDP_URL,
    RBI_RISK_FREE_MATURITY_POLICY,
    acquire_rbi_risk_free,
)
from data_engine.security_master import SecurityMasterService, load_default_catalog
from data_engine.security_master.models import SecurityListing
from pydantic import ValidationError
from valuation.dcf_intelligence.wacc import compute_wacc

_ENGINE = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
_NOW = datetime(2026, 9, 12, tzinfo=UTC)
_VALUATION = date(2026, 9, 12)
_RBI = "https://www.rbi.org.in/Scripts/BS_ViewBulletin.aspx"
_NAMED = (
    ("TCS", "INE467B01029", "XNSE"),
    ("INFY", "INE009A01021", "XNSE"),
    ("RELIANCE", "INE002A01018", "XNSE"),
    ("WIPRO", "INE075A01022", "XNSE"),
    ("20MICRONS", "INE144J01027", "XNSE"),
    ("21STCENMGM", "INE253B01015", "XNSE"),
)
_NSDP = """
<html><body>
Date of Publish : Sep 11, 2026
Interest Rates
1. Bank Rate^ Per cent per annum September/04/2026 5.50
3. Treasury Bill Rates Per cent per annum September/09/2026 5.2089
Stock Market
</body></html>
"""
_GSEC10 = """
<html><body>
Date of Publish : Sep 11, 2026
Interest Rates
10-year Government Security yield Per cent per annum September/09/2026 7.00
Stock Market
</body></html>
"""


def _simple18():
    path = Path(__file__).with_name("test_simple18.py")
    spec = importlib.util.spec_from_file_location("simple18_helpers_s29", path)
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


def _payload(listing, field: str, value: str, **extra) -> dict:
    row = {
        "field": field,
        "value": value,
        "source": extra.get("source", "RBI"),
        "source_type": extra.get("source_type", "regulator"),
        "source_url": extra.get("source_url", _RBI),
        "retrieved_at": _NOW,
        "as_of": extra.get("as_of", _VALUATION),
        "document_date": extra.get("document_date", _VALUATION),
        "isin": extra.get("isin", listing.isin),
        "mic": extra.get("mic", listing.mic),
        "unit": "decimal",
        "currency": extra.get("currency", "INR"),
        "period": extra.get("period", "FY2026"),
        "evidence_locator": extra.get("evidence_locator", field),
        "methodology": extra.get("methodology"),
        "market": extra.get("market"),
        "beta_kind": extra.get("beta_kind"),
        "geography": extra.get("geography"),
    }
    return row


def test_tenor_policy_is_explicit_gap() -> None:
    policy = tenor_policy_public_dict()
    assert policy["maturity_policy"] == "POLICY_GAP"
    assert policy["preferred_maturity"] is None
    assert DCF_RISK_FREE_PREFERRED_MATURITY is None
    assert DCF_RISK_FREE_MATURITY_POLICY == RBI_RISK_FREE_MATURITY_POLICY == "POLICY_GAP"
    assert policy["unlabeled_treatment"] == "VERIFIED_OBSERVATION_NON_BINDING"
    assert policy["known_maturity_required_to_bind"] is True
    assert "CapmInputs" in policy["basis"]


def test_h_unlabeled_tbill_verified_observation_policy_gap() -> None:
    listing = _listing("TCS", "INE467B01029")
    result = acquire_rbi_risk_free(
        listing,
        valuation_date=_VALUATION,
        document_text=_NSDP,
        mode="MOCK",
        now=_NOW,
    )
    assert result.status == "RETRIEVED"
    assert result.instrument == "Treasury Bill Rates"
    assert result.maturity == "UNSPECIFIED"
    assert result.binding_status == "POLICY_GAP"
    assert result.wacc_input is None
    assert result.value == Decimal("0.052089")
    assert not any(
        item.field == "risk_free_rate" and item.status == "VERIFIED"
        for item in result.evidence
    )


def test_i_tenor_mismatch_and_gsec_unbound_under_gap() -> None:
    assert (
        evaluate_risk_free_binding(
            instrument_kind="g_sec",
            maturity="10-year",
            required_maturity="91-day",
            maturity_policy="REQUIRED_MATURITY",
        )
        == "POLICY_MISMATCH"
    )
    listing = _listing("INFY", "INE009A01021")
    result = acquire_rbi_risk_free(
        listing,
        valuation_date=_VALUATION,
        document_text=_GSEC10,
        mode="MOCK",
        now=_NOW,
    )
    assert result.maturity == "10-year"
    assert result.binding_status == "POLICY_GAP"
    assert result.wacc_input is None


def test_a_ai_wacc_rejected() -> None:
    listing = _listing("TCS", "INE467B01029")
    ingest = ingest_researched_components(
        (_payload(listing, "wacc", "0.11"),),
        listing,
        proposed_by="AI_RESEARCH",
    )
    assert ingest.status == "REJECTED"
    assert "wacc" in AI_FORBIDDEN_RESULT_FIELDS
    judged = EvidenceJudge().promote(
        evidence_item_from_component(_payload(listing, "wacc", "0.11"), listing)
    )
    assert judged.status != "VERIFIED"


def test_b_ai_beta_without_provenance_rejected() -> None:
    listing = _listing("WIPRO", "INE075A01022")
    ingest = ingest_researched_components(
        (_payload(listing, "beta", "1.05", source_url=""),),
        listing,
        proposed_by="gemini_find",
    )
    assert ingest.status == "REJECTED"
    q = qualify_capm_component(
        {"field": "beta", "value": "1.05", "source_url": "", "isin": listing.isin, "mic": listing.mic},
        listing,
        valuation_date=_VALUATION,
    )
    assert q.status == "REJECTED"
    assert q.wacc_eligible is False


def test_c_erp_without_methodology_or_date_rejected() -> None:
    listing = _listing("INFY", "INE009A01021")
    q = qualify_capm_component(
        {
            "field": "equity_risk_premium",
            "value": "0.05",
            "source_url": _RBI,
            "source_type": "regulator",
            "isin": listing.isin,
            "mic": listing.mic,
            "methodology": "",
            "as_of": None,
        },
        listing,
        valuation_date=_VALUATION,
    )
    assert q.status == "REJECTED"
    assert "methodology/date" in q.detail


def test_d_wrong_company_beta_rejected() -> None:
    listing = _listing("TCS", "INE467B01029")
    other = _listing("INFY", "INE009A01021")
    ingest = ingest_researched_components(
        (_payload(listing, "beta", "1.05", isin=other.isin),),
        listing,
        proposed_by="AI_RESEARCH",
    )
    assert ingest.rejected[0]["detail"] == "IDENTITY_FAIL"


def test_e_wrong_listing_beta_rejected() -> None:
    listing = _listing("TCS", "INE467B01029")
    ingest = ingest_researched_components(
        (_payload(listing, "beta", "1.05", mic="XBOM"),),
        listing,
        proposed_by="AI_RESEARCH",
    )
    assert ingest.rejected[0]["detail"] == "IDENTITY_FAIL"


def test_f_stale_beta_review_required() -> None:
    listing = _listing("RELIANCE", "INE002A01018")
    q = qualify_capm_component(
        _payload(
            listing,
            "beta",
            "1.10",
            as_of=date(2024, 1, 1),
            methodology="5y weekly vs Nifty 50 levered equity",
            period="2019-2024",
        ),
        listing,
        valuation_date=_VALUATION,
    )
    assert q.status == "REVIEW_REQUIRED"
    assert q.wacc_eligible is False
    assert q.freshness_status == "STALE"


def test_g_conflicting_erp_review_required() -> None:
    listing = _listing("TCS", "INE467B01029")
    result = research_dcf_assumptions(
        None,
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing, "equity_risk_premium", "0.055", evidence_ids=("a",)
            ),
            dcf_assumption_candidate(
                listing, "equity_risk_premium", "0.07", evidence_ids=("b",)
            ),
            dcf_assumption_candidate(listing, "risk_free_rate", "0.07", evidence_ids=("rf",)),
            dcf_assumption_candidate(listing, "beta", "1.0", evidence_ids=("beta",)),
        ),
        now=_NOW,
    )
    assert result.wacc_reconstruction["status"] == "REVIEW_REQUIRED"
    assert result.dsp_wacc is not None
    assert result.dsp_wacc.wacc is None


def test_j_wrong_currency_risk_free_rejected() -> None:
    from dataclasses import replace as dc_replace

    listing = dc_replace(_listing("TCS", "INE467B01029"), currency="USD")
    result = acquire_rbi_risk_free(
        listing,
        valuation_date=_VALUATION,
        document_text=_NSDP,
        mode="MOCK",
        now=_NOW,
    )
    assert result.status == "REJECTED"


def test_k_us_erp_rejected_for_indian_equity() -> None:
    listing = _listing("TCS", "INE467B01029")
    q = qualify_capm_component(
        _payload(
            listing,
            "equity_risk_premium",
            "0.05",
            methodology="historical US equity premium vs T-bonds",
            market="US",
            geography="US",
        ),
        listing,
        valuation_date=_VALUATION,
    )
    assert q.status == "REJECTED"
    judged = EvidenceJudge().promote(
        evidence_item_from_component(
            _payload(listing, "equity_risk_premium", "0.05", market="us_erp"),
            listing,
        )
    )
    assert judged.status == "REJECTED"


def test_l_ai_intrinsic_value_rejected() -> None:
    listing = _listing("INFY", "INE009A01021")
    ingest = ingest_researched_components(
        (_payload(listing, "intrinsic_value", "1234"),),
        listing,
        proposed_by="AI_RESEARCH",
    )
    assert ingest.status == "REJECTED"
    with pytest.raises(ValidationError):
        AnalyseRequest(ticker="TCS", intrinsic_value=1234)  # type: ignore[call-arg]


def test_m_external_wacc_does_not_override_dsp() -> None:
    dsp = calculate_dsp_wacc(
        risk_free_rate=Decimal("0.07"),
        beta=Decimal("1"),
        equity_risk_premium=Decimal("0.05"),
        equity_market_value=Decimal("100"),
        debt_market_value=Decimal("100"),
        pre_tax_cost_of_debt=Decimal("0.10"),
        tax_rate=Decimal("0.25"),
    )
    assert dsp.engine == DSP_WACC_ENGINE
    assert dsp.wacc == Decimal("0.0975")
    assert compare_external_wacc(dsp.wacc, Decimal("0.11")) == "REVIEW_REQUIRED"


def test_n_missing_beta_blocks_wacc() -> None:
    calculated = calculate_dsp_wacc(
        risk_free_rate=Decimal("0.07"),
        beta=None,
        equity_risk_premium=Decimal("0.05"),
        equity_market_value=Decimal("100"),
        debt_market_value=Decimal("0"),
        pre_tax_cost_of_debt=None,
        tax_rate=None,
    )
    assert calculated.status == "UNKNOWN"
    assert calculated.wacc is None


def test_o_missing_erp_blocks_wacc() -> None:
    calculated = calculate_dsp_wacc(
        risk_free_rate=Decimal("0.07"),
        beta=Decimal("1"),
        equity_risk_premium=None,
        equity_market_value=Decimal("100"),
        debt_market_value=Decimal("0"),
        pre_tax_cost_of_debt=None,
        tax_rate=None,
    )
    assert calculated.status == "UNKNOWN"
    assert calculated.wacc is None


def test_case1_complete_verified_components_dsp_wacc() -> None:
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
    assert calculated.engine == f"{compute_wacc.__module__}.{compute_wacc.__name__}"
    assert calculated.cost_of_equity == Decimal("0.12")
    assert calculated.wacc == Decimal("0.0975")
    source = (_ENGINE / "dsp_wacc.py").read_text(encoding="utf-8")
    assert "compute_rbi_wacc" not in source
    assert "compute_ai_wacc" not in (_ENGINE / "capm_components.py").read_text(encoding="utf-8")


def test_case2_ai_wacc_injection_dsp_retained() -> None:
    listing = _listing("INFY", "INE009A01021")
    s18 = _simple18()
    evidence = tuple(
        EvidenceJudge().promote(
            evidence_item_from_component(
                _payload(listing, name, value),
                listing,
                agent="official_filing_detail",
            )
        )
        for name, value in {
            "risk_free_rate": "0.07",
            "beta": "1.0",
            "equity_risk_premium": "0.05",
            "pre_tax_cost_of_debt": "0.10",
            "tax_rate": "0.25",
        }.items()
    )
    dataset = s18._dataset(
        listing,
        price=s18._price(listing),
        price_status="VERIFIED",
        shares=s18._shares(listing, value="1"),
        shares_status="VERIFIED",
        financials=s18._financials(
            cash=("0", "VERIFIED", date(2026, 3, 31)),
            debt=("100", "VERIFIED", date(2026, 3, 31)),
            equity=("100", "VERIFIED", date(2026, 3, 31)),
            cfo=("20", "VERIFIED", date(2026, 3, 31)),
            capex=("5", "VERIFIED", date(2026, 3, 31)),
            ebit=("8", "VERIFIED", date(2026, 3, 31)),
            net_income=("12", "VERIFIED", date(2026, 3, 31)),
            revenue=("100", "VERIFIED", date(2026, 3, 31)),
        ),
    )
    from dataclasses import replace as dc_replace

    dataset = dc_replace(dataset, evidence=evidence)
    result = research_dcf_assumptions(
        dataset,
        listing,
        proposals=(
            dcf_assumption_candidate(
                listing,
                "wacc",
                "0.11",
                proposed_by="AI_RESEARCH",
                source="ai_synthesis",
                evidence_ids=("ai",),
            ),
            dcf_assumption_candidate(listing, "terminal_growth_rate", "0.03", evidence_ids=("t",)),
            dcf_assumption_candidate(listing, "projection_years", "5", unit="years", evidence_ids=("y",)),
        ),
        now=_NOW,
    )
    assert result.dsp_wacc is not None
    assert result.dsp_wacc.wacc == Decimal("0.0975")
    assert result.dsp_wacc.engine == DSP_WACC_ENGINE
    assert result.wacc == Decimal("0.0975")
    assert any(
        item.name == "wacc" and item.status == "REJECTED"
        for item in result.rejected_assumptions
    )
    assert result.wacc_source != "ai_synthesis"
    # AI WACC is filtered before reconstruction; DSP remains the only calculated WACC.
    assert result.wacc_reconstruction.get("status") in {"NOT_APPLICABLE", "MATCH"}


def test_case5_unresolved_tenor_blocks_wacc_even_with_beta_erp() -> None:
    listing = _listing("TCS", "INE467B01029")
    result = analyse_listing(
        listing,
        mode="MOCK",
        rbi_document_text=_NSDP,
        research_horizon=_VALUATION,
        assumptions=(
            dcf_assumption_candidate(listing, "beta", "1.0", evidence_ids=("b",)),
            dcf_assumption_candidate(
                listing, "equity_risk_premium", "0.05", evidence_ids=("e",)
            ),
        ),
    )
    assert result.rbi_risk_free is not None
    assert result.rbi_risk_free.binding_status == "POLICY_GAP"
    assert result.assumption_research is not None
    assert result.assumption_research.wacc_status == "UNKNOWN"
    assert result.assumption_research.dcf_eligibility == "DCF_BLOCKED"


def test_case3_4_missing_components_block_dcf() -> None:
    listing = _listing("WIPRO", "INE075A01022")
    missing_beta = research_dcf_assumptions(
        None,
        listing,
        proposals=(
            dcf_assumption_candidate(listing, "risk_free_rate", "0.07", evidence_ids=("rf",)),
            dcf_assumption_candidate(
                listing, "equity_risk_premium", "0.05", evidence_ids=("erp",)
            ),
        ),
        now=_NOW,
    )
    assert missing_beta.dcf_eligibility == "DCF_BLOCKED"
    missing_erp = research_dcf_assumptions(
        None,
        listing,
        proposals=(
            dcf_assumption_candidate(listing, "risk_free_rate", "0.07", evidence_ids=("rf",)),
            dcf_assumption_candidate(listing, "beta", "1.0", evidence_ids=("b",)),
        ),
        now=_NOW,
    )
    assert missing_erp.dcf_eligibility == "DCF_BLOCKED"


def test_live_beta_erp_remain_unknown_without_new_provider() -> None:
    listing = _listing("TCS", "INE467B01029")
    capm = research_live_capm_components(
        listing,
        agent=UnavailableAgent(role="gemini_find"),
        valuation_date=_VALUATION,
        now=_NOW,
    )
    assert capm.ai_status == "NOT_CONFIGURED"
    assert capm.beta_status == "UNKNOWN"
    assert capm.erp_status == "UNKNOWN"
    status = live_macro_acquisition_status()
    assert status["beta"]["status"] == "UNKNOWN"
    assert status["equity_risk_premium"]["status"] == "UNKNOWN"
    none = research_components_from_agent(UnavailableAgent(role="gemini_find"), listing)
    assert none.detail == "NOT_CONFIGURED"


def test_yahoo_and_industry_beta_cannot_verify() -> None:
    listing = _listing("TCS", "INE467B01029")
    yahoo = qualify_capm_component(
        _payload(
            listing,
            "beta",
            "1.2",
            source_url="https://finance.yahoo.com/quote/TCS.NS",
            source_type="secondary",
            methodology="yahoo 5y monthly",
        ),
        listing,
        valuation_date=_VALUATION,
    )
    assert yahoo.status == "REJECTED"
    judged = EvidenceJudge().promote(
        evidence_item_from_component(
            _payload(listing, "beta", "1.1", beta_kind="industry_beta"),
            listing,
        )
    )
    assert judged.status == "REJECTED"


def test_universality_and_no_ticker_hardcoding() -> None:
    policy = tenor_policy_public_dict()
    assert policy["preferred_maturity"] is None
    for ticker, isin, mic in _NAMED:
        listing = _listing(ticker, isin, mic)
        rbi = acquire_rbi_risk_free(
            listing,
            valuation_date=_VALUATION,
            document_text=_NSDP,
            mode="MOCK",
            now=_NOW,
        )
        assert rbi.source_url == RBI_NSDP_URL
        assert rbi.binding_status == "POLICY_GAP"
        capm = research_live_capm_components(listing, valuation_date=_VALUATION, now=_NOW)
        assert capm.beta_status == "UNKNOWN"
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
    ][:4]
    assert len(dynamic) == 4
    for item in dynamic:
        listing = _listing(item.ticker, item.isin, item.mic)
        capm = research_live_capm_components(listing, valuation_date=_VALUATION, now=_NOW)
        assert capm.beta_status == "UNKNOWN"
        assert capm.erp_status == "UNKNOWN"
    bank = _listing("HDFCBANK", "INE040A01034")
    assert research_dcf_assumptions(None, bank, now=_NOW).dcf_eligibility == (
        "BANK_VALUATION_METHOD_REQUIRED"
    )
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
    banned = named
    for name in ("dcf_tenor_policy.py", "capm_components.py"):
        tree = ast.parse((_ENGINE / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in banned:
                raise AssertionError(f"{name} contains ticker {node.value}")


def test_dcf_formula_and_client_injection_unchanged() -> None:
    listing = _listing("TCS", "INE467B01029")
    s18 = _simple18()
    dsp = run_dsp_calculations(s18._happy(listing), listing=listing)
    assert dsp.margin_of_safety.formula == MOS_FORMULA
    with pytest.raises(ValidationError):
        AnalyseRequest(ticker="TCS", wacc=0.11)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        AnalyseRequest(ticker="TCS", beta=1.1)  # type: ignore[call-arg]


def test_analyse_exposes_capm_research_timings() -> None:
    listing = _listing("TCS", "INE467B01029")
    result = analyse_listing(
        listing,
        mode="MOCK",
        rbi_document_text=_NSDP,
        research_horizon=_VALUATION,
    )
    assert result.capm_components is not None
    assert result.capm_components.beta_status == "UNKNOWN"
    assert result.capm_components.tenor_policy["maturity_policy"] == "POLICY_GAP"
    assert "beta_retrieval" in result.timings
    assert "erp_retrieval" in result.timings
    assert "dsp_wacc" in result.timings