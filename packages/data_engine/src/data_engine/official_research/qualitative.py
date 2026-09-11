"""Connect existing DSP qualitative engines to a VerifiedDataset.

Reuses FinancialEngine, BusinessQualityEngine, EconomicEngine,
ManagementEngine, FinancialStrengthEngine, and composition risk_view.
Does not invent scores, weights, or line items. Missing inputs stay
UNKNOWN / PARTIAL. AI narrative cannot create a score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from time import perf_counter
from typing import Any

from business_quality import BusinessQualityEngine
from business_quality.business_quality_engine import _module_01
from economic_moat import EconomicEngine
from financial import FinancialEngine
from financial.balance_sheet import BalanceSheet
from financial.cash_flow import CashFlowStatement
from financial.currency import CurrencyRef
from financial.income_statement import IncomeStatement
from financial.metadata import StatementMetadata, UnitScale
from financial.models import FinancialStatements
from financial.period import FinancialPeriod, PeriodType
from financial_strength import FinancialStrengthEngine
from management_quality import ManagementEngine

from data_engine.official_research.dsp_calculation import MOAT_WEIGHTS, QUALITY_WEIGHTS
from data_engine.official_research.verified_dataset import VerifiedDataset
from data_engine.security_master.models import SecurityListing

__all__ = [
    "DATA_CLASS_AI_INTERPRETATION",
    "DATA_CLASS_DSP_ASSESSMENT",
    "DATA_CLASS_RESEARCH_CLAIM",
    "DATA_CLASS_VERIFIED_FACT",
    "QualitativeSnapshot",
    "run_qualitative_engines",
    "statements_from_dataset",
]

DATA_CLASS_VERIFIED_FACT = "VERIFIED_FACT"
DATA_CLASS_RESEARCH_CLAIM = "RESEARCH_CLAIM"
DATA_CLASS_DSP_ASSESSMENT = "DSP_ASSESSMENT"
DATA_CLASS_AI_INTERPRETATION = "AI_INTERPRETATION"

_QUALITY_KEYS = tuple(QUALITY_WEIGHTS)
_MOAT_KEYS = tuple(MOAT_WEIGHTS)


@dataclass(frozen=True, slots=True)
class QualitativeSnapshot:
    status: str
    detail: str
    quality_components: dict[str, Decimal | None]
    moat_components: dict[str, Decimal | None]
    risk_observations: tuple[str, ...]
    business_quality: dict[str, Any]
    moat: dict[str, Any]
    management: dict[str, Any]
    financial_strength: dict[str, Any]
    risk: dict[str, Any]
    overall_score_status: str
    overall_business_quality: str | None
    timings: dict[str, float] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "detail": self.detail,
            "data_classes": {
                "verified_fact": DATA_CLASS_VERIFIED_FACT,
                "research_claim": DATA_CLASS_RESEARCH_CLAIM,
                "dsp_assessment": DATA_CLASS_DSP_ASSESSMENT,
                "ai_interpretation": DATA_CLASS_AI_INTERPRETATION,
            },
            "quality_components": {
                key: None if val is None else str(val)
                for key, val in self.quality_components.items()
            },
            "moat_components": {
                key: None if val is None else str(val)
                for key, val in self.moat_components.items()
            },
            "risk_observations": list(self.risk_observations),
            "business_quality": dict(self.business_quality),
            "moat": dict(self.moat),
            "management": dict(self.management),
            "financial_strength": dict(self.financial_strength),
            "risk": dict(self.risk),
            "overall_score_status": self.overall_score_status,
            "overall_business_quality": self.overall_business_quality,
            "timings": dict(self.timings),
            "weights_reused": {
                "business_quality": {k: str(v) for k, v in QUALITY_WEIGHTS.items()},
                "moat": {k: str(v) for k, v in MOAT_WEIGHTS.items()},
            },
        }


def _empty_components(keys: tuple[str, ...]) -> dict[str, Decimal | None]:
    return {key: None for key in keys}


def _blocked(
    detail: str,
    *,
    timings: dict[str, float] | None = None,
    status: str = "UNKNOWN",
) -> QualitativeSnapshot:
    return QualitativeSnapshot(
        status=status,
        detail=detail,
        quality_components=_empty_components(_QUALITY_KEYS),
        moat_components=_empty_components(_MOAT_KEYS),
        risk_observations=(),
        business_quality={"status": status, "detail": detail},
        moat={"status": status, "detail": detail},
        management={"status": status, "detail": detail},
        financial_strength={"status": status, "detail": detail},
        risk={
            "status": status,
            "overall_risk_level": None,
            "numeric_score": None,
            "detail": "existing risk methodology is qualitative / ordinal; no 0–10 score",
        },
        overall_score_status="NOT_CURRENTLY_DEFINED",
        overall_business_quality=None,
        timings=dict(timings or {}),
    )


def _float(dataset: VerifiedDataset, name: str) -> float | None:
    raw = dataset.verified_decimal(name)
    return None if raw is None else float(raw)


def statements_from_dataset(dataset: VerifiedDataset) -> FinancialStatements | None:
    """Map VERIFIED fields only. Never alias operating profit as EBIT."""
    financials = dataset.financials
    if financials is None or financials.period_end is None:
        return None
    identity = dataset.identity
    currency = CurrencyRef.parse(None if identity is None else identity.currency or "INR")
    period = FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=financials.period_end,
        fiscal_year=int(financials.period_end.year),
        currency=currency,
        source="verified_dataset",
    )
    revenue = _float(dataset, "revenue")
    net_income = _float(dataset, "net_income")
    equity = _float(dataset, "equity")
    cash = _float(dataset, "cash")
    cfo = _float(dataset, "cfo")
    if revenue is None and net_income is None and equity is None and cfo is None:
        return None
    capex = _float(dataset, "capex")
    ebit = _float(dataset, "ebit")
    fcf = None
    if cfo is not None and capex is not None:
        fcf = cfo - abs(capex)
    return FinancialStatements(
        period=period,
        income_statement=IncomeStatement(
            revenue=revenue,
            ebit=ebit,
            net_income=net_income,
        ),
        balance_sheet=BalanceSheet(
            cash=cash,
            total_assets=_float(dataset, "total_assets"),
            total_liabilities=_float(dataset, "total_liabilities"),
            equity=equity,
            total_equity=equity,
            long_term_debt=_float(dataset, "debt"),
        ),
        cash_flow=CashFlowStatement(
            operating_cash_flow=cfo,
            capex=None if capex is None else -abs(capex),
            free_cash_flow=fcf,
        ),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.ACTUAL),
    )


def _score_01(analysis: Any) -> Decimal | None:
    value = _module_01(analysis)
    if value is None:
        return None
    return Decimal(str(value))


def _moat_100(component: Any) -> Decimal | None:
    score = getattr(component, "score", None)
    value = getattr(score, "value", None) if score is not None else None
    if value is None:
        return None
    return Decimal(str(value))


def run_qualitative_engines(
    dataset: VerifiedDataset | None,
    listing: SecurityListing | None = None,
) -> QualitativeSnapshot:
    """Run existing engines. Failures and missing inputs stay UNKNOWN."""
    _ = listing
    timings: dict[str, float] = {
        "statements": 0.0,
        "financial": 0.0,
        "business_quality": 0.0,
        "moat": 0.0,
        "management": 0.0,
        "financial_strength": 0.0,
        "risk": 0.0,
        "complete": 0.0,
    }
    started = perf_counter()
    if dataset is None or dataset.identity_status != "VERIFIED":
        return _blocked("identity not VERIFIED; qualitative engines not run", timings=timings)
    t = perf_counter()
    statements = statements_from_dataset(dataset)
    timings["statements"] = perf_counter() - t
    if statements is None:
        return _blocked(
            "verified financial primitives missing; QUALITY UNKNOWN",
            timings=timings,
            status="UNKNOWN",
        )

    t = perf_counter()
    try:
        financial = FinancialEngine().analyze_financials(statements)
    except Exception as exc:  # noqa: BLE001 — engine absence is UNKNOWN, not a crash
        timings["financial"] = perf_counter() - t
        timings["complete"] = perf_counter() - started
        return _blocked(
            f"FinancialEngine could not assess sparse statements ({type(exc).__name__})",
            timings=timings,
            status="UNKNOWN",
        )
    timings["financial"] = perf_counter() - t

    t = perf_counter()
    bq = None
    try:
        bq = BusinessQualityEngine().analyze(financial)
    except Exception:
        bq = None
    timings["business_quality"] = perf_counter() - t

    quality_components = _empty_components(_QUALITY_KEYS)
    bq_public: dict[str, Any] = {"status": "UNKNOWN", "rating": None, "score": None}
    if bq is not None:
        quality_components = {
            "earnings_quality": _score_01(getattr(bq, "earnings_quality", None)),
            "capital_allocation": _score_01(getattr(bq, "capital_allocation", None)),
            "business_characteristics": _score_01(getattr(bq, "business_characteristics", None)),
            "competitive_position": _score_01(getattr(bq, "competitive_position", None)),
        }
        rating = getattr(bq, "overall_rating", None)
        rating_value = None if rating is None else getattr(rating, "value", str(rating))
        score_obj = getattr(bq, "overall_score", None)
        score_value = getattr(score_obj, "value", None) if score_obj is not None else None
        present = sum(1 for item in quality_components.values() if item is not None)
        bq_public = {
            "status": "PARTIAL" if present and present < 4 else ("CALCULATED" if present == 4 else "UNKNOWN"),
            "rating": rating_value,
            "score": None if score_value is None else str(score_value),
            "data_class": DATA_CLASS_DSP_ASSESSMENT,
            "engine": "business_quality.BusinessQualityEngine",
        }

    t = perf_counter()
    moat_analysis = None
    if bq is not None:
        try:
            moat_analysis = EconomicEngine().analyze(financial, bq)
        except Exception:
            moat_analysis = None
    timings["moat"] = perf_counter() - t
    moat_components = _empty_components(_MOAT_KEYS)
    moat_public: dict[str, Any] = {"status": "UNKNOWN", "rating": None}
    if moat_analysis is not None:
        for component in getattr(moat_analysis, "components", ()) or ():
            dim = getattr(getattr(component, "dimension", None), "value", None)
            if dim in moat_components:
                moat_components[dim] = _moat_100(component)
        rating = getattr(moat_analysis, "overall_moat_rating", None)
        moat_public = {
            "status": "CALCULATED" if any(moat_components.values()) else "UNKNOWN",
            "rating": None if rating is None else getattr(rating, "value", str(rating)),
            "data_class": DATA_CLASS_DSP_ASSESSMENT,
            "engine": "economic_moat.EconomicEngine",
            "positive_factors": list(getattr(moat_analysis, "positive_factors", ()) or ()),
            "negative_factors": list(getattr(moat_analysis, "negative_factors", ()) or ()),
        }

    t = perf_counter()
    mgmt = None
    if bq is not None:
        try:
            mgmt = ManagementEngine().analyze(financial, bq)
        except Exception:
            mgmt = None
    timings["management"] = perf_counter() - t
    mgmt_public: dict[str, Any] = {"status": "UNKNOWN", "rating": None}
    if mgmt is not None:
        rating = getattr(mgmt, "overall_management_rating", None)
        mgmt_public = {
            "status": "CALCULATED" if getattr(mgmt, "overall_management_score", None) is not None else "PARTIAL",
            "rating": None if rating is None else getattr(rating, "value", str(rating)),
            "data_class": DATA_CLASS_DSP_ASSESSMENT,
            "engine": "management_quality.ManagementEngine",
            "strengths": list(getattr(mgmt, "strengths", ()) or ()),
            "weaknesses": list(getattr(mgmt, "weaknesses", ()) or ()),
        }

    t = perf_counter()
    strength = None
    if bq is not None:
        try:
            strength = FinancialStrengthEngine().analyze(financial, bq)
        except Exception:
            strength = None
    timings["financial_strength"] = perf_counter() - t
    strength_public: dict[str, Any] = {"status": "UNKNOWN", "rating": None}
    if strength is not None:
        rating = getattr(strength, "overall_strength_rating", None)
        strength_public = {
            "status": "CALCULATED" if rating is not None else "PARTIAL",
            "rating": None if rating is None else getattr(rating, "value", str(rating)),
            "data_class": DATA_CLASS_DSP_ASSESSMENT,
            "engine": "financial_strength.FinancialStrengthEngine",
        }

    t = perf_counter()
    risk_public: dict[str, Any] = {
        "status": "UNKNOWN",
        "overall_risk_level": None,
        "numeric_score": None,
        "detail": "existing risk methodology is qualitative / ordinal; no 0–10 score",
        "data_class": DATA_CLASS_DSP_ASSESSMENT,
        "engine": "dsp_platform.composition.risk_view",
    }
    observations: list[str] = []
    try:
        from dsp_platform.composition.risk_view import build_company_risk_view

        view = build_company_risk_view(
            financial_strength=strength,
            economic_moat=moat_analysis,
        )
        risk_public = view.to_dict()
        risk_public["numeric_score"] = None
        risk_public["status"] = (
            "PARTIAL" if view.categories_available else "UNKNOWN"
        )
        risk_public["data_class"] = DATA_CLASS_DSP_ASSESSMENT
        if view.overall_risk_level:
            observations.append(f"overall_risk_level={view.overall_risk_level}")
        for category in view.categories:
            if category.available and category.level:
                observations.append(f"{category.category}={category.level}")
    except Exception:
        pass
    timings["risk"] = perf_counter() - t

    present_q = sum(1 for item in quality_components.values() if item is not None)
    status = "UNKNOWN"
    if present_q == 4:
        status = "CALCULATED"
    elif present_q or moat_public.get("rating") or mgmt_public.get("rating"):
        status = "PARTIAL"

    overall_bq = bq_public.get("rating")
    timings["complete"] = perf_counter() - started
    return QualitativeSnapshot(
        status=status,
        detail="existing DSP qualitative engines; missing modules remain UNKNOWN",
        quality_components=quality_components,
        moat_components=moat_components,
        risk_observations=tuple(observations),
        business_quality=bq_public,
        moat=moat_public,
        management=mgmt_public,
        financial_strength=strength_public,
        risk=risk_public,
        overall_score_status="NOT_CURRENTLY_DEFINED",
        overall_business_quality=None if overall_bq is None else str(overall_bq),
        timings=timings,
    )
