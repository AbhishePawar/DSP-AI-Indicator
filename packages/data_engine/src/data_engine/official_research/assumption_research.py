"""Universal DCF assumption research. DSP validator is the only acceptance authority.

Does not invent WACC, terminal growth, or forecast growth.
Does not write VerifiedDataset. Does not call DcfMethod.
AI may propose. Missing evidence stays UNKNOWN. Conflicts are not averaged.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from time import perf_counter
from typing import Any, Mapping, Sequence

from data_engine.official_research.assumption_contract import (
    ASSUMPTION_SOURCES,
    CanonicalAssumption,
    DATA_CLASS_ASSUMPTION,
    DATA_CLASS_DERIVED,
    DATA_CLASS_FACT,
    assumption,
    classify_data_class,
)
from data_engine.official_research.assumption_validator import (
    AssumptionValidation,
    refuse_ai_fact,
    validate_assumption_pack,
)
from data_engine.official_research.component_research import (
    AI_FORBIDDEN_RESULT_FIELDS,
)
from data_engine.official_research.derived_fields import derive_dsp_fields
from data_engine.official_research.dsp_calculation import describe_dcf_blockers
from data_engine.official_research.dsp_wacc import (
    DspWaccCalculation,
    calculate_dsp_wacc,
    compare_external_wacc,
)
from data_engine.official_research.extraction import canonicalize_period, periods_comparable
from data_engine.official_research.research_plan import classify_research_capability
from data_engine.official_research.verified_dataset import (
    FinancialField,
    VerifiedDataset,
)
from data_engine.security_master.models import (
    UNSUPPORTED_SECURITY_TYPES,
    SecurityListing,
)

__all__ = [
    "ASSUMPTION_FRESHNESS_DAYS",
    "VALIDATOR_VERSION",
    "DcfAssumptionCandidate",
    "DcfAssumptionResearchResult",
    "HistoricalObservation",
    "dcf_assumption_candidate",
    "research_dcf_assumptions",
]

VALIDATOR_VERSION = "assumption_validator.v1"
ASSUMPTION_FRESHNESS_DAYS = 365
_AI_PROPOSERS = frozenset(
    {
        "ai",
        "ai_research",
        "ai_synthesis",
        "gemini_find",
        "chatgpt_verify",
        "deep_search_attack",
        "claude_review",
        "openai_nse_mcp",
        "openai",
    }
)
_WACC_COMPONENTS = (
    "risk_free_rate",
    "equity_risk_premium",
    "beta",
    "cost_of_equity",
    "pre_tax_cost_of_debt",
    "tax_rate",
    "debt",
    "equity",
    "capital_weights",
    "wacc",
)
_CAPM_COMPONENT_FIELDS = frozenset(
    {
        "risk_free_rate",
        "beta",
        "equity_risk_premium",
        "pre_tax_cost_of_debt",
        "tax_rate",
    }
)


@dataclass(frozen=True, slots=True)
class HistoricalObservation:
    """One verified historical point. Missing years stay missing."""

    field: str
    value: Decimal
    as_of: date
    isin: str
    mic: str
    currency: str | None
    unit: str | None
    statement_basis: str | None
    evidence_id: str | None
    status: str = "VERIFIED"


@dataclass(frozen=True, slots=True)
class DcfAssumptionCandidate:
    """Proposal only. accepted_by is never proposed_by."""

    name: str
    value: Decimal | None
    unit: str | None
    currency: str | None
    scenario: str
    rationale: str
    evidence_ids: tuple[str, ...]
    source: str
    source_type: str
    as_of: date | None
    retrieved_at: datetime
    confidence: str | None
    proposed_by: str
    isin: str
    mic: str
    ticker: str
    security_type: str
    freshness: str
    data_class: str = DATA_CLASS_ASSUMPTION
    period: str | None = None
    status: str = "PROPOSED"
    detail: str = ""
    accepted_by: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": None if self.value is None else str(self.value),
            "unit": self.unit,
            "currency": self.currency,
            "scenario": self.scenario,
            "rationale": self.rationale,
            "evidence_ids": list(self.evidence_ids),
            "source": self.source,
            "source_type": self.source_type,
            "as_of": None if self.as_of is None else self.as_of.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat(),
            "confidence": self.confidence,
            "proposed_by": self.proposed_by,
            "accepted_by": self.accepted_by,
            "isin": self.isin,
            "mic": self.mic,
            "ticker": self.ticker,
            "security_type": self.security_type,
            "freshness": self.freshness,
            "data_class": self.data_class,
            "period": self.period,
            "status": self.status,
            "detail": self.detail,
        }


def dcf_assumption_candidate(
    listing: SecurityListing,
    name: str,
    value: Decimal | str | float | int | None,
    *,
    proposed_by: str = "DETERMINISTIC_RESEARCH",
    source: str = "primary_research",
    evidence_ids: tuple[str, ...] = (),
    retrieved_at: datetime | None = None,
    as_of: date | None = None,
    currency: str | None = None,
    unit: str | None = "decimal",
    scenario: str = "BASE",
    rationale: str = "",
    isin: str | None = None,
    mic: str | None = None,
    freshness: str = "CURRENT",
    source_type: str = "assumption_proposal",
    confidence: str | None = None,
    period: str | None = None,
) -> DcfAssumptionCandidate:
    numeric: Decimal | None
    if value is None:
        numeric = None
    elif isinstance(value, Decimal):
        numeric = value
    else:
        numeric = Decimal(str(value))
    return DcfAssumptionCandidate(
        name=name,
        value=numeric,
        unit=unit,
        currency=currency,
        scenario=scenario,
        rationale=rationale,
        evidence_ids=evidence_ids,
        source=source,
        source_type=source_type,
        as_of=as_of,
        retrieved_at=retrieved_at or datetime.now(tz=UTC),
        confidence=confidence,
        proposed_by=proposed_by,
        isin=isin or listing.isin,
        mic=mic or listing.mic,
        ticker=listing.ticker,
        security_type=listing.security_type,
        freshness=freshness,
        period=period,
    )


@dataclass(frozen=True, slots=True)
class DcfAssumptionResearchResult:
    status: str
    company: str
    ticker: str
    isin: str
    mic: str
    security_type: str
    capability: str
    wacc: Decimal | None
    wacc_status: str
    wacc_source: str | None
    wacc_evidence: tuple[str, ...]
    terminal_growth: Decimal | None
    terminal_growth_status: str
    terminal_growth_source: str | None
    terminal_growth_evidence: tuple[str, ...]
    historical_growth_metrics: dict[str, Any]
    wacc_components: dict[str, Any]
    candidate_assumptions: tuple[DcfAssumptionCandidate, ...]
    accepted_assumptions: tuple[CanonicalAssumption, ...]
    rejected_assumptions: tuple[DcfAssumptionCandidate, ...]
    conflicts: tuple[str, ...]
    validation_reasons: tuple[str, ...]
    assumption_researched_at: datetime
    assumption_validated_at: datetime
    dcf_eligibility: str
    dcf_blockers: tuple[str, ...]
    ai_status: str
    timings: dict[str, float] = field(default_factory=dict)
    validator_version: str = VALIDATOR_VERSION
    dsp_wacc: DspWaccCalculation | None = None
    wacc_reconstruction: dict[str, Any] = field(default_factory=dict)

    @property
    def accepted_pack(self) -> tuple[CanonicalAssumption, ...]:
        return self.accepted_assumptions

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "company": self.company,
            "ticker": self.ticker,
            "isin": self.isin,
            "mic": self.mic,
            "security_type": self.security_type,
            "capability": self.capability,
            "wacc": None if self.wacc is None else str(self.wacc),
            "wacc_status": self.wacc_status,
            "wacc_source": self.wacc_source,
            "wacc_evidence": list(self.wacc_evidence),
            "terminal_growth": None if self.terminal_growth is None else str(self.terminal_growth),
            "terminal_growth_status": self.terminal_growth_status,
            "terminal_growth_source": self.terminal_growth_source,
            "terminal_growth_evidence": list(self.terminal_growth_evidence),
            "historical_growth_metrics": dict(self.historical_growth_metrics),
            "wacc_components": dict(self.wacc_components),
            "candidate_assumptions": [item.to_public_dict() for item in self.candidate_assumptions],
            "accepted_assumptions": [item.to_public_dict() for item in self.accepted_assumptions],
            "rejected_assumptions": [item.to_public_dict() for item in self.rejected_assumptions],
            "conflicts": list(self.conflicts),
            "validation_reasons": list(self.validation_reasons),
            "assumption_researched_at": self.assumption_researched_at.isoformat(),
            "assumption_validated_at": self.assumption_validated_at.isoformat(),
            "dcf_eligibility": self.dcf_eligibility,
            "dcf_blockers": list(self.dcf_blockers),
            "ai_status": self.ai_status,
            "timings": dict(self.timings),
            "validator_version": self.validator_version,
            "dsp_wacc": None if self.dsp_wacc is None else self.dsp_wacc.to_public_dict(),
            "wacc_reconstruction": dict(self.wacc_reconstruction),
        }


def research_dcf_assumptions(
    dataset: VerifiedDataset | None,
    listing: SecurityListing,
    *,
    proposals: Sequence[CanonicalAssumption | DcfAssumptionCandidate] = (),
    history: Sequence[HistoricalObservation] = (),
    now: datetime | None = None,
    ai_configured: bool = False,
) -> DcfAssumptionResearchResult:
    """Research → candidate → validator. Never AI → DCF. Never missing → default."""
    researched_at = now or datetime.now(tz=UTC)
    capability = classify_research_capability(listing)
    timings: dict[str, float] = {
        "research": 0.0,
        "normalization": 0.0,
        "assumption_generation": 0.0,
        "assumption_validation": 0.0,
        "dsp_wacc": 0.0,
        "dsp_growth": 0.0,
        "ai_retrieval": 0.0,
        "source_retrieval": 0.0,
        "evidence_judge": 0.0,
    }
    t_all = perf_counter()
    if listing.security_type in UNSUPPORTED_SECURITY_TYPES:
        return _empty_result(
            listing,
            capability=capability,
            status="UNKNOWN",
            dcf_eligibility="UNSUPPORTED",
            dcf_blockers=(f"{listing.security_type} is outside ordinary-equity DCF",),
            now=researched_at,
            ai_status="NOT_CONFIGURED" if not ai_configured else "CONFIGURED",
        )
    if capability == "bank_equity":
        return _empty_result(
            listing,
            capability=capability,
            status="UNKNOWN",
            dcf_eligibility="BANK_VALUATION_METHOD_REQUIRED",
            dcf_blockers=("bank_equity: ordinary DCF not applicable",),
            now=researched_at,
            ai_status="NOT_CONFIGURED" if not ai_configured else "CONFIGURED",
        )
    if capability != "equity":
        return _empty_result(
            listing,
            capability=capability,
            status="UNKNOWN",
            dcf_eligibility="BLOCKED",
            dcf_blockers=(f"{capability}: ordinary DCF not applicable",),
            now=researched_at,
            ai_status="NOT_CONFIGURED" if not ai_configured else "CONFIGURED",
        )

    t_norm = perf_counter()
    observations = _merge_history(dataset, listing, history)
    historical_metrics = _historical_metrics(observations, listing)
    timings["normalization"] = perf_counter() - t_norm
    timings["dsp_growth"] = timings["normalization"]
    t_gen = perf_counter()
    generated = _deterministic_growth_candidates(
        listing, historical_metrics, retrieved_at=researched_at
    )
    inbound = _normalize_proposals(proposals, listing, retrieved_at=researched_at)
    evidenced = _candidates_from_verified_evidence(dataset, listing, retrieved_at=researched_at)
    t_wacc = perf_counter()
    derived_wacc, dsp_wacc, reconstruction = _dsp_wacc_candidates(
        inbound + generated + evidenced,
        listing,
        dataset=dataset,
        retrieved_at=researched_at,
    )
    timings["dsp_wacc"] = perf_counter() - t_wacc
    candidates = inbound + generated + evidenced + derived_wacc
    timings["assumption_generation"] = perf_counter() - t_gen

    screened: list[DcfAssumptionCandidate] = []
    rejected: list[DcfAssumptionCandidate] = []
    reasons: list[str] = []
    for item in candidates:
        screened_item, reason = _screen(item, listing, dataset, now=researched_at)
        if screened_item.status in {"REJECTED", "STALE"}:
            rejected.append(screened_item)
            if reason:
                reasons.append(reason)
            continue
        screened.append(screened_item)

    pack = tuple(_to_assumption(item) for item in screened)
    t_val = perf_counter()
    historical_rates = {
        key: Decimal(str(row["value"]))
        for key, row in historical_metrics.items()
        if key.endswith("_cagr") and row.get("value") is not None
    }
    mapped_hist: dict[str, Decimal] = {}
    if "fcf_cagr" in historical_rates:
        mapped_hist["fcf_growth_rate"] = historical_rates["fcf_cagr"]
    if "revenue_cagr" in historical_rates:
        mapped_hist["revenue_growth"] = historical_rates["revenue_cagr"]
    validated = validate_assumption_pack(pack, historical=mapped_hist or None)
    timings["assumption_validation"] = perf_counter() - t_val

    accepted_rows: list[CanonicalAssumption] = []
    conflicts: list[str] = []
    validated_candidates: list[DcfAssumptionCandidate] = []
    for raw, result in zip(screened, validated, strict=True):
        updated = _apply_validation(raw, result)
        validated_candidates.append(updated)
        if result.status == "REVIEW_REQUIRED":
            conflicts.append(result.detail)
            reasons.append(result.detail)
        elif result.status == "ACCEPTED":
            accepted_rows.append(result.assumption)
        else:
            rejected.append(updated)
            reasons.append(result.detail)

    accepted = tuple(accepted_rows)
    wacc_row = _accepted_field(accepted, ("wacc", "discount_rate"))
    terminal_row = _accepted_field(accepted, ("terminal_growth_rate",))
    growth_row = _accepted_field(accepted, ("fcf_growth_rate",))
    years_row = _accepted_field(accepted, ("projection_years",))
    blockers = describe_dcf_blockers(
        dataset,
        None,
        capability=capability,
        assumptions_accepted=bool(wacc_row and terminal_row and growth_row and years_row),
    )
    if not wacc_row:
        blockers = tuple(dict.fromkeys((*blockers, "WACC:UNKNOWN")))
    if not terminal_row:
        blockers = tuple(dict.fromkeys((*blockers, "TERMINAL_GROWTH:UNKNOWN")))
    if not growth_row:
        blockers = tuple(dict.fromkeys((*blockers, "FCF_GROWTH:UNKNOWN")))
    if not years_row:
        blockers = tuple(dict.fromkeys((*blockers, "PROJECTION_YEARS:UNKNOWN")))
    if reconstruction.get("status") == "REVIEW_REQUIRED":
        conflicts.append("WACC reconstruction conflict; values are not averaged")
        blockers = tuple(dict.fromkeys((*blockers, "WACC_RECONSTRUCTION:REVIEW_REQUIRED")))
    if conflicts:
        blockers = tuple(dict.fromkeys((*blockers, "REVIEW_REQUIRED")))
    eligibility = (
        "ELIGIBLE"
        if wacc_row and terminal_row and growth_row and years_row and not conflicts
        else "DCF_BLOCKED"
    )
    status = "ACCEPTED" if eligibility == "ELIGIBLE" else (
        "REVIEW_REQUIRED" if conflicts else "UNKNOWN"
    )
    components = _component_status(
        tuple(validated_candidates) + tuple(rejected),
        dataset=dataset,
        accepted=accepted,
        dsp_wacc=dsp_wacc,
    )
    timings["research"] = perf_counter() - t_all
    return DcfAssumptionResearchResult(
        status=status,
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        security_type=listing.security_type,
        capability=capability,
        wacc=None if wacc_row is None else wacc_row.value,
        wacc_status="ACCEPTED" if wacc_row is not None else "UNKNOWN",
        wacc_source=None if wacc_row is None else wacc_row.source,
        wacc_evidence=() if wacc_row is None else wacc_row.evidence_ids,
        terminal_growth=None if terminal_row is None else terminal_row.value,
        terminal_growth_status="ACCEPTED" if terminal_row is not None else "UNKNOWN",
        terminal_growth_source=None if terminal_row is None else terminal_row.source,
        terminal_growth_evidence=() if terminal_row is None else terminal_row.evidence_ids,
        historical_growth_metrics=historical_metrics,
        wacc_components=components,
        candidate_assumptions=tuple(validated_candidates),
        accepted_assumptions=accepted,
        rejected_assumptions=tuple(rejected),
        conflicts=tuple(dict.fromkeys(conflicts)),
        validation_reasons=tuple(dict.fromkeys(reasons)),
        assumption_researched_at=researched_at,
        assumption_validated_at=datetime.now(tz=UTC),
        dcf_eligibility=eligibility,
        dcf_blockers=blockers,
        ai_status="CONFIGURED" if ai_configured else "NOT_CONFIGURED",
        timings=timings,
        dsp_wacc=dsp_wacc,
        wacc_reconstruction=reconstruction,
    )


def _empty_result(
    listing: SecurityListing,
    *,
    capability: str,
    status: str,
    dcf_eligibility: str,
    dcf_blockers: tuple[str, ...],
    now: datetime,
    ai_status: str,
) -> DcfAssumptionResearchResult:
    return DcfAssumptionResearchResult(
        status=status,
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        security_type=listing.security_type,
        capability=capability,
        wacc=None,
        wacc_status="UNKNOWN",
        wacc_source=None,
        wacc_evidence=(),
        terminal_growth=None,
        terminal_growth_status="UNKNOWN",
        terminal_growth_source=None,
        terminal_growth_evidence=(),
        historical_growth_metrics={},
        wacc_components={name: {"status": "UNKNOWN", "value": None} for name in _WACC_COMPONENTS},
        candidate_assumptions=(),
        accepted_assumptions=(),
        rejected_assumptions=(),
        conflicts=(),
        validation_reasons=dcf_blockers,
        assumption_researched_at=now,
        assumption_validated_at=now,
        dcf_eligibility=dcf_eligibility,
        dcf_blockers=dcf_blockers,
        ai_status=ai_status,
    )


def _merge_history(
    dataset: VerifiedDataset | None,
    listing: SecurityListing,
    extra: Sequence[HistoricalObservation],
) -> tuple[HistoricalObservation, ...]:
    found: list[HistoricalObservation] = []
    if dataset is not None and dataset.identity_status == "VERIFIED" and dataset.identity is not None:
        identity = dataset.identity
        financials = dataset.financials
        if financials is not None and financials.period_end is not None:
            for name in ("revenue", "net_income", "cfo", "capex"):
                item = getattr(financials, name, None)
                if not isinstance(item, FinancialField):
                    continue
                if item.status != "VERIFIED" or item.value is None or item.as_of is None:
                    continue
                found.append(
                    HistoricalObservation(
                        field=name,
                        value=item.value,
                        as_of=item.as_of,
                        isin=identity.isin,
                        mic=identity.mic,
                        currency=identity.currency,
                        unit=financials.unit_scale,
                        statement_basis=financials.statement_basis,
                        evidence_id=item.evidence_id,
                    )
                )
        for item in dataset.evidence:
            if item.field not in {"revenue", "net_income", "cfo", "capex"}:
                continue
            if item.status != "VERIFIED" or item.value in {None, ""} or item.as_of is None:
                continue
            if (item.isin or "").upper() != listing.isin.upper():
                continue
            if item.mic and item.mic != listing.mic:
                continue
            try:
                amount = Decimal(str(item.value).replace(",", ""))
            except (InvalidOperation, ValueError):
                continue
            found.append(
                HistoricalObservation(
                    field=item.field,
                    value=amount,
                    as_of=item.as_of,
                    isin=item.isin or listing.isin,
                    mic=item.mic or listing.mic,
                    currency=item.currency,
                    unit=item.unit,
                    statement_basis=item.statement_basis,
                    evidence_id=item.evidence_id,
                )
            )
    for item in extra:
        if item.status != "VERIFIED":
            continue
        if item.isin.upper() != listing.isin.upper() or item.mic != listing.mic:
            continue
        found.append(item)
    unique: dict[tuple[str, date, str], HistoricalObservation] = {}
    for item in found:
        unique[(item.field, item.as_of, item.evidence_id or "")] = item
    return tuple(sorted(unique.values(), key=lambda row: (row.field, row.as_of)))


def _historical_metrics(
    observations: tuple[HistoricalObservation, ...],
    listing: SecurityListing,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    by_field: dict[str, list[HistoricalObservation]] = {}
    for item in observations:
        if item.isin.upper() != listing.isin.upper() or item.mic != listing.mic:
            continue
        by_field.setdefault(item.field, []).append(item)
    for name in ("revenue", "net_income", "cfo"):
        metrics[f"{name}_cagr"] = _cagr_metric(by_field.get(name, ()))
    fcf_points = _fcf_points(by_field.get("cfo", ()), by_field.get("capex", ()))
    metrics["fcf_cagr"] = _cagr_from_points(fcf_points)
    metrics["fcf_margin_trend"] = "UNKNOWN"
    return metrics


def _cagr_metric(rows: Sequence[HistoricalObservation]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda item: item.as_of)
    if len(ordered) < 2:
        return {"value": None, "status": "UNKNOWN", "reason": "insufficient history"}
    first, last = ordered[0], ordered[-1]
    years = (last.as_of - first.as_of).days / 365.25
    if years < 1:
        return {"value": None, "status": "UNKNOWN", "reason": "periods not a full year apart"}
    if first.currency and last.currency and first.currency != last.currency:
        return {"value": None, "status": "REJECTED", "reason": "currency mismatch"}
    if first.unit and last.unit and first.unit != last.unit:
        return {"value": None, "status": "REJECTED", "reason": "unit mismatch"}
    if (
        first.statement_basis
        and last.statement_basis
        and first.statement_basis != last.statement_basis
    ):
        return {"value": None, "status": "REJECTED", "reason": "consolidation mismatch"}
    value = _cagr(first.value, last.value, years)
    if value is None:
        return {"value": None, "status": "UNKNOWN", "reason": "non-positive base"}
    return {
        "value": str(value),
        "status": "CALCULATED",
        "data_class": DATA_CLASS_DERIVED,
        "start": first.as_of.isoformat(),
        "end": last.as_of.isoformat(),
        "evidence_ids": [item.evidence_id for item in ordered if item.evidence_id],
    }


def _fcf_points(
    cfo_rows: Sequence[HistoricalObservation],
    capex_rows: Sequence[HistoricalObservation],
) -> list[tuple[date, Decimal, tuple[str, ...]]]:
    capex_by = {item.as_of: item for item in capex_rows}
    points: list[tuple[date, Decimal, tuple[str, ...]]] = []
    for cfo in cfo_rows:
        capex = capex_by.get(cfo.as_of)
        if capex is None:
            continue
        if cfo.currency and capex.currency and cfo.currency != capex.currency:
            continue
        fcf = cfo.value - abs(capex.value)
        ids = tuple(item for item in (cfo.evidence_id, capex.evidence_id) if item)
        points.append((cfo.as_of, fcf, ids))
    return points


def _cagr_from_points(points: Sequence[tuple[date, Decimal, tuple[str, ...]]]) -> dict[str, Any]:
    ordered = sorted(points, key=lambda item: item[0])
    if len(ordered) < 2:
        return {"value": None, "status": "UNKNOWN", "reason": "insufficient history"}
    first, last = ordered[0], ordered[-1]
    years = (last[0] - first[0]).days / 365.25
    value = _cagr(first[1], last[1], years)
    if value is None:
        return {"value": None, "status": "UNKNOWN", "reason": "non-positive FCF"}
    evidence = [item for pair in ordered for item in pair[2]]
    return {
        "value": str(value),
        "status": "CALCULATED",
        "data_class": DATA_CLASS_DERIVED,
        "start": first[0].isoformat(),
        "end": last[0].isoformat(),
        "evidence_ids": evidence,
    }


def _cagr(start: Decimal, end: Decimal, years: float) -> Decimal | None:
    if years < 1 or start <= 0 or end <= 0:
        return None
    exponent = Decimal("1") / Decimal(str(years))
    return (end / start) ** exponent - Decimal("1")


def _deterministic_growth_candidates(
    listing: SecurityListing,
    metrics: Mapping[str, Any],
    *,
    retrieved_at: datetime,
) -> tuple[DcfAssumptionCandidate, ...]:
    """Historical CAGR is a derived metric. Using it as forecast growth is still an assumption."""
    fcf = metrics.get("fcf_cagr") or {}
    if fcf.get("status") != "CALCULATED" or fcf.get("value") is None:
        return ()
    evidence = tuple(str(item) for item in (fcf.get("evidence_ids") or ()) if item)
    if not evidence:
        return ()
    return (
        DcfAssumptionCandidate(
            name="fcf_growth_rate",
            value=Decimal(str(fcf["value"])),
            unit="decimal",
            currency=None,
            scenario="BASE",
            rationale=(
                "forecast FCF growth proposed from verified multi-period FCF CAGR; "
                "not last-year growth; not GDP; not a hidden default"
            ),
            evidence_ids=evidence,
            source="historical_company_performance",
            source_type="derived_historical_metric",
            as_of=date.fromisoformat(str(fcf["end"])),
            retrieved_at=retrieved_at,
            confidence=None,
            proposed_by="DETERMINISTIC_RESEARCH",
            isin=listing.isin,
            mic=listing.mic,
            ticker=listing.ticker,
            security_type=listing.security_type,
            freshness="CURRENT",
            period=str(fcf.get("end")),
        ),
    )


def _normalize_proposals(
    proposals: Sequence[CanonicalAssumption | DcfAssumptionCandidate],
    listing: SecurityListing,
    *,
    retrieved_at: datetime,
) -> tuple[DcfAssumptionCandidate, ...]:
    found: list[DcfAssumptionCandidate] = []
    for item in proposals:
        if isinstance(item, DcfAssumptionCandidate):
            found.append(item)
            continue
        found.append(
            DcfAssumptionCandidate(
                name=item.field,
                value=item.value,
                unit=item.unit,
                currency=None,
                scenario=item.scenario,
                rationale=item.reasoning or item.detail,
                evidence_ids=item.evidence_ids,
                source=item.source,
                source_type="assumption_proposal",
                as_of=None,
                retrieved_at=item.created_at,
                confidence=item.confidence,
                proposed_by=item.proposed_by,
                isin=listing.isin,
                mic=listing.mic,
                ticker=listing.ticker,
                security_type=listing.security_type,
                freshness=_freshness(item.created_at, retrieved_at),
                period=item.period,
                status=item.validation_status if item.validation_status == "PROPOSED" else "PROPOSED",
                detail=item.detail,
            )
        )
    return tuple(found)


def _candidates_from_verified_evidence(
    dataset: VerifiedDataset | None,
    listing: SecurityListing,
    *,
    retrieved_at: datetime,
) -> tuple[DcfAssumptionCandidate, ...]:
    """Primary VERIFIED component evidence becomes research candidates. Not WACC."""
    if dataset is None:
        return ()
    found: list[DcfAssumptionCandidate] = []
    for item in dataset.evidence:
        if item.status != "VERIFIED":
            continue
        if item.field in AI_FORBIDDEN_RESULT_FIELDS:
            continue
        if item.field not in {
            "risk_free_rate",
            "beta",
            "equity_risk_premium",
            "tax_rate",
            "pre_tax_cost_of_debt",
        }:
            continue
        if (item.isin or "").upper() != listing.isin.upper() or (item.mic or listing.mic) != listing.mic:
            continue
        if item.value in {None, ""}:
            continue
        try:
            amount = Decimal(str(item.value).replace(",", ""))
        except (InvalidOperation, ValueError):
            continue
        found.append(
            DcfAssumptionCandidate(
                name=item.field,
                value=amount,
                unit=item.unit or "decimal",
                currency=item.currency,
                scenario="BASE",
                rationale="verified primary-source component; DSP will calculate WACC",
                evidence_ids=(item.evidence_id,),
                source="regulatory_information" if (item.source_type or "") == "regulator" else "primary_research",
                source_type=item.source_type or "assumption_proposal",
                as_of=item.as_of,
                retrieved_at=item.retrieved_at,
                confidence=item.confidence,
                proposed_by="MARKET_DATA",
                isin=listing.isin,
                mic=listing.mic,
                ticker=listing.ticker,
                security_type=listing.security_type,
                freshness=_freshness(item.retrieved_at, retrieved_at),
                period=item.period,
            )
        )
    return tuple(found)


def _verified_amount(dataset: VerifiedDataset | None, field: str) -> tuple[Decimal | None, tuple[str, ...]]:
    if dataset is None:
        return None, ()
    if field in {"debt", "equity"}:
        value = dataset.verified_decimal(field)
        item = None if dataset.financials is None else getattr(dataset.financials, field, None)
        evidence = ()
        if item is not None and getattr(item, "evidence_id", None):
            evidence = (item.evidence_id,)
        return value, evidence
    for item in dataset.evidence:
        if item.field != field or item.status != "VERIFIED" or item.value in {None, ""}:
            continue
        try:
            return Decimal(str(item.value).replace(",", "")), (item.evidence_id,)
        except (InvalidOperation, ValueError):
            continue
    return None, ()


def _dsp_wacc_candidates(
    candidates: tuple[DcfAssumptionCandidate, ...],
    listing: SecurityListing,
    *,
    dataset: VerifiedDataset | None,
    retrieved_at: datetime,
) -> tuple[tuple[DcfAssumptionCandidate, ...], DspWaccCalculation | None, dict[str, Any]]:
    """DSP calculates WACC. AI WACC rows are ignored as inputs."""
    reconstruction: dict[str, Any] = {"status": "NOT_APPLICABLE"}
    usable = tuple(
        item
        for item in candidates
        if not (
            item.proposed_by.strip().lower() in _AI_PROPOSERS
            and item.name in AI_FORBIDDEN_RESULT_FIELDS
        )
    )
    component_names = (
        "risk_free_rate",
        "equity_risk_premium",
        "beta",
        "tax_rate",
        "pre_tax_cost_of_debt",
    )
    for name in component_names:
        values = {
            item.value
            for item in usable
            if item.name == name and item.value is not None
        }
        if len(values) > 1:
            return (
                (),
                _unknown_wacc(f"conflicting {name} values are not averaged"),
                {
                    "status": "REVIEW_REQUIRED",
                    "detail": f"conflicting {name} values are not averaged",
                    "external_wacc": None,
                    "dsp_wacc": None,
                },
            )
    by_name = {item.name: item for item in usable if item.value is not None}
    rf = by_name.get("risk_free_rate")
    erp = by_name.get("equity_risk_premium")
    beta = by_name.get("beta")
    tax = by_name.get("tax_rate")
    rd_row = by_name.get("pre_tax_cost_of_debt")
    period_error = _capm_period_mismatch((rf, erp, beta, tax, rd_row))
    if period_error:
        return (), _unknown_wacc(period_error), {
            "status": "REJECTED",
            "detail": period_error,
            "external_wacc": None,
            "dsp_wacc": None,
        }
    ids: list[str] = []
    for row in (rf, erp, beta, tax, rd_row):
        if row is not None:
            ids.extend(row.evidence_ids)
    debt, debt_ids = _verified_amount(dataset, "debt")
    finance_costs, fc_ids = _verified_amount(dataset, "finance_costs")
    ids.extend(debt_ids)
    ids.extend(fc_ids)
    equity_mv: Decimal | None = None
    if dataset is not None:
        derived = derive_dsp_fields(dataset, calculated_at=retrieved_at)
        if derived.market_cap.status == "CALCULATED":
            equity_mv = derived.market_cap.value
            ids.extend(derived.market_cap.input_evidence_ids)
    calculated = calculate_dsp_wacc(
        risk_free_rate=None if rf is None else rf.value,
        beta=None if beta is None else beta.value,
        equity_risk_premium=None if erp is None else erp.value,
        equity_market_value=equity_mv,
        debt_market_value=debt,
        pre_tax_cost_of_debt=None if rd_row is None else rd_row.value,
        tax_rate=None if tax is None else tax.value,
        finance_costs=finance_costs,
        tax_rate_kind=None if tax is None else "evidenced",
        evidence_ids=tuple(dict.fromkeys(ids)),
    )
    if calculated.status != "CALCULATED" or calculated.wacc is None:
        fallback = calculate_dsp_wacc(
            risk_free_rate=None if rf is None else rf.value,
            beta=None if beta is None else beta.value,
            equity_risk_premium=None if erp is None else erp.value,
            equity_market_value=equity_mv,
            debt_market_value=Decimal("0"),
            pre_tax_cost_of_debt=None,
            tax_rate=None,
            finance_costs=None,
            evidence_ids=tuple(dict.fromkeys(ids)),
        )
        if fallback.status == "CALCULATED" and fallback.wacc is not None:
            calculated = DspWaccCalculation(
                status="CALCULATED",
                cost_of_equity=fallback.cost_of_equity,
                pre_tax_cost_of_debt=calculated.pre_tax_cost_of_debt,
                after_tax_cost_of_debt=calculated.after_tax_cost_of_debt,
                equity_weight=fallback.equity_weight,
                debt_weight=fallback.debt_weight,
                wacc=fallback.wacc,
                formula=fallback.formula,
                engine=fallback.engine,
                inputs=calculated.inputs or fallback.inputs,
                evidence_ids=fallback.evidence_ids,
                detail=f"{calculated.detail}; using cost of equity until levered inputs are evidenced",
                calculated_at=fallback.calculated_at,
                calculation_version=fallback.calculation_version,
            )
        else:
            return (), calculated, reconstruction
    if rf is None or erp is None or beta is None:
        return (), calculated, reconstruction
    if not (rf.evidence_ids and erp.evidence_ids and beta.evidence_ids):
        return (), calculated, reconstruction
    if any(item.freshness == "STALE" for item in (rf, erp, beta)):
        return (), calculated, reconstruction
    external_rows = tuple(
        item
        for item in usable
        if item.name in {"wacc", "discount_rate"} and item.value is not None
    )
    dsp_candidate = DcfAssumptionCandidate(
        name="discount_rate",
        value=calculated.wacc,
        unit="decimal",
        currency=None,
        scenario="BASE",
        rationale=f"{calculated.formula}; {calculated.detail}",
        evidence_ids=calculated.evidence_ids,
        source="primary_research",
        source_type="derived_from_accepted_components",
        as_of=rf.as_of,
        retrieved_at=retrieved_at,
        confidence=None,
        proposed_by="DETERMINISTIC_RESEARCH",
        isin=listing.isin,
        mic=listing.mic,
        ticker=listing.ticker,
        security_type=listing.security_type,
        freshness="CURRENT",
        data_class=DATA_CLASS_ASSUMPTION,
    )
    if external_rows:
        external_value = external_rows[0].value
        comparison = compare_external_wacc(calculated.wacc, external_value)
        reconstruction = {
            "status": comparison,
            "external_wacc": str(external_value),
            "dsp_wacc": str(calculated.wacc),
            "engine": calculated.engine,
            "detail": (
                "DSP reconstructed WACC independently"
                if comparison == "MATCH"
                else "external WACC differs from DSP reconstruction; values are not averaged"
            ),
        }
        if comparison != "MATCH":
            return ((dsp_candidate,), calculated, reconstruction)
    return ((dsp_candidate,), calculated, reconstruction)


def _unknown_wacc(detail: str) -> DspWaccCalculation:
    calculated = calculate_dsp_wacc(
        risk_free_rate=None,
        beta=None,
        equity_risk_premium=None,
        equity_market_value=None,
        debt_market_value=None,
        pre_tax_cost_of_debt=None,
        tax_rate=None,
    )
    return DspWaccCalculation(
        status="UNKNOWN",
        cost_of_equity=None,
        pre_tax_cost_of_debt=None,
        after_tax_cost_of_debt=None,
        equity_weight=None,
        debt_weight=None,
        wacc=None,
        formula=calculated.formula,
        engine=calculated.engine,
        inputs=calculated.inputs,
        evidence_ids=(),
        detail=detail,
        calculated_at=calculated.calculated_at,
        calculation_version=calculated.calculation_version,
    )


def _capm_period_mismatch(rows: tuple[DcfAssumptionCandidate | None, ...]) -> str | None:
    periods = []
    for item in rows:
        if item is None or not item.period:
            continue
        canonical = canonicalize_period(item.period)
        if canonical is not None:
            periods.append(canonical)
    if len(periods) < 2:
        return None
    first = periods[0]
    if any(not periods_comparable(first, item) for item in periods[1:]):
        return "period mismatch"
    return None


def _derived_cost_of_capital(
    candidates: tuple[DcfAssumptionCandidate, ...],
    listing: SecurityListing,
    *,
    retrieved_at: datetime,
) -> tuple[DcfAssumptionCandidate, ...]:
    """Compatibility wrapper. Prefer _dsp_wacc_candidates."""
    rows, _calc, _reconstruction = _dsp_wacc_candidates(
        candidates, listing, dataset=None, retrieved_at=retrieved_at
    )
    return rows


def _screen(
    item: DcfAssumptionCandidate,
    listing: SecurityListing,
    dataset: VerifiedDataset | None,
    *,
    now: datetime,
) -> tuple[DcfAssumptionCandidate, str]:
    klass = classify_data_class(item.name)
    if klass == DATA_CLASS_FACT:
        ai_status = refuse_ai_fact(item.name, proposed_by=item.proposed_by)
        is_ai = item.proposed_by.strip().lower() in _AI_PROPOSERS or ai_status == "REJECTED"
        rejected = _replace(
            item,
            status="REJECTED",
            detail="PRIMARY_WINS; facts cannot be assumptions",
        )
        reason = "PRIMARY_WINS;AI_REJECTED" if is_ai else f"{item.name}:REJECTED"
        return rejected, reason
    if klass == DATA_CLASS_DERIVED:
        rejected = _replace(item, status="REJECTED", detail="derived values cannot become assumptions")
        return rejected, f"{item.name}:REJECTED"
    if klass != DATA_CLASS_ASSUMPTION:
        rejected = _replace(item, status="REJECTED", detail="unknown assumption field")
        return rejected, f"{item.name}:UNKNOWN"
    if item.name in AI_FORBIDDEN_RESULT_FIELDS and item.proposed_by.strip().lower() in _AI_PROPOSERS:
        rejected = _replace(
            item,
            status="REJECTED",
            detail="AI_CALCULATED_OUTPUT_REJECTED; DSP calculates WACC/growth",
        )
        return rejected, f"{item.name}:AI_REJECTED"
    if item.name in _CAPM_COMPONENT_FIELDS and item.proposed_by.strip().lower() in _AI_PROPOSERS:
        rejected = _replace(
            item,
            status="REJECTED",
            detail="AI_COMPONENT_INJECTION_REJECTED; retrieve evidence for EvidenceJudge",
        )
        return rejected, f"{item.name}:AI_REJECTED"
    if item.isin.upper() != listing.isin.upper() or item.mic != listing.mic:
        rejected = _replace(item, status="REJECTED", detail="IDENTITY_FAIL")
        return rejected, "IDENTITY_FAIL"
    if dataset is not None and dataset.identity is not None:
        if item.currency and dataset.identity.currency and item.currency != dataset.identity.currency:
            rejected = _replace(item, status="REJECTED", detail="currency mismatch")
            return rejected, "currency mismatch"
    freshness = item.freshness
    if freshness in {"UNKNOWN", "CURRENT"}:
        computed = _freshness(item.retrieved_at, now)
        if computed == "STALE":
            freshness = "STALE"
        elif freshness == "UNKNOWN":
            freshness = computed
    if freshness == "STALE":
        stale = _replace(item, status="STALE", freshness="STALE", detail="STALE; RESEARCH_REQUIRED")
        return stale, "STALE"
    if item.proposed_by.strip().lower() in _AI_PROPOSERS and not item.evidence_ids:
        rejected = _replace(
            item, status="REJECTED", detail="AI proposal has no evidence"
        )
        return rejected, f"{item.name}:AI_REJECTED"
    if item.source.strip().lower() == "ai_synthesis" and not item.evidence_ids:
        rejected = _replace(
            item, status="REJECTED", detail="AI synthesis is not primary evidence"
        )
        return rejected, f"{item.name}:AI_REJECTED"
    return _replace(item, freshness=freshness, status="PROPOSED"), ""


def _freshness(created_at: datetime, now: datetime) -> str:
    created = created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    current = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    if current - created > timedelta(days=ASSUMPTION_FRESHNESS_DAYS):
        return "STALE"
    return "CURRENT"


def _to_assumption(item: DcfAssumptionCandidate) -> CanonicalAssumption:
    source = item.source if item.source in ASSUMPTION_SOURCES else (
        "ai_synthesis" if item.proposed_by.strip().lower() in _AI_PROPOSERS else "primary_research"
    )
    return assumption(
        item.name,
        item.value,
        scenario=item.scenario,
        source=source,
        proposed_by=item.proposed_by,
        validation_status="PROPOSED",
        unit=item.unit or "decimal",
        period=item.period,
        evidence_ids=item.evidence_ids,
        reasoning=item.rationale,
        confidence=item.confidence,
        created_at=item.retrieved_at,
        detail=item.detail,
    )


def _apply_validation(
    item: DcfAssumptionCandidate, result: AssumptionValidation
) -> DcfAssumptionCandidate:
    accepted_by = VALIDATOR_VERSION if result.status == "ACCEPTED" else None
    return _replace(
        item,
        status=result.status,
        detail=result.detail,
        accepted_by=accepted_by,
        value=result.assumption.value,
    )


def _replace(item: DcfAssumptionCandidate, **changes: Any) -> DcfAssumptionCandidate:
    return replace(item, **changes)


def _accepted_field(
    accepted: tuple[CanonicalAssumption, ...], names: tuple[str, ...]
) -> CanonicalAssumption | None:
    for item in accepted:
        if item.field in names and item.validation_status == "ACCEPTED":
            return item
    return None


def _component_status(
    candidates: Sequence[DcfAssumptionCandidate],
    *,
    dataset: VerifiedDataset | None,
    accepted: tuple[CanonicalAssumption, ...],
    dsp_wacc: DspWaccCalculation | None = None,
) -> dict[str, Any]:
    found: dict[str, Any] = {
        name: {
            "status": "UNKNOWN",
            "value": None,
            "source": None,
            "data_class": (
                DATA_CLASS_FACT if name in {"debt", "equity"}
                else DATA_CLASS_DERIVED if name in {"cost_of_equity", "capital_weights", "wacc"}
                else DATA_CLASS_ASSUMPTION
            ),
        }
        for name in _WACC_COMPONENTS
    }
    if dataset is not None:
        for name in ("debt", "equity"):
            status = dataset.field_status(name)
            value = dataset.verified_decimal(name)
            found[name] = {
                "status": status,
                "value": None if value is None else str(value),
                "source": "verified_dataset",
                "data_class": DATA_CLASS_FACT,
            }
    for item in candidates:
        mapped = "wacc" if item.name in {"wacc", "discount_rate"} else item.name
        if mapped == "discount_rate":
            mapped = "cost_of_equity"
        if mapped not in found:
            continue
        found[mapped] = {
            "status": item.status,
            "value": None if item.value is None else str(item.value),
            "source": item.source,
            "evidence_ids": list(item.evidence_ids),
            "data_class": item.data_class,
        }
    wacc_row = _accepted_field(accepted, ("wacc", "discount_rate"))
    if dsp_wacc is not None:
        found["dsp_calculation"] = dsp_wacc.to_public_dict()
        if dsp_wacc.equity_weight is not None:
            found["capital_weights"] = {
                "status": dsp_wacc.status,
                "value": {
                    "equity_weight": str(dsp_wacc.equity_weight),
                    "debt_weight": str(dsp_wacc.debt_weight),
                },
                "data_class": DATA_CLASS_DERIVED,
            }
        if dsp_wacc.after_tax_cost_of_debt is not None:
            found["after_tax_cost_of_debt"] = {
                "status": dsp_wacc.status,
                "value": str(dsp_wacc.after_tax_cost_of_debt),
                "data_class": DATA_CLASS_DERIVED,
            }
    if wacc_row is not None:
        found["wacc"] = {
            "status": "ACCEPTED",
            "value": str(wacc_row.value),
            "source": wacc_row.source,
            "evidence_ids": list(wacc_row.evidence_ids),
            "data_class": DATA_CLASS_ASSUMPTION,
            "note": "accepted required-return input; not an observed market fact",
        }
        found["cost_of_equity"] = dict(found["wacc"])
    return found
