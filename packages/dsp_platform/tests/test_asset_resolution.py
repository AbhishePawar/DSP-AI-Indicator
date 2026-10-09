from contracts.enums import AssetClass
from dsp_platform.asset_resolution import (
    AssetResolutionService,
    resolve_asset,
)
from dsp_platform.platform import DSPPlatform


def test_resolve_equity_by_name() -> None:
    asset = resolve_asset("Tata Motors")
    assert asset is not None
    assert asset.symbol == "TATAMOTORS"
    assert asset.asset_class is AssetClass.EQUITY
    assert asset.exchange in ("NSE", "BSE")
    assert asset.bse_code == "500570"
    assert asset.dual_listed is True
    assert asset.allows_equity_valuation is True
    assert asset.allows_buffett_analysis is True
    assert asset.allows_commodity_research is False


def test_resolve_equity_by_bse_code() -> None:
    asset = resolve_asset("500570")
    assert asset is not None
    assert asset.symbol == "TATAMOTORS"
    assert asset.exchange == "BSE"
    assert asset.bse_code == "500570"
    assert asset.allows_equity_valuation is True


def test_resolve_commodities_with_contracts_and_units() -> None:
    gold = resolve_asset("Gold")
    assert gold is not None
    assert gold.symbol == "GOLD"
    assert gold.asset_class is AssetClass.COMMODITY
    assert gold.exchange == "MCX"
    assert gold.currency == "INR"
    assert "10 grams" in gold.unit
    assert gold.allows_equity_valuation is False
    assert gold.allows_buffett_analysis is False
    assert gold.allows_commodity_research is True
    assert len(gold.macro_drivers) > 0

    crude = resolve_asset("Crude Oil")
    assert crude is not None
    assert crude.symbol == "CRUDEOIL"
    assert crude.asset_class is AssetClass.COMMODITY
    assert crude.exchange == "MCX"
    assert "barrel" in crude.unit
    assert crude.allows_equity_valuation is False
    assert crude.allows_commodity_research is True


def test_resolve_indices() -> None:
    nifty = resolve_asset("Nifty 50")
    assert nifty is not None
    assert nifty.symbol == "NIFTY50"
    assert nifty.asset_class is AssetClass.INDEX
    assert nifty.exchange == "NSE"


def test_ambiguity_detection_and_candidates() -> None:
    amb = resolve_asset("Tata")
    assert amb is not None
    assert amb.ambiguous is True
    assert len(amb.candidates) >= 2
    symbols = [c["symbol"] for c in amb.candidates]
    assert "TATAMOTORS" in symbols
    assert "TCS" in symbols or "TATASTEEL" in symbols


def test_ticker_fallback_and_invalid_queries() -> None:
    valid_ticker = resolve_asset("MYTICKER")
    assert valid_ticker is not None
    assert valid_ticker.symbol == "MYTICKER"
    assert valid_ticker.asset_class is AssetClass.EQUITY

    empty = resolve_asset("")
    assert empty is None

    whitespace = resolve_asset("   ")
    assert whitespace is None


def test_platform_orchestrator_integration() -> None:
    orchestrator = DSPPlatform()
    res = orchestrator.resolve_asset_identity("Gold")
    assert res is not None
    assert res["symbol"] == "GOLD"
    assert res["asset_class"] == "commodity"
    assert res["analytical_eligibility"]["commodity_research"] is True
    assert res["analytical_eligibility"]["equity_valuation"] is False

    comp = orchestrator.resolve_company_identity("Tata Motors")
    assert comp is not None
    assert comp["symbol"] == "TATAMOTORS"
