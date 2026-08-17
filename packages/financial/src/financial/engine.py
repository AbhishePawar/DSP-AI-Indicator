"""FinancialEngine — validate / normalize / serialize / analyze statements."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from financial.balance_sheet import BalanceSheet
from financial.cash_flow import CashFlowStatement
from financial.currency import CurrencyCode, CurrencyRef
from financial.derivation import (
    DerivationInput,
    DerivedFinancialValue,
    FinancialDerivationEngine,
)
from financial.income_statement import IncomeStatement
from financial.intelligence.aggregator_engine import FinancialAggregatorEngine
from financial.intelligence.aggregator_models import FinancialAnalysis
from financial.intelligence.balance_engine import BalanceSheetEngine
from financial.intelligence.balance_models import BalanceSheetAnalysis
from financial.intelligence.cashflow_engine import CashFlowEngine
from financial.intelligence.cashflow_models import CashFlowAnalysis
from financial.intelligence.income_engine import IncomeStatementEngine
from financial.intelligence.income_models import IncomeStatementAnalysis
from financial.intelligence.ratio_engine import FinancialRatioEngine
from financial.intelligence.ratio_models import FinancialRatioAnalysis
from financial.intelligence.trend_engine import TrendEngine
from financial.intelligence.trend_models import (
    FinancialStatementsHistory,
    TrendAnalysis,
)
from financial.metadata import UnitScale
from financial.models import FINANCIAL_VERSION, FinancialSnapshot, FinancialStatements
from financial.normalization import normalize_snapshot
from financial.validation import ValidationResult, validate_snapshot

__all__ = ["FinancialEngine", "FINANCIAL_VERSION"]


class FinancialEngine:
    """Domain façade for Financial Statement Intelligence (F2.1–F2.7)."""

    def __init__(self) -> None:
        self._income_engine = IncomeStatementEngine()
        self._balance_engine = BalanceSheetEngine()
        self._cashflow_engine = CashFlowEngine()
        self._ratio_engine = FinancialRatioEngine()
        self._trend_engine = TrendEngine()
        self._aggregator_engine = FinancialAggregatorEngine()
        self._derivation_engine = FinancialDerivationEngine()

    def validate(
        self,
        snapshot: FinancialSnapshot,
        *,
        accounting_tolerance: float = 1e-6,
        require_revenue: bool = False,
        require_total_assets: bool = False,
    ) -> ValidationResult:
        return validate_snapshot(
            snapshot,
            accounting_tolerance=accounting_tolerance,
            require_revenue=require_revenue,
            require_total_assets=require_total_assets,
        )

    def normalize(
        self,
        snapshot: FinancialSnapshot,
        *,
        target_scale: UnitScale = UnitScale.ACTUAL,
        target_currency: CurrencyRef | CurrencyCode | str | None = None,
    ) -> FinancialSnapshot:
        return normalize_snapshot(
            snapshot,
            target_scale=target_scale,
            target_currency=target_currency,
        )

    def serialize(self, snapshot: FinancialSnapshot) -> dict[str, Any]:
        return snapshot.to_dict()

    def serialize_json(
        self, snapshot: FinancialSnapshot, *, indent: int | None = None
    ) -> str:
        return snapshot.to_json(indent=indent)

    def deserialize(self, payload: dict[str, Any] | str) -> FinancialSnapshot:
        if isinstance(payload, str):
            return FinancialSnapshot.from_json(payload)
        return FinancialSnapshot.from_dict(payload)

    def analyze_income_statement(
        self,
        source: IncomeStatement
        | FinancialStatements
        | FinancialSnapshot
        | dict
        | Sequence[IncomeStatement | FinancialStatements],
        *,
        history: Sequence[IncomeStatement | FinancialStatements] | None = None,
    ) -> IncomeStatementAnalysis:
        return self._income_engine.analyze(source, history=history)

    def analyze_balance_sheet(
        self,
        source: BalanceSheet
        | FinancialStatements
        | FinancialSnapshot
        | dict
        | Sequence[BalanceSheet | FinancialStatements],
        *,
        history: Sequence[BalanceSheet | FinancialStatements] | None = None,
        allow_negative_equity: bool = False,
    ) -> BalanceSheetAnalysis:
        return self._balance_engine.analyze(
            source,
            history=history,
            allow_negative_equity=allow_negative_equity,
        )

    def analyze_cash_flow(
        self,
        source: CashFlowStatement
        | FinancialStatements
        | FinancialSnapshot
        | dict
        | Sequence[CashFlowStatement | FinancialStatements],
        *,
        history: Sequence[CashFlowStatement | FinancialStatements] | None = None,
    ) -> CashFlowAnalysis:
        return self._cashflow_engine.analyze(source, history=history)

    def analyze_financial_ratios(
        self,
        source: FinancialStatements
        | FinancialSnapshot
        | dict
        | Sequence[FinancialStatements],
        *,
        history: Sequence[FinancialStatements] | None = None,
    ) -> FinancialRatioAnalysis:
        return self._ratio_engine.analyze(source, history=history)

    def analyze_trends(
        self,
        source: FinancialStatementsHistory
        | FinancialSnapshot
        | dict
        | Sequence[FinancialStatements],
    ) -> TrendAnalysis:
        """Run Trend & Time-Series Intelligence (F2.6)."""
        return self._trend_engine.analyze(source)

    def analyze_financials(
        self,
        source: FinancialStatements
        | FinancialStatementsHistory
        | Sequence[FinancialStatements],
    ) -> FinancialAnalysis:
        """Primary entry: aggregate F2.2–F2.6 into ``FinancialAnalysis`` (F2.7)."""
        return self._aggregator_engine.analyze(source)

    def reported_value(self, item: DerivationInput) -> DerivedFinancialValue:
        """Preserve a provider-reported field (never relabel calculated as reported)."""
        return self._derivation_engine.reported(item)

    def derive(
        self,
        formula_id: str,
        inputs: Mapping[str, DerivationInput] | Sequence[DerivationInput],
    ) -> DerivedFinancialValue:
        """Deterministic derivation: calculated or unavailable — never guessed."""
        return self._derivation_engine.derive(formula_id, inputs)
