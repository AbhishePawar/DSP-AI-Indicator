"""SIMPLE-25 — universal DCF completion and assumption validation. Fail-closed is success."""

from __future__ import annotations

import importlib.util
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter

import pytest

from data_engine.official_research.assumption_contract import (
    DATA_CLASS_ASSUMPTION,
    DATA_CLASS_DERIVED,
    DATA_CLASS_FACT,
    assumption,
    classify_data_class,
)
from data_engine.official_research.assumption_validator import (
    refuse_ai_fact,
    validate_assumption_pack,
)
from data_engine.official_research.derived_fields import derive_dsp_fields
from data_engine.official_research.dsp_calculation import (
    MOS_FORMULA,
    describe_dcf_blockers,
    ignore_ai_valuation,
    run_dsp_calculations,
)
from data_engine.official_research.end_to_end import AUTO_REQUEST_GROUPS
from data_engine.official_research.extraction import (
    classify_capex_semantic,
    extract_classified_capex,
    extract_labeled_field,
)
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import EvidenceItem, ResearchRequest, new_evidence_id, utc_now
from data_engine.official_research.nse_eod import NseEodService, NsePublicHttp
from data_engine.official_research.nse_mcp import NSE_MCP_COMMERCIAL_STATUS
from data_engine.official_research.nse_primary import NsePrimaryEvidenceService
from data_engine.official_research.orchestrator import ResearchOrchestrator
from data_engine.official_research.research_plan import classify_research_capability
from data_engine.official_research.xbrl import extract_xbrl_fields
from data_engine.security_master import SecurityMasterService, load_default_catalog
from data_engine.security_master.models import SecurityListing
from llm_adapters.config import load_llm_config

_ENGINE = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
_PRIOR_TICKERS = (
    "TCS",
    "INFY",
    "RELIANCE",
    "HDFCBANK",
    "WIPRO",
    "20MICRONS",
    "AADHARHFC",
    "3IINFOLTD",
    "A2ZINFRA",
    "ABFRL",
    "21STCENMGM",
    "APOORVA",
    "ADROITINFO",
    "ABINFRA",
    "ADFFOODS",
    "360ONE",
)


def _master() -> SecurityMasterService:
    return SecurityMasterService(load_default_catalog())


def _listing_by_ticker(ticker: str) -> SecurityListing:
    for item in load_default_catalog().all():
        if item.ticker == ticker and item.mic == "XNSE" and item.eligibility:
            return item
    raise AssertionError(f"catalog missing eligible XNSE equity {ticker}")


def _listing(ticker: str, isin: str, mic: str = "XNSE") -> SecurityListing:
    resolved = _master().resolve(isin, isin=isin, mic=mic)
    assert resolved.status == "RESOLVED" and resolved.identity is not None
    return resolved.identity

_LIVE_COVERAGE: list[dict[str, str]] = []
_DYNAMIC: list[str] = []

_PPE_XBRL = """<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in-bse-fin="http://www.bseindia.com/xbrl/fin">
  <xbrli:context id="FourDConsolidated">
    <xbrli:entity>
      <xbrli:identifier scheme="http://www.nseindia.com/isin">INE009A01021</xbrli:identifier>
    </xbrli:entity>
    <xbrli:period>
      <xbrli:startDate>2023-04-01</xbrli:startDate>
      <xbrli:endDate>2024-03-31</xbrli:endDate>
    </xbrli:period>
  </xbrli:context>
  <xbrli:unit id="INR"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>
  <in-bse-fin:CashFlowsFromUsedInOperatingActivities contextRef="FourDConsolidated" unitRef="INR">252100000000.00</in-bse-fin:CashFlowsFromUsedInOperatingActivities>
  <in-bse-fin:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities contextRef="FourDConsolidated" unitRef="INR">22010000000.00</in-bse-fin:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities>
  <in-bse-fin:CashFlowsFromUsedInInvestingActivities contextRef="FourDConsolidated" unitRef="INR">-50090000000.00</in-bse-fin:CashFlowsFromUsedInInvestingActivities>
  <in-bse-fin:CashFlowsUsedInObtainingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities contextRef="FourDConsolidated" unitRef="INR">1010000000.00</in-bse-fin:CashFlowsUsedInObtainingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities>
  <in-bse-fin:RevenueFromOperations contextRef="FourDConsolidated" unitRef="INR">1536700000000.00</in-bse-fin:RevenueFromOperations>
</xbrl>
"""

_CF_TEXT = (
    "unit: actual\nas_of: 2024-03-31\nconsolidated\n"
    "statement of cash flows\n"
    "net cash from operating activities: 252100000000\n"
    "purchase of property, plant and equipment: 22010000000\n"
    "cash flows from used in investing activities: -50090000000\n"
)


def _kind(listing: SecurityListing) -> str:
    name = listing.company_name.lower()
    if "bank" in name:
        return "bank"
    if "finance" in name or "nbfc" in name or "housing" in name:
        return "financial"
    if any(token in name for token in ("software", "infotech", "technology", "consult")):
        return "technology"
    return "other"


def _dynamic_listings(count: int = 5, *, skip: set[str] | None = None) -> list[SecurityListing]:
    blocked = set(skip or ())
    picked: list[SecurityListing] = []
    for item in load_default_catalog().all():
        if not item.eligibility or item.mic != "XNSE" or item.security_type != "equity":
            continue
        if item.ticker in blocked:
            continue
        picked.append(item)
        if len(picked) >= count:
            break
    assert len(picked) >= count
    return picked[:count]


def _simple18():
    path = Path(__file__).with_name("test_simple18.py")
    spec = importlib.util.spec_from_file_location("simple18_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture_assumptions():
    return (
        assumption(
            "discount_rate",
            "0.10",
            source="primary_research",
            evidence_ids=("fixture-horizon",),
            reasoning="universal test pack; not a company fact",
        ),
        assumption(
            "fcf_growth_rate",
            "0.08",
            source="historical_company_performance",
            evidence_ids=("fixture-history",),
            reasoning="universal test pack; not a company fact",
        ),
        assumption(
            "terminal_growth_rate",
            "0.03",
            source="macro_data",
            evidence_ids=("fixture-macro",),
            reasoning="universal test pack; not a company fact",
        ),
        assumption(
            "projection_years",
            "5",
            unit="years",
            source="primary_research",
            evidence_ids=("fixture-horizon",),
        ),
    )


def test_ppe_xbrl_is_capex_investing_total_is_not() -> None:
    parsed = extract_xbrl_fields(_PPE_XBRL.encode("utf-8"), isin="INE009A01021")
    assert parsed.fields["cfo"].value == "252100000000.00"
    assert parsed.fields["capex"].value == "22010000000.00"
    assert "PurchaseOfPropertyPlantAndEquipment" in parsed.fields["capex"].locator
    assert "-50090000000" not in (parsed.fields["capex"].value or "")
    assert parsed.fields["cfo"].as_of == parsed.fields["capex"].as_of
    assert parsed.fields["cfo"].statement_basis == parsed.fields["capex"].statement_basis


def test_labeled_capex_still_requires_explicit_words() -> None:
    ppe = "unit: actual\nas_of: 2026-03-31\npurchase of property, plant and equipment: 50"
    assert extract_labeled_field(ppe, "capex") is None
    classified = extract_classified_capex(_CF_TEXT)
    assert classified is not None
    assert classified.value == "22010000000"
    assert classified.semantic_status == "VERIFIED"
    investing_only = (
        "unit: actual\nas_of: 2024-03-31\nconsolidated\n"
        "statement of cash flows\n"
        "cash flows from used in investing activities: -50090000000\n"
    )
    assert extract_classified_capex(investing_only) is None
    negative = (
        "unit: actual\nas_of: 2024-03-31\nconsolidated\n"
        "statement of cash flows\n"
        "purchase of property, plant and equipment: -22010000000\n"
    )
    signed = extract_classified_capex(negative)
    assert signed is not None
    assert signed.value.startswith("-")


def test_capex_semantics_reject_acquisitions_and_investing_total() -> None:
    assert classify_capex_semantic("capital expenditure") == "CAPITAL_EXPENDITURE"
    assert classify_capex_semantic(
        "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"
    ) == "PPE_PURCHASE"
    assert classify_capex_semantic("cash flows from used in investing activities") == (
        "OTHER_INVESTING"
    )
    assert classify_capex_semantic("purchase of investments") == "INVESTMENT"
    assert classify_capex_semantic("acquisition of subsidiary") == "ACQUISITION"
    assert classify_capex_semantic("purchase of intangible assets") == "INTANGIBLE_PURCHASE"


def test_assumptions_are_not_facts_and_not_hidden() -> None:
    assert classify_data_class("capex") == DATA_CLASS_FACT
    assert classify_data_class("fcf") == DATA_CLASS_DERIVED
    assert classify_data_class("wacc") == DATA_CLASS_ASSUMPTION
    pack = validate_assumption_pack(_fixture_assumptions())
    assert all(item.accepted for item in pack)
    empty = validate_assumption_pack(())
    assert empty == ()


def test_assumption_conflicts_are_not_averaged() -> None:
    pack = validate_assumption_pack(
        (
            assumption("fcf_growth_rate", "0.08", source="primary_research", evidence_ids=("a",)),
            assumption("fcf_growth_rate", "0.18", source="ai_synthesis", evidence_ids=("b",)),
            assumption("discount_rate", "0.10", source="primary_research", evidence_ids=("a",)),
            assumption("terminal_growth_rate", "0.03", source="macro_data", evidence_ids=("c",)),
        )
    )
    growth = [item for item in pack if item.assumption.field == "fcf_growth_rate"]
    assert all(item.status == "REVIEW_REQUIRED" for item in growth)
    assert {item.assumption.value for item in growth} == {Decimal("0.08"), Decimal("0.18")}


def test_ai_cannot_write_capex_or_iv() -> None:
    assert refuse_ai_fact("capex", proposed_by="openai") == "REJECTED"
    assert ignore_ai_valuation(Decimal("999")) is None
    listing = _listing("INFY", "INE009A01021")
    raw = EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field="capex",
        value="1",
        as_of=date(2024, 3, 31),
        retrieved_at=utc_now(),
        source="OpenAI",
        source_type="llm",
        source_url=None,
        document_date=date(2024, 3, 31),
        evidence_locator="hallucinated capex",
        currency="INR",
        unit="actual",
        statement_basis="consolidated",
        agent="openai",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence="high",
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
    )
    assert EvidenceJudge().promote(raw).status != "VERIFIED"
    nse = EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field="capex",
        value="22010000000",
        as_of=date(2024, 3, 31),
        retrieved_at=utc_now(),
        source="NSE",
        source_type="regulator",
        source_url="https://nsearchives.nseindia.com/annual.pdf",
        document_date=date(2024, 3, 31),
        evidence_locator="PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
        currency="INR",
        unit="actual",
        statement_basis="consolidated",
        agent="official_nse_primary",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence="high",
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
    )
    decision = EvidenceJudge().reconcile_candidates((nse, raw), field="capex", listing=listing)
    assert decision.chosen is not None
    assert decision.chosen.value == "22010000000"
    assert decision.conflict_class == "AI_CLAIM_REJECTED"


def test_wacc_must_exceed_terminal_and_mos_formula_unchanged() -> None:
    pack = validate_assumption_pack(
        (
            assumption("discount_rate", "0.02", source="primary_research", evidence_ids=("a",)),
            assumption("fcf_growth_rate", "0.01", source="primary_research", evidence_ids=("a",)),
            assumption("terminal_growth_rate", "0.03", source="macro_data", evidence_ids=("a",)),
        )
    )
    assert any(
        item.status == "REJECTED" and "WACC" in item.detail
        for item in pack
        if item.assumption.field in {"discount_rate", "terminal_growth_rate"}
    )
    assert MOS_FORMULA == (
        "(intrinsic_value_per_share - market_price_per_share) / intrinsic_value_per_share"
    )


def test_dcf_reproducible_with_identical_inputs() -> None:
    helpers = _simple18()
    listing = _listing("TCS", "INE467B01029")
    dataset = helpers._happy(listing)
    pack = _fixture_assumptions()
    first = run_dsp_calculations(dataset, assumptions=pack, listing=listing)
    second = run_dsp_calculations(dataset, assumptions=pack, listing=listing)
    assert first.dcf.status == "CALCULATED"
    assert first.dcf.value == second.dcf.value
    assert first.dcf.extras["fcf0"] == second.dcf.extras["fcf0"]
    assert first.dcf.extras["pv_terminal"] == second.dcf.extras["pv_terminal"]
    assert first.intrinsic_value_per_share.value == second.intrinsic_value_per_share.value
    assert first.margin_of_safety.value == second.margin_of_safety.value
    derived = derive_dsp_fields(dataset)
    assert derived.fcf.status == "CALCULATED"
    assert derived.fcf.value == Decimal("15")
    assert derived.net_debt.value == Decimal("-30")


def test_missing_capex_is_not_substituted_with_zero() -> None:
    helpers = _simple18()
    listing = _listing("TCS", "INE467B01029")
    dataset = helpers._dataset(
        listing,
        price=helpers._price(listing),
        price_status="VERIFIED",
        shares=helpers._shares(listing),
        shares_status="VERIFIED",
        financials=helpers._financials(
            cfo=("20", "VERIFIED", date(2026, 3, 31)),
            capex=(None, "UNAVAILABLE", None),
        ),
    )
    derived = derive_dsp_fields(dataset)
    assert derived.fcf.status != "CALCULATED"
    assert derived.fcf.value is None
    dsp = run_dsp_calculations(dataset, assumptions=_fixture_assumptions(), listing=listing)
    assert dsp.dcf.status != "CALCULATED"
    mismatched = helpers._dataset(
        listing,
        price=helpers._price(listing),
        price_status="VERIFIED",
        shares=helpers._shares(listing),
        shares_status="VERIFIED",
        financials=helpers._financials(
            cfo=("20", "VERIFIED", date(2026, 3, 31)),
            capex=("5", "VERIFIED", date(2025, 3, 31)),
        ),
    )
    assert derive_dsp_fields(mismatched).fcf.status == "CALCULATION_BLOCKED"
    signed = helpers._dataset(
        listing,
        price=helpers._price(listing),
        price_status="VERIFIED",
        shares=helpers._shares(listing),
        shares_status="VERIFIED",
        financials=helpers._financials(
            cfo=("20", "VERIFIED", date(2026, 3, 31)),
            capex=("-5", "VERIFIED", date(2026, 3, 31)),
        ),
    )
    assert derive_dsp_fields(signed).fcf.value == Decimal("15")


def test_architecture_no_company_dcf_branches() -> None:
    for path in _ENGINE.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "if ticker ==" not in text
        if path.name in {
            "xbrl.py",
            "dsp_calculation.py",
            "assumption_validator.py",
            "extraction.py",
            "acquisition.py",
        }:
            for token in ("TCS", "INFY", "RELIANCE", "HDFCBANK", "WIPRO"):
                assert token not in text
    assert NSE_MCP_COMMERCIAL_STATUS == "COMMERCIAL_USE_PENDING"
    cfg = load_llm_config()
    if not cfg.openai_api_key:
        return


def test_browser_is_parked() -> None:
    pytest.skip("FRONTEND PARKED: SIMPLE-25 is DCF input-completion only")


def _skip_live() -> None:
    if os.environ.get("DSP_SKIP_LIVE_NSE_EOD") == "1":
        pytest.skip("LIVE NSE skipped by DSP_SKIP_LIVE_NSE_EOD=1")


def _status(dataset, name: str) -> str:
    if dataset is None:
        return "UNKNOWN"
    if name == "price":
        return dataset.price_status
    if name == "shares":
        return dataset.shares_status
    return dataset.field_status(name)


def _coverage_row(listing: SecurityListing, result, *, with_assumptions) -> dict[str, str]:
    dataset = result.dataset
    dsp = with_assumptions
    capex = _status(dataset, "capex")
    cfo = _status(dataset, "cfo")
    dcf = "BLOCKED"
    if dsp is not None and dsp.dcf.status == "CALCULATED":
        dcf = "RUN"
    elif dsp is not None:
        dcf = dsp.dcf.status
    replayed = dsp is not None
    blockers = describe_dcf_blockers(
        dataset,
        dsp if dsp is not None else result.dsp,
        capability=classify_research_capability(listing),
        assumptions_accepted=replayed,
    )
    return {
        "security": listing.ticker,
        "identity": result.identity_status,
        "price": _status(dataset, "price"),
        "shares": _status(dataset, "shares"),
        "revenue": _status(dataset, "revenue"),
        "net_income": _status(dataset, "net_income"),
        "cfo": cfo,
        "capex": capex,
        "cash": _status(dataset, "cash"),
        "debt": _status(dataset, "debt"),
        "assumptions": "ACCEPTED" if replayed else "USER_REQUIRED",
        "dcf": dcf,
        "blocker": ";".join(blockers),
        "kind": _kind(listing),
        "mode": "UNKNOWN" if dataset is None else dataset.mode,
    }


@pytest.mark.network
def test_live_dcf_completion_prior_and_new_dynamic() -> None:
    global _DYNAMIC
    _skip_live()
    transport = NsePublicHttp(timeout_seconds=30.0)
    nse_eod = NseEodService(transport, mode="LIVE")
    nse_primary = NsePrimaryEvidenceService(transport, mode="LIVE")
    try:
        bundle = nse_eod.fetch_latest()
    except LookupError as exc:
        pytest.skip(f"LIVE NSE EOD not reachable: {exc}")
    orch = ResearchOrchestrator(
        security_master=_master(),
        nse_eod=nse_eod,
        nse_primary=nse_primary,
        production=False,
    )
    listings = [_listing_by_ticker(ticker) for ticker in _PRIOR_TICKERS]
    extra = _dynamic_listings(5, skip=set(_PRIOR_TICKERS))
    _DYNAMIC = [item.ticker for item in extra]
    listings.extend(extra)
    pack = _fixture_assumptions()
    samples: list[float] = []
    dcf_times: list[float] = []
    for listing in listings:
        started = perf_counter()
        result = orch.analyse(
            ResearchRequest(
                ticker=listing.ticker,
                company=listing.company_name,
                isin=listing.isin,
                mic=listing.mic,
                exchange=listing.exchange,
                fields=AUTO_REQUEST_GROUPS,
                mode="LIVE",
            ),
            nse_bundle=bundle,
        )
        samples.append(perf_counter() - started)
        assert result.production is False
        assert result.identity_status == "VERIFIED"
        if result.dsp is not None:
            assert result.dsp.dcf.status != "CALCULATED"
        mark = perf_counter()
        replay = None
        if result.dataset is not None:
            replay = run_dsp_calculations(
                result.dataset, assumptions=pack, listing=listing
            )
        dcf_times.append(perf_counter() - mark)
        row = _coverage_row(listing, result, with_assumptions=replay)
        if result.dsp is not None and result.dsp.dcf.status == "CALCULATED":
            raise AssertionError("production path must not inject DCF assumptions")
        _LIVE_COVERAGE.append(row)
        if row["dcf"] == "RUN":
            assert row["cfo"] == "VERIFIED"
            assert row["capex"] == "VERIFIED"
            assert replay is not None
            assert replay.margin_of_safety.formula == MOS_FORMULA
    assert len(_DYNAMIC) == 5
    assert set(_DYNAMIC).isdisjoint(set(_PRIOR_TICKERS))
    ordered = sorted(samples)
    calc = sorted(dcf_times)
    print("SIMPLE-25 LIVE coverage:", _LIVE_COVERAGE)
    print("SIMPLE-25 new dynamic securities:", _DYNAMIC)
    print(
        "SIMPLE-25 analyse p50/p95:",
        ordered[len(ordered) // 2],
        ordered[-1] if ordered else None,
    )
    print(
        "SIMPLE-25 DCF calc p50/p95:",
        calc[len(calc) // 2],
        calc[-1] if calc else None,
    )
    assert all(row["identity"] == "VERIFIED" for row in _LIVE_COVERAGE)
    assert all(row["mode"] in {"LIVE", "UNKNOWN"} for row in _LIVE_COVERAGE)
    hdfc = next(row for row in _LIVE_COVERAGE if row["security"] == "HDFCBANK")
    assert "ordinary DCF not applicable" in hdfc["blocker"] or hdfc["dcf"] != "RUN"
    for row in _LIVE_COVERAGE:
        if row["shares"] != "VERIFIED" and row["dcf"] == "RUN":
            continue
        if row["dcf"] != "RUN":
            assert row["blocker"] != "NONE"
