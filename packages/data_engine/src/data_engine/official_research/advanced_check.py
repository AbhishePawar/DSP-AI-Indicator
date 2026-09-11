"""Advanced Failure & Asymmetry Check — separate from core DSP.

UI name: Advanced Investment Check
Internal name: ADVANCED_FAILURE_ASYMMETRY

Asks: even if this is a good company, how could the investment
permanently go wrong, and is the downside protected?

AI may research and attack. EvidenceJudge gates factual claims.
DSP remains responsible for numbers. No invented 0–10 scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256
from time import perf_counter
from typing import Any, Sequence

from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import EvidenceItem, ResearchClaim
from data_engine.official_research.prompt_guard import looks_like_injection
from data_engine.official_research.qualitative import (
    DATA_CLASS_AI_INTERPRETATION,
    DATA_CLASS_DSP_ASSESSMENT,
    DATA_CLASS_RESEARCH_CLAIM,
    DATA_CLASS_VERIFIED_FACT,
    QualitativeSnapshot,
)
from data_engine.official_research.verified_dataset import VerifiedDataset
from data_engine.security_master.models import UNSUPPORTED_SECURITY_TYPES, SecurityListing
from valuation.overall.overall_models import MosClassification, MosThresholds

__all__ = [
    "ADVANCED_CHECK_NAME",
    "ADVANCED_DIMENSIONS",
    "AdvancedCheckResult",
    "AdvancedFinding",
    "InvestmentThesis",
    "ThesisBreaker",
    "evaluate_advanced_check",
]

ADVANCED_CHECK_NAME = "ADVANCED_FAILURE_ASYMMETRY"
ADVANCED_DIMENSIONS: tuple[str, ...] = (
    "LEVERAGE",
    "MOAT_ATTACK",
    "MANAGEMENT_OWNERSHIP",
    "EARNINGS_QUALITY",
    "PERMANENT_LOSS",
    "VALUATION_MOS",
    "INDUSTRY_EXTERNAL",
    "INVESTOR_BIAS",
)

_SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
_FS_TO_SEVERITY = {
    "very_weak": "HIGH",
    "weak": "MEDIUM",
    "average": "LOW",
    "strong": "LOW",
    "exceptional": "LOW",
}
_MOAT_TO_SEVERITY = {
    "no_moat": "HIGH",
    "weak": "MEDIUM",
    "narrow": "LOW",
    "strong": "LOW",
    "wide": "LOW",
}
_RISK_TO_SEVERITY = {
    "very_low": "LOW",
    "low": "LOW",
    "moderate": "MEDIUM",
    "elevated": "HIGH",
    "high": "HIGH",
}


@dataclass(frozen=True, slots=True)
class AdvancedFinding:
    finding: str
    dimension: str
    evidence: str
    source: str
    source_authority: str
    as_of: str | None
    retrieved_at: str | None
    identity: str | None
    confidence: str
    severity: str
    data_class: str
    verification_status: str
    evidence_ids: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "finding": self.finding,
            "dimension": self.dimension,
            "evidence": self.evidence,
            "source": self.source,
            "source_authority": self.source_authority,
            "as_of": self.as_of,
            "retrieved_at": self.retrieved_at,
            "identity": self.identity,
            "confidence": self.confidence,
            "severity": self.severity,
            "data_class": self.data_class,
            "verification_status": self.verification_status,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class ThesisBreaker:
    id: str
    dimension: str
    description: str
    evidence_ids: tuple[str, ...]
    severity: str
    current_status: str
    trigger: str
    monitoring_metric: str
    verification_status: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "dimension": self.dimension,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "severity": self.severity,
            "current_status": self.current_status,
            "trigger": self.trigger,
            "monitoring_metric": self.monitoring_metric,
            "verification_status": self.verification_status,
        }


@dataclass(frozen=True, slots=True)
class InvestmentThesis:
    positive_factors: tuple[str, ...]
    negative_factors: tuple[str, ...]
    key_assumptions: tuple[str, ...]
    thesis_breakers: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    confidence: str
    status: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "positive_factors": list(self.positive_factors),
            "negative_factors": list(self.negative_factors),
            "key_assumptions": list(self.key_assumptions),
            "thesis_breakers": list(self.thesis_breakers),
            "evidence_ids": list(self.evidence_ids),
            "confidence": self.confidence,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class AdvancedCheckResult:
    name: str
    status: str
    detail: str
    findings: tuple[AdvancedFinding, ...]
    thesis_breakers: tuple[ThesisBreaker, ...]
    thesis: InvestmentThesis
    asymmetry: dict[str, Any]
    scenarios: dict[str, Any]
    hard_fail_status: str
    timings: dict[str, float] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ui_name": "Advanced Investment Check",
            "status": self.status,
            "detail": self.detail,
            "findings": [item.to_public_dict() for item in self.findings],
            "thesis_breakers": [item.to_public_dict() for item in self.thesis_breakers],
            "thesis": self.thesis.to_public_dict(),
            "asymmetry": dict(self.asymmetry),
            "scenarios": dict(self.scenarios),
            "hard_fail_status": self.hard_fail_status,
            "timings": dict(self.timings),
            "replaces_core_dsp": False,
            "alters_dcf": False,
        }


def _identity_label(dataset: VerifiedDataset | None) -> str | None:
    if dataset is None or dataset.identity is None:
        return None
    ident = dataset.identity
    return f"{ident.isin}:{ident.mic}"


def _as_of(dataset: VerifiedDataset | None) -> str | None:
    if dataset is None or dataset.financials is None or dataset.financials.period_end is None:
        return None
    return dataset.financials.period_end.isoformat()


def _finding(
    *,
    finding: str,
    dimension: str,
    evidence: str,
    source: str,
    source_authority: str,
    dataset: VerifiedDataset | None,
    confidence: str,
    severity: str,
    data_class: str,
    verification_status: str,
    evidence_ids: tuple[str, ...] = (),
) -> AdvancedFinding:
    retrieved = None
    if dataset is not None and dataset.shares is not None:
        retrieved = dataset.shares.last_verified_at.isoformat()
    return AdvancedFinding(
        finding=finding,
        dimension=dimension,
        evidence=evidence,
        source=source,
        source_authority=source_authority,
        as_of=_as_of(dataset),
        retrieved_at=retrieved,
        identity=_identity_label(dataset),
        confidence=confidence,
        severity=severity,
        data_class=data_class,
        verification_status=verification_status,
        evidence_ids=evidence_ids,
    )


def _breaker_id(dimension: str, description: str) -> str:
    digest = sha256(f"{dimension}:{description}".encode("utf-8")).hexdigest()[:12]
    return f"tb-{dimension.lower()}-{digest}"


def _mos_band(mos: Decimal | None) -> str:
    if mos is None:
        return MosClassification.UNAVAILABLE.value
    thr = MosThresholds()
    value = float(mos)
    if value >= thr.deep_value:
        return MosClassification.DEEP_VALUE.value
    if value >= thr.undervalued:
        return MosClassification.UNDERVALUED.value
    if value > -thr.fairly_band:
        return MosClassification.FAIRLY_VALUED.value
    if value > thr.extremely_overvalued:
        return MosClassification.OVERVALUED.value
    return MosClassification.EXTREMELY_OVERVALUED.value


def _claim_is_ai(claim: ResearchClaim | EvidenceItem) -> bool:
    source_type = getattr(claim, "source_type", None)
    agent = str(getattr(claim, "agent", "") or "")
    if source_type in {"llm", "agent_claim"}:
        return True
    if agent in {"gemini_find", "chatgpt_verify", "openai_nse_mcp", "claude_review"}:
        return True
    notes = str(getattr(claim, "notes", "") or getattr(claim, "source", "") or "").lower()
    return "llm" in notes or "ai " in notes


def _judge_claim(item: EvidenceItem, *, production: bool) -> str:
    try:
        promoted = EvidenceJudge().promote(item, production=production)
    except (ValueError, TypeError):
        return "UNVERIFIED"
    if promoted.status == "VERIFIED":
        return "VERIFIED"
    if promoted.status in {"REJECTED", "CONFLICT"}:
        return promoted.status
    if promoted.status == "UNAVAILABLE" or _claim_is_ai(item):
        return "UNVERIFIED"
    return "UNVERIFIED"


def evaluate_advanced_check(
    *,
    dataset: VerifiedDataset | None,
    dsp: Any,
    qualitative: QualitativeSnapshot | None,
    listing: SecurityListing | None,
    claims: Sequence[ResearchClaim | EvidenceItem] = (),
    production: bool = False,
    capability: str | None = None,
) -> AdvancedCheckResult:
    """Deterministic advanced check. AI claims cannot become facts."""
    started = perf_counter()
    timings = {"evaluate": 0.0, "complete": 0.0}
    if listing is not None and (
        listing.security_type in UNSUPPORTED_SECURITY_TYPES or not listing.eligibility
    ):
        thesis = InvestmentThesis(
            positive_factors=(),
            negative_factors=("instrument is outside ordinary-equity thesis analysis",),
            key_assumptions=(),
            thesis_breakers=(),
            evidence_ids=(),
            confidence="none",
            status="UNKNOWN",
        )
        timings["complete"] = perf_counter() - started
        return AdvancedCheckResult(
            name=ADVANCED_CHECK_NAME,
            status="UNSUPPORTED",
            detail="ETF / ineligible security is not forced through equity thesis analysis",
            findings=(),
            thesis_breakers=(),
            thesis=thesis,
            asymmetry={"upside": "UNKNOWN", "downside": "UNKNOWN", "probability": "UNKNOWN"},
            scenarios={},
            hard_fail_status="REVIEW_REQUIRED",
            timings=timings,
        )

    findings: list[AdvancedFinding] = []
    breakers: list[ThesisBreaker] = []
    positives: list[str] = []
    negatives: list[str] = []
    assumption_names: list[str] = []
    evidence_ids: list[str] = []

    q = qualitative
    fs_rating = None if q is None else q.financial_strength.get("rating")
    moat_rating = None if q is None else q.moat.get("rating")
    mgmt_rating = None if q is None else q.management.get("rating")
    bq_rating = None if q is None else q.business_quality.get("rating")
    risk_level = None if q is None else q.risk.get("overall_risk_level")

    debt = None if dataset is None else dataset.verified_decimal("debt")
    equity = None if dataset is None else dataset.verified_decimal("equity")
    cash = None if dataset is None else dataset.verified_decimal("cash")
    cfo = None if dataset is None else dataset.verified_decimal("cfo")
    net_income = None if dataset is None else dataset.verified_decimal("net_income")

    if debt is None or equity is None:
        findings.append(
            _finding(
                finding="Leverage / financial survival cannot be scored — debt or equity UNKNOWN",
                dimension="LEVERAGE",
                evidence="verified debt or equity missing",
                source="VerifiedDataset",
                source_authority="primary",
                dataset=dataset,
                confidence="none",
                severity="MEDIUM",
                data_class=DATA_CLASS_VERIFIED_FACT,
                verification_status="UNKNOWN",
            )
        )
        # Missing evidence is UNKNOWN, not a negative finding.
    else:
        findings.append(
            _finding(
                finding=f"Verified debt={debt} equity={equity}"
                + (f" cash={cash}" if cash is not None else ""),
                dimension="LEVERAGE",
                evidence="VerifiedDataset debt/equity",
                source="VerifiedDataset",
                source_authority="primary",
                dataset=dataset,
                confidence="high",
                severity=_FS_TO_SEVERITY.get(str(fs_rating or ""), "MEDIUM"),
                data_class=DATA_CLASS_VERIFIED_FACT,
                verification_status="VERIFIED",
            )
        )
        if fs_rating in {"very_weak", "weak"}:
            negatives.append(f"financial_strength={fs_rating}")
        elif fs_rating in {"strong", "exceptional"}:
            positives.append(f"financial_strength={fs_rating}")

    if moat_rating:
        findings.append(
            _finding(
                finding=f"DSP moat assessment={moat_rating}",
                dimension="MOAT_ATTACK",
                evidence="economic_moat.EconomicEngine",
                source="EconomicEngine",
                source_authority="dsp_methodology",
                dataset=dataset,
                confidence="medium",
                severity=_MOAT_TO_SEVERITY.get(str(moat_rating), "MEDIUM"),
                data_class=DATA_CLASS_DSP_ASSESSMENT,
                verification_status="VERIFIED" if moat_rating else "UNKNOWN",
            )
        )
        if moat_rating in {"wide", "strong"}:
            positives.append(f"moat={moat_rating}")
        elif moat_rating in {"no_moat", "weak"}:
            negatives.append(f"moat={moat_rating}")
    else:
        findings.append(
            _finding(
                finding="Moat deterioration cannot be assessed — engine inputs missing",
                dimension="MOAT_ATTACK",
                evidence="EconomicEngine not calculated",
                source="EconomicEngine",
                source_authority="dsp_methodology",
                dataset=dataset,
                confidence="none",
                severity="MEDIUM",
                data_class=DATA_CLASS_DSP_ASSESSMENT,
                verification_status="UNKNOWN",
            )
        )

    if mgmt_rating:
        findings.append(
            _finding(
                finding=f"DSP management assessment={mgmt_rating}",
                dimension="MANAGEMENT_OWNERSHIP",
                evidence="management_quality.ManagementEngine",
                source="ManagementEngine",
                source_authority="dsp_methodology",
                dataset=dataset,
                confidence="medium",
                severity="HIGH" if mgmt_rating in {"poor", "below_average"} else "LOW",
                data_class=DATA_CLASS_DSP_ASSESSMENT,
                verification_status="VERIFIED",
            )
        )
        if mgmt_rating in {"good", "strong", "excellent"}:
            positives.append(f"management={mgmt_rating}")
        elif mgmt_rating in {"poor", "below_average"}:
            negatives.append(f"management={mgmt_rating}")
    else:
        findings.append(
            _finding(
                finding="Management / ownership UNKNOWN — do not treat narrative as proof",
                dimension="MANAGEMENT_OWNERSHIP",
                evidence="ManagementEngine not calculated",
                source="ManagementEngine",
                source_authority="dsp_methodology",
                dataset=dataset,
                confidence="none",
                severity="MEDIUM",
                data_class=DATA_CLASS_DSP_ASSESSMENT,
                verification_status="UNKNOWN",
            )
        )

    if cfo is None or net_income is None:
        findings.append(
            _finding(
                finding="Earnings quality UNKNOWN — cash conversion cannot be verified",
                dimension="EARNINGS_QUALITY",
                evidence="verified CFO or net_income missing",
                source="VerifiedDataset",
                source_authority="primary",
                dataset=dataset,
                confidence="none",
                severity="MEDIUM",
                data_class=DATA_CLASS_VERIFIED_FACT,
                verification_status="UNKNOWN",
            )
        )
    else:
        findings.append(
            _finding(
                finding=f"Verified net_income={net_income} cfo={cfo}",
                dimension="EARNINGS_QUALITY",
                evidence="VerifiedDataset net_income/cfo",
                source="VerifiedDataset",
                source_authority="primary",
                dataset=dataset,
                confidence="high",
                severity="LOW",
                data_class=DATA_CLASS_VERIFIED_FACT,
                verification_status="VERIFIED",
            )
        )

    if capability == "bank_equity":
        findings.append(
            _finding(
                finding="Bank equity — ordinary-equity DCF is not forced; solvency uses financial-strength rules",
                dimension="PERMANENT_LOSS",
                evidence="research_plan.classify_research_capability",
                source="research_capability",
                source_authority="dsp_methodology",
                dataset=dataset,
                confidence="high",
                severity="MEDIUM",
                data_class=DATA_CLASS_DSP_ASSESSMENT,
                verification_status="VERIFIED",
            )
        )

    dcf_status = getattr(getattr(dsp, "dcf", None), "status", None) if dsp is not None else None
    mos_value = getattr(getattr(dsp, "margin_of_safety", None), "value", None) if dsp is not None else None
    mos_band = _mos_band(mos_value if isinstance(mos_value, Decimal) else None)
    if dcf_status != "CALCULATED":
        findings.append(
            _finding(
                finding="Intrinsic value not established — DCF blocked or missing",
                dimension="VALUATION_MOS",
                evidence=str(getattr(getattr(dsp, "dcf", None), "detail", "DCF unavailable")),
                source="DcfMethod",
                source_authority="dsp_methodology",
                dataset=dataset,
                confidence="high",
                severity="HIGH",
                data_class=DATA_CLASS_DSP_ASSESSMENT,
                verification_status="UNKNOWN",
            )
        )
        negatives.append("DCF blocked")
    else:
        findings.append(
            _finding(
                finding=f"DCF CALCULATED; existing MoS classification={mos_band}",
                dimension="VALUATION_MOS",
                evidence="valuation.methods.dcf + MosThresholds",
                source="DcfMethod",
                source_authority="dsp_methodology",
                dataset=dataset,
                confidence="high",
                severity="HIGH" if mos_band in {"overvalued", "extremely_overvalued", "unavailable"} else "LOW",
                data_class=DATA_CLASS_DSP_ASSESSMENT,
                verification_status="VERIFIED",
            )
        )

    findings.append(
        _finding(
            finding="Industry / regulatory / external threats have no connected primary feed",
            dimension="INDUSTRY_EXTERNAL",
            evidence="composition risk_view marks regulatory/technology as unavailable",
            source="risk_view",
            source_authority="dsp_methodology",
            dataset=dataset,
            confidence="none",
            severity="MEDIUM",
            data_class=DATA_CLASS_DSP_ASSESSMENT,
            verification_status="UNKNOWN",
        )
    )

    findings.append(
        _finding(
            finding="Investor-bias attack is required; excellence cannot be assumed",
            dimension="INVESTOR_BIAS",
            evidence="confirmation / anchoring / story bias must be attacked explicitly",
            source="advanced_check",
            source_authority="dsp_methodology",
            dataset=dataset,
            confidence="high",
            severity="MEDIUM",
            data_class=DATA_CLASS_DSP_ASSESSMENT,
            verification_status="VERIFIED",
        )
    )

    if risk_level:
        findings.append(
            _finding(
                finding=f"Ordinal overall_risk_level={risk_level} (not a numeric score)",
                dimension="PERMANENT_LOSS",
                evidence="dsp_platform.composition.risk_view",
                source="risk_view",
                source_authority="dsp_methodology",
                dataset=dataset,
                confidence="medium",
                severity=_RISK_TO_SEVERITY.get(str(risk_level), "MEDIUM"),
                data_class=DATA_CLASS_DSP_ASSESSMENT,
                verification_status="VERIFIED",
            )
        )

    for claim in claims:
        text = str(
            getattr(claim, "notes", None)
            or getattr(claim, "value", None)
            or getattr(claim, "field", "")
        )
        if looks_like_injection(text) or "assume this is an excellent" in text.lower():
            findings.append(
                _finding(
                    finding="Bias / instruction injection rejected; thesis excellence not accepted",
                    dimension="INVESTOR_BIAS",
                    evidence=text[:240],
                    source="prompt_guard",
                    source_authority="policy",
                    dataset=dataset,
                    confidence="high",
                    severity="HIGH",
                    data_class=DATA_CLASS_AI_INTERPRETATION,
                    verification_status="REJECTED",
                )
            )
            continue
        field_name = str(getattr(claim, "field", "") or "")
        if field_name in {"intrinsic_value", "dcf", "fair_value", "iv"}:
            findings.append(
                _finding(
                    finding="AI intrinsic-value proposal ignored; DcfMethod recalculates",
                    dimension="VALUATION_MOS",
                    evidence=text[:240],
                    source="AI",
                    source_authority="none",
                    dataset=dataset,
                    confidence="none",
                    severity="HIGH",
                    data_class=DATA_CLASS_AI_INTERPRETATION,
                    verification_status="REJECTED",
                )
            )
            continue
        if field_name in {"risk", "risk_score"} or "risk = " in text.lower() or "9/10" in text:
            findings.append(
                _finding(
                    finding="AI numeric risk score ignored — methodology has no 0–10 risk score",
                    dimension="PERMANENT_LOSS",
                    evidence=text[:240],
                    source="AI",
                    source_authority="none",
                    dataset=dataset,
                    confidence="none",
                    severity="MEDIUM",
                    data_class=DATA_CLASS_AI_INTERPRETATION,
                    verification_status="REJECTED",
                )
            )
            continue
        if isinstance(claim, EvidenceItem):
            status = _judge_claim(claim, production=production)
            primary = None if dataset is None else dataset.verified_decimal(claim.field)
            if primary is not None and claim.value and str(primary) != str(claim.value):
                status = "CONFLICT"
            findings.append(
                _finding(
                    finding=f"AI/untrusted claim field={claim.field} value={claim.value}",
                    dimension=(
                        "LEVERAGE"
                        if claim.field == "debt"
                        else (
                            "MANAGEMENT_OWNERSHIP"
                            if "govern" in text.lower() or "fraud" in text.lower()
                            else "MOAT_ATTACK" if "moat" in text.lower() else "INVESTOR_BIAS"
                        )
                    ),
                    evidence=f"EvidenceJudge status={status}",
                    source=claim.source or "AI",
                    source_authority="none" if _claim_is_ai(claim) else (claim.source_type or "unknown"),
                    dataset=dataset,
                    confidence="none",
                    severity="HIGH" if status in {"REJECTED", "CONFLICT", "UNAVAILABLE"} else "MEDIUM",
                    data_class=DATA_CLASS_RESEARCH_CLAIM if _claim_is_ai(claim) else DATA_CLASS_VERIFIED_FACT,
                    verification_status="UNVERIFIED" if status in {"UNKNOWN", "UNAVAILABLE"} else status,
                    evidence_ids=(claim.evidence_id,),
                )
            )
            if status in {"REJECTED", "CONFLICT"}:
                negatives.append(f"untrusted claim {claim.field} {status}")
            continue
        findings.append(
            _finding(
                finding=f"Research claim {field_name or text[:80]}: {text[:160]}",
                dimension=(
                    "MANAGEMENT_OWNERSHIP"
                    if "govern" in text.lower() or "fraud" in text.lower()
                    else "MOAT_ATTACK" if "moat" in text.lower() else "INVESTOR_BIAS"
                ),
                evidence="ResearchClaim is never automatically VERIFIED",
                source=str(getattr(claim, "agent", "AI") or "AI"),
                source_authority="none",
                dataset=dataset,
                confidence="none",
                severity="MEDIUM",
                data_class=DATA_CLASS_RESEARCH_CLAIM,
                verification_status="UNVERIFIED",
                evidence_ids=tuple(getattr(claim, "evidence_ids", ()) or ()),
            )
        )

    for item in findings:
        if item.verification_status in {"VERIFIED", "UNKNOWN"} and item.severity in {
            "HIGH",
            "CRITICAL",
        }:
            bid = _breaker_id(item.dimension, item.finding)
            breakers.append(
                ThesisBreaker(
                    id=bid,
                    dimension=item.dimension,
                    description=item.finding,
                    evidence_ids=item.evidence_ids,
                    severity=item.severity,
                    current_status=item.verification_status,
                    trigger=item.finding,
                    monitoring_metric=f"{item.dimension} (descriptive only — no monitor built)",
                    verification_status=item.verification_status,
                )
            )
            evidence_ids.extend(item.evidence_ids)

    if q is not None:
        positives.extend(str(x) for x in q.moat.get("positive_factors") or ())
        positives.extend(str(x) for x in q.management.get("strengths") or ())
        negatives.extend(str(x) for x in q.moat.get("negative_factors") or ())
        negatives.extend(str(x) for x in q.management.get("weaknesses") or ())

    scenarios: dict[str, Any] = {}
    if dsp is not None:
        raw_scenarios = getattr(dsp, "scenarios", {}) or {}
        for name in ("BEAR", "BASE", "BULL"):
            row = raw_scenarios.get(name)
            scenarios[name] = None if row is None else {
                "status": getattr(row, "status", None),
                "detail": getattr(row, "detail", None),
                "value": None if getattr(row, "value", None) is None else str(row.value),
            }
            assumption_names.extend(list(getattr(row, "assumption_ids", ()) or ()))

    bear = scenarios.get("BEAR") or {}
    bull = scenarios.get("BULL") or {}
    base = scenarios.get("BASE") or {}
    asymmetry = {
        "upside": bull.get("status") or "UNKNOWN",
        "downside": bear.get("status") or "UNKNOWN",
        "base": base.get("status") or "UNKNOWN",
        "probability": "UNKNOWN",
        "detail": "probabilities are not defined by existing methodology; BEAR/BASE/BULL are existing DCF scenarios",
        "what_breaks_bear": "DCF BEAR blocked or missing assumptions" if bear.get("status") != "CALCULATED" else "existing BEAR DCF stands until inputs change",
        "what_supports_base": "existing BASE DcfMethod" if base.get("status") == "CALCULATED" else "BASE DCF not calculated",
        "what_would_justify_bull": "existing BULL DCF only if ACCEPTED BULL assumptions exist",
    }

    hard = "NONE"
    if dcf_status != "CALCULATED":
        hard = "REVIEW_REQUIRED"
    if fs_rating == "very_weak":
        hard = "REVIEW_REQUIRED"
    if mos_band == MosClassification.UNAVAILABLE.value:
        hard = "REVIEW_REQUIRED"

    verified_facts = dataset is not None and dataset.identity_status == "VERIFIED"
    high_breakers = [item for item in breakers if item.severity in {"HIGH", "CRITICAL"} and item.verification_status == "VERIFIED"]
    if not verified_facts:
        thesis_status = "UNKNOWN"
        confidence = "none"
    elif dcf_status != "CALCULATED" or not positives:
        thesis_status = "WEAK" if negatives else "UNKNOWN"
        confidence = "low"
    elif high_breakers and positives:
        thesis_status = "MIXED"
        confidence = "medium"
    elif positives and not high_breakers and dcf_status == "CALCULATED":
        thesis_status = "SUPPORTED"
        confidence = "medium"
    else:
        thesis_status = "MIXED"
        confidence = "low"
    if bq_rating in {"poor", "weak"} and thesis_status == "SUPPORTED":
        thesis_status = "MIXED"

    thesis = InvestmentThesis(
        positive_factors=tuple(dict.fromkeys(positives)),
        negative_factors=tuple(dict.fromkeys(negatives)),
        key_assumptions=tuple(dict.fromkeys(assumption_names)),
        thesis_breakers=tuple(item.id for item in breakers),
        evidence_ids=tuple(dict.fromkeys(evidence_ids)),
        confidence=confidence,
        status=thesis_status,
    )
    timings["evaluate"] = perf_counter() - started
    timings["complete"] = timings["evaluate"]
    status = "PARTIAL" if verified_facts else "UNKNOWN"
    if listing is not None and capability == "bank_equity":
        status = "PARTIAL"
    return AdvancedCheckResult(
        name=ADVANCED_CHECK_NAME,
        status=status,
        detail="Advanced check is separate from core DSP; AI cannot change DCF or weights",
        findings=tuple(findings),
        thesis_breakers=tuple(breakers),
        thesis=thesis,
        asymmetry=asymmetry,
        scenarios=scenarios,
        hard_fail_status=hard,
        timings=timings,
    )
