"""Financial Statement Domain tests — target 100% module coverage."""

from __future__ import annotations

from datetime import date

import pytest

from financial import (
    FINANCIAL_VERSION,
    AccountingStandard,
    BalanceSheet,
    CashFlowStatement,
    CompanyMetadata,
    CurrencyCode,
    CurrencyRef,
    FinancialEngine,
    FinancialError,
    FinancialPeriod,
    FinancialSnapshot,
    FinancialStatements,
    FinancialValidationError,
    IncomeStatement,
    PeriodType,
    StatementMetadata,
    UnitScale,
    canonicalize_field_name,
    map_raw_fields,
    normalize_snapshot,
    normalize_statements,
    scale_values,
    statements_from_raw,
    validate_snapshot,
    validate_statements,
)
from financial.validation import ValidationResult


def _period(**kwargs) -> FinancialPeriod:
    data = dict(
        period_type=PeriodType.ANNUAL,
        period_end=date(2024, 12, 31),
        fiscal_year=2024,
        currency=CurrencyRef(CurrencyCode.USD),
        audited=True,
        source="test",
    )
    data.update(kwargs)
    return FinancialPeriod(**data)


def _balanced_bs(**kwargs) -> BalanceSheet:
    data = dict(
        cash=100.0,
        total_assets=1000.0,
        total_liabilities=400.0,
        total_equity=600.0,
        equity=600.0,
    )
    data.update(kwargs)
    return BalanceSheet(**data)


def _stmt(**kwargs) -> FinancialStatements:
    data = dict(
        period=_period(),
        income_statement=IncomeStatement(revenue=500.0, net_income=50.0),
        balance_sheet=_balanced_bs(),
        cash_flow=CashFlowStatement(
            operating_cash_flow=80.0, capex=-20.0, free_cash_flow=60.0
        ),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )
    data.update(kwargs)
    return FinancialStatements(**data)


def _snapshot(*stmts: FinancialStatements) -> FinancialSnapshot:
    return FinancialSnapshot(
        company=CompanyMetadata(
            company="Example Co",
            ticker="EXM",
            exchange="NYSE",
            sector="Technology",
            industry="Software",
            country="US",
            accounting_standard=AccountingStandard.US_GAAP,
        ),
        statements=stmts or (_stmt(),),
    )


class TestPeriodCurrencyMetadata:
    def test_period_roundtrip(self) -> None:
        p = _period(
            period_type=PeriodType.QUARTERLY,
            fiscal_quarter=2,
            reporting_date=date(2024, 8, 1),
            period_length_days=91,
            restated=True,
        )
        d = p.to_dict()
        p2 = FinancialPeriod.from_dict(d)
        assert p2.period_type is PeriodType.QUARTERLY
        assert p2.fiscal_quarter == 2
        assert p2.reporting_date == date(2024, 8, 1)
        assert p2.key()[0] == "quarterly"

    def test_period_currency_string(self) -> None:
        p = FinancialPeriod.from_dict(
            {
                "period_type": "ttm",
                "period_end": "2024-06-30",
                "currency": "INR",
            }
        )
        assert p.period_type is PeriodType.TTM
        assert p.currency.code is CurrencyCode.INR

    def test_currency_parse(self) -> None:
        assert CurrencyRef.parse(None).code is CurrencyCode.USD
        assert CurrencyRef.parse(CurrencyCode.EUR).code is CurrencyCode.EUR
        assert CurrencyRef.parse(CurrencyRef(CurrencyCode.GBP)).code is CurrencyCode.GBP
        assert CurrencyRef.parse("").code is CurrencyCode.USD
        other = CurrencyRef.parse("XYZ")
        assert other.code is CurrencyCode.OTHER
        assert other.label == "XYZ"
        assert CurrencyRef.from_dict({"code": "???","label": "x"}).code is CurrencyCode.OTHER

    def test_company_metadata(self) -> None:
        m = CompanyMetadata(
            company="A",
            ticker="A",
            isin="US000",
            accounting_standard=AccountingStandard.IFRS,
            reporting_currency=CurrencyRef(CurrencyCode.EUR),
        )
        m2 = CompanyMetadata.from_dict(m.to_dict())
        assert m2.accounting_standard is AccountingStandard.IFRS
        assert m2.reporting_currency.code is CurrencyCode.EUR
        weird = CompanyMetadata.from_dict({"accounting_standard": "local-gaap"})
        assert weird.accounting_standard is AccountingStandard.OTHER
        sm = StatementMetadata.from_dict(
            {"unit_scale": "billions", "currency": "USD", "notes": "n"}
        )
        assert sm.unit_scale is UnitScale.BILLIONS
        assert StatementMetadata.from_dict({"unit_scale": "nope"}).unit_scale is UnitScale.ACTUAL
        assert StatementMetadata.from_dict({"currency": {"code": "JPY"}}).currency.code is CurrencyCode.JPY


class TestStatements:
    def test_income_balance_cash_roundtrip(self) -> None:
        inc = IncomeStatement(revenue=1.0, cogs=0.4, gross_profit=0.6, eps=1.2)
        assert IncomeStatement.from_dict(inc.to_dict()).revenue == 1.0
        bs = _balanced_bs(ppe=200.0, goodwill=50.0)
        assert BalanceSheet.from_dict(bs.to_dict()).ppe == 200.0
        cf = CashFlowStatement(owner_earnings=None, operating_cash_flow=10.0)
        assert CashFlowStatement.from_dict(cf.to_dict()).operating_cash_flow == 10.0

    def test_snapshot_json(self) -> None:
        snap = _snapshot()
        assert snap.version == FINANCIAL_VERSION
        text = snap.to_json(indent=2)
        snap2 = FinancialSnapshot.from_json(text)
        assert snap2.company.ticker == "EXM"
        assert len(snap2.statements) == 1
        snap3 = snap.with_statements(
            (
                _stmt(period=_period(period_end=date(2023, 12, 31), fiscal_year=2023)),
            )
        )
        assert len(snap3.statements) == 1


class TestValidation:
    def test_ok(self) -> None:
        result = validate_statements(_stmt())
        assert result.ok
        assert "accounting equation holds" in result.checks
        assert ValidationResult(ok=True).to_dict()["ok"] is True

    def test_accounting_equation_fail(self) -> None:
        with pytest.raises(FinancialValidationError, match="accounting equation"):
            validate_statements(
                _stmt(balance_sheet=_balanced_bs(total_assets=999.0))
            )

    def test_nan_and_infinite(self) -> None:
        with pytest.raises(FinancialValidationError, match="NaN"):
            validate_statements(
                _stmt(income_statement=IncomeStatement(revenue=float("nan")))
            )
        with pytest.raises(FinancialValidationError, match="infinite"):
            validate_statements(
                _stmt(income_statement=IncomeStatement(revenue=float("inf")))
            )

    def test_required_fields(self) -> None:
        with pytest.raises(FinancialValidationError, match="revenue"):
            validate_statements(
                _stmt(income_statement=IncomeStatement()),
                require_revenue=True,
            )
        with pytest.raises(FinancialValidationError, match="total_assets"):
            validate_statements(
                _stmt(balance_sheet=BalanceSheet()),
                require_total_assets=True,
            )

    def test_quarter_ok_check(self) -> None:
        result = validate_statements(
            _stmt(
                period=_period(
                    period_type=PeriodType.QUARTERLY,
                    fiscal_quarter=1,
                    period_end=date(2024, 3, 31),
                )
            )
        )
        assert "fiscal_quarter in range" in result.checks

    def test_quarter_and_length_errors(self) -> None:
        with pytest.raises(FinancialValidationError, match="fiscal_quarter"):
            validate_statements(
                _stmt(
                    period=_period(
                        period_type=PeriodType.QUARTERLY, fiscal_quarter=5
                    )
                )
            )
        with pytest.raises(FinancialValidationError, match="period_length"):
            validate_statements(_stmt(period=_period(period_length_days=0)))

    def test_negative_shares_and_warnings(self) -> None:
        with pytest.raises(FinancialValidationError, match="weighted_shares"):
            validate_statements(
                _stmt(
                    income_statement=IncomeStatement(
                        revenue=10.0, weighted_shares=-1.0
                    )
                )
            )
        result = validate_statements(
            _stmt(
                income_statement=IncomeStatement(revenue=-5.0),
                balance_sheet=_balanced_bs(cash=-1.0, inventory=-2.0),
            )
        )
        assert any("negative revenue" in w for w in result.warnings)
        assert any("negative cash" in w for w in result.warnings)

    def test_incomplete_equation_warning(self) -> None:
        result = validate_statements(
            _stmt(balance_sheet=BalanceSheet(total_assets=100.0))
        )
        assert any("incomplete" in w for w in result.warnings)

    def test_duplicate_periods(self) -> None:
        s = _stmt()
        with pytest.raises(FinancialValidationError, match="duplicate"):
            validate_snapshot(FinancialSnapshot(statements=(s, s)))

    def test_empty_and_mixed_currency(self) -> None:
        empty = validate_snapshot(FinancialSnapshot())
        assert any("empty" in w for w in empty.warnings)
        snap = FinancialSnapshot(
            statements=(
                _stmt(period=_period(currency=CurrencyRef(CurrencyCode.USD))),
                _stmt(
                    period=_period(
                        period_end=date(2023, 12, 31),
                        fiscal_year=2023,
                        currency=CurrencyRef(CurrencyCode.EUR),
                    )
                ),
            )
        )
        result = validate_snapshot(snap)
        assert any("mixed" in w for w in result.warnings)

    def test_snapshot_collects_statement_errors(self) -> None:
        bad = _stmt(balance_sheet=_balanced_bs(total_assets=1.0))
        with pytest.raises(FinancialValidationError, match="accounting equation"):
            validate_snapshot(FinancialSnapshot(statements=(bad,)))

    def test_equity_fallback(self) -> None:
        # total_equity None → use equity
        result = validate_statements(
            _stmt(
                balance_sheet=BalanceSheet(
                    total_assets=100.0,
                    total_liabilities=40.0,
                    equity=60.0,
                    total_equity=None,
                )
            )
        )
        assert "accounting equation holds" in result.checks


class TestNormalization:
    def test_aliases_and_map(self) -> None:
        assert canonicalize_field_name("Total Revenue") == "revenue"
        assert canonicalize_field_name("cost-of-sales") == "cogs"
        mapped2 = map_raw_fields(
            {"Sales": 100, "Net Earnings": 10, "noise": 1, "cogs": "", "bad": "x"},
            allowed=("revenue", "net_income", "cogs"),
        )
        assert mapped2["revenue"] == 100.0
        assert mapped2["net_income"] == 10.0
        assert mapped2["cogs"] is None
        assert "noise" not in mapped2
        assert canonicalize_field_name("foo__bar") == "foo_bar"
        # TypeError/ValueError path for allowed field
        assert map_raw_fields({"revenue": object()}, allowed=("revenue",))["revenue"] is None
        assert map_raw_fields({"revenue": "not-a-number"}, allowed=("revenue",))[
            "revenue"
        ] is None

    def test_scale_values(self) -> None:
        vals = {"revenue": 2.0, "cogs": None}
        same = scale_values(vals, from_scale=UnitScale.ACTUAL, to_scale=UnitScale.ACTUAL)
        assert same["revenue"] == 2.0
        millions = scale_values(
            vals, from_scale=UnitScale.MILLIONS, to_scale=UnitScale.ACTUAL
        )
        assert millions["revenue"] == pytest.approx(2_000_000.0)

    def test_statements_from_raw_and_normalize(self) -> None:
        raw = statements_from_raw(
            period=_period(),
            income={"Total Revenue": 5, "cogs": 2},
            balance={"Cash And Equivalents": 1, "total_assets": 10,
                     "total_liabilities": 4, "total_equity": 6},
            cash_flow={"CFO": 3, "fcf": 1},
            statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
        )
        assert raw.income_statement.revenue == 5.0
        assert raw.cash_flow.operating_cash_flow == 3.0
        norm = normalize_statements(raw, target_scale=UnitScale.ACTUAL)
        assert norm.income_statement.revenue == pytest.approx(5_000_000.0)
        assert norm.statement_metadata.unit_scale is UnitScale.ACTUAL
        fx = normalize_statements(
            raw, target_scale=UnitScale.MILLIONS, target_currency="EUR"
        )
        assert fx.period.currency.code is CurrencyCode.EUR

    def test_normalize_snapshot(self) -> None:
        snap = _snapshot()
        out = normalize_snapshot(snap, target_scale=UnitScale.ACTUAL, target_currency="INR")
        assert out.company.reporting_currency.code is CurrencyCode.INR
        assert out.statements[0].income_statement.revenue == pytest.approx(
            500_000_000.0
        )


class TestEngine:
    def test_engine_roundtrip(self) -> None:
        eng = FinancialEngine()
        snap = _snapshot()
        assert eng.validate(snap).ok
        norm = eng.normalize(snap, target_scale=UnitScale.ACTUAL)
        payload = eng.serialize(norm)
        assert payload["version"] == FINANCIAL_VERSION
        back = eng.deserialize(payload)
        assert back.company.ticker == "EXM"
        text = eng.serialize_json(back)
        assert eng.deserialize(text).statements[0].period.fiscal_year == 2024

    def test_exception_hierarchy(self) -> None:
        assert issubclass(FinancialValidationError, FinancialError)
        assert issubclass(FinancialError, Exception)

    def test_half_year_custom_period_types(self) -> None:
        for pt in (PeriodType.HALF_YEAR, PeriodType.CUSTOM, PeriodType.ANNUAL):
            r = validate_statements(_stmt(period=_period(period_type=pt)))
            assert r.ok

    def test_package_version(self) -> None:
        import financial

        assert financial.__version__ == "0.7.0"
        assert financial.FINANCIAL_VERSION.startswith("0.7.0")
        assert financial.FinancialEngine is FinancialEngine
        assert len(financial.ACCOUNTING_STANDARDS) >= 4
