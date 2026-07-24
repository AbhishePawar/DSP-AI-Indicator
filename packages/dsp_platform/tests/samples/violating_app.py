"""Violating application sample — must fail boundary checks."""

from data_engine.services import MarketDataService
from dsp import IndicatorEngine
from orchestration import InvestmentAnalysisService
from valuation import ValuationEngine

_ = (MarketDataService, IndicatorEngine, InvestmentAnalysisService, ValuationEngine)
