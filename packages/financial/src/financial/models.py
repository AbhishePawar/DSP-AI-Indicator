"""Aggregate financial statement models and versioned payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Sequence

from financial.balance_sheet import BalanceSheet
from financial.cash_flow import CashFlowStatement
from financial.income_statement import IncomeStatement
from financial.metadata import CompanyMetadata, StatementMetadata
from financial.period import FinancialPeriod

__all__ = [
    "FINANCIAL_VERSION",
    "FinancialStatements",
    "FinancialSnapshot",
]

FINANCIAL_VERSION = "0.7.0-financial"


@dataclass(frozen=True, slots=True)
class FinancialStatements:
    """One period's full statement triad (canonical container)."""

    period: FinancialPeriod
    income_statement: IncomeStatement = field(default_factory=IncomeStatement)
    balance_sheet: BalanceSheet = field(default_factory=BalanceSheet)
    cash_flow: CashFlowStatement = field(default_factory=CashFlowStatement)
    statement_metadata: StatementMetadata = field(default_factory=StatementMetadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period.to_dict(),
            "income_statement": self.income_statement.to_dict(),
            "balance_sheet": self.balance_sheet.to_dict(),
            "cash_flow": self.cash_flow.to_dict(),
            "statement_metadata": self.statement_metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinancialStatements:
        return cls(
            period=FinancialPeriod.from_dict(data["period"]),
            income_statement=IncomeStatement.from_dict(
                data.get("income_statement") or {}
            ),
            balance_sheet=BalanceSheet.from_dict(data.get("balance_sheet") or {}),
            cash_flow=CashFlowStatement.from_dict(data.get("cash_flow") or {}),
            statement_metadata=StatementMetadata.from_dict(
                data.get("statement_metadata") or {}
            ),
        )


@dataclass(frozen=True, slots=True)
class FinancialSnapshot:
    """Company-level multi-period financial snapshot (versioned payload root)."""

    company: CompanyMetadata = field(default_factory=CompanyMetadata)
    statements: tuple[FinancialStatements, ...] = ()
    version: str = FINANCIAL_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "company": self.company.to_dict(),
            "statements": [s.to_dict() for s in self.statements],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinancialSnapshot:
        stmts_raw = data.get("statements") or ()
        statements = tuple(
            FinancialStatements.from_dict(s) for s in stmts_raw
        )
        return cls(
            company=CompanyMetadata.from_dict(data.get("company") or {}),
            statements=statements,
            version=str(data.get("version") or FINANCIAL_VERSION),
        )

    @classmethod
    def from_json(cls, text: str) -> FinancialSnapshot:
        return cls.from_dict(json.loads(text))

    def with_statements(
        self, statements: Sequence[FinancialStatements]
    ) -> FinancialSnapshot:
        return FinancialSnapshot(
            company=self.company,
            statements=tuple(statements),
            version=self.version,
        )
