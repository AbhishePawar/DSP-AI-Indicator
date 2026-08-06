"""Extract immutable research snapshots from completed analyse payloads.

Pure consumer of public composition / report dicts. Never calls engines.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.research_intelligence.hashing import content_sha256
from dsp_platform.research_intelligence.models import (
    ResearchSnapshot,
    freeze_mapping,
    utc_now,
)

__all__ = [
    "build_snapshot_from_analyse_payload",
    "confidence_label_from_value",
    "extract_nested",
]


def confidence_label_from_value(confidence: float | None) -> str | None:
    if confidence is None:
        return None
    if confidence >= 0.7:
        return "high"
    if confidence >= 0.4:
        return "medium"
    return "low"


def extract_nested(payload: Mapping[str, Any] | None, *paths: str) -> Any:
    """Return the first non-None value found at dotted paths."""
    if not isinstance(payload, Mapping):
        return None
    for path in paths:
        cur: Any = payload
        ok = True
        for part in path.split("."):
            if isinstance(cur, Mapping) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur is not None:
            return cur
    return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.strip().lower() in {
        "data unavailable.",
        "unable to calculate.",
        "unavailable",
        "n/a",
    }:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {
        "data unavailable.",
        "unable to calculate.",
        "unavailable",
        "none",
    }:
        return None
    return text


def build_snapshot_from_analyse_payload(
    payload: Mapping[str, Any],
    *,
    research_id: str | None = None,
    timestamp: str | None = None,
    ticker: str | None = None,
    company: str | None = None,
    exchange: str | None = None,
    research_version: str | None = None,
    model_version: str | None = None,
) -> ResearchSnapshot:
    """Build an immutable snapshot from a public analyse / composition payload."""
    if not isinstance(payload, Mapping):
        raise ValueError("analyse payload must be a mapping")

    recommendation = _as_str(
        extract_nested(
            payload,
            "investment_recommendation.decision",
            "investment_recommendation.label",
            "investment_recommendation.recommendation",
            "recommendation_summary.label",
            "recommendation_summary.decision",
            "recommendation",
            "stages.investment_recommendation.decision",
        )
    )
    confidence = _as_float(
        extract_nested(
            payload,
            "investment_recommendation.confidence",
            "recommendation_summary.confidence",
            "confidence",
            "stages.investment_recommendation.confidence",
        )
    )
    conf_label = _as_str(
        extract_nested(
            payload,
            "investment_recommendation.confidence_label",
            "recommendation_summary.confidence_label",
            "confidence_label",
        )
    ) or confidence_label_from_value(confidence)

    price = _as_float(
        extract_nested(
            payload,
            "market.price",
            "market.current_price",
            "valuation.current_price",
            "valuation.price",
            "current_market_price",
            "price",
            "header.price",
        )
    )
    iv = _as_float(
        extract_nested(
            payload,
            "valuation.intrinsic_value",
            "valuation.iv",
            "intrinsic_value",
            "header.intrinsic_value",
            "header.iv",
        )
    )
    mos = _as_float(
        extract_nested(
            payload,
            "valuation.margin_of_safety",
            "investment_recommendation.margin_of_safety",
            "recommendation_summary.margin_of_safety",
            "margin_of_safety",
            "header.margin_of_safety",
            "header.mos",
        )
    )

    bq = _as_float(
        extract_nested(
            payload,
            "business_quality.score",
            "business_quality.overall_score",
            "scores.business_quality",
            "header.business_quality",
        )
    )
    mgmt = _as_float(
        extract_nested(
            payload,
            "management.score",
            "management.overall_score",
            "scores.management",
            "header.management",
        )
    )
    moat = _as_float(
        extract_nested(
            payload,
            "economic_moat.score",
            "moat.score",
            "scores.moat",
            "header.moat",
        )
    )
    risk = _as_float(
        extract_nested(
            payload,
            "risk.score",
            "risk.overall_score",
            "scores.risk",
            "header.risk",
        )
    )

    committee = _as_str(
        extract_nested(
            payload,
            "investment_committee.decision",
            "investment_committee.consensus",
            "ai_committee.decision",
            "stages.investment_committee.decision",
        )
    )
    explain = _as_str(
        extract_nested(
            payload,
            "explainability.summary",
            "explainability.executive_summary",
            "explanation.summary",
            "header.explainability_summary",
        )
    )

    evidence_raw = extract_nested(
        payload,
        "evidence.refs",
        "evidence_refs",
        "citations",
        "provenance.evidence_refs",
    )
    evidence_refs: list[str] = []
    if isinstance(evidence_raw, (list, tuple)):
        for item in evidence_raw:
            if isinstance(item, Mapping):
                ref = item.get("id") or item.get("ref") or item.get("path")
                if ref:
                    evidence_refs.append(str(ref))
            elif item is not None:
                evidence_refs.append(str(item))

    source_conf = _as_float(
        extract_nested(
            payload,
            "source_confidence",
            "provenance.source_confidence",
            "data_quality.source_confidence",
        )
    )

    symbol = _as_str(ticker) or _as_str(
        extract_nested(payload, "symbol", "ticker", "metadata.symbol", "header.symbol")
    )
    company_name = _as_str(company) or _as_str(
        extract_nested(payload, "company", "company_name", "header.company")
    )
    exch = _as_str(exchange) or _as_str(
        extract_nested(payload, "exchange", "market.exchange", "header.exchange")
    )
    sector = _as_str(extract_nested(payload, "sector", "company.sector", "header.sector"))
    industry = _as_str(
        extract_nested(payload, "industry", "company.industry", "header.industry")
    )

    rid = research_id or str(uuid.uuid4())
    ts = timestamp or utc_now().isoformat()
    rver = research_version or _as_str(
        extract_nested(payload, "research_version", "metadata.research_version")
    )
    mver = model_version or _as_str(
        extract_nested(payload, "model_version", "metadata.model_version")
    )

    pre_hash = {
        "research_id": rid,
        "symbol": symbol,
        "company": company_name,
        "exchange": exch,
        "sector": sector,
        "industry": industry,
        "timestamp": ts,
        "recommendation": recommendation,
        "confidence": confidence,
        "confidence_label": conf_label,
        "intrinsic_value": iv,
        "price": price,
        "margin_of_safety": mos,
        "business_quality_score": bq,
        "management_score": mgmt,
        "moat_score": moat,
        "risk_score": risk,
        "ai_committee_decision": committee,
        "explainability_summary": explain,
        "evidence_refs": evidence_refs,
        "source_confidence": source_conf,
        "research_version": rver,
        "model_version": mver,
    }
    digest = content_sha256(pre_hash)

    return ResearchSnapshot(
        research_id=rid,
        company=company_name,
        exchange=exch,
        sector=sector,
        industry=industry,
        timestamp=ts,
        recommendation=recommendation,
        confidence=confidence,
        confidence_label=conf_label,
        intrinsic_value=iv,
        price=price,
        margin_of_safety=mos,
        business_quality_score=bq,
        management_score=mgmt,
        moat_score=moat,
        risk_score=risk,
        ai_committee_decision=committee,
        explainability_summary=explain,
        evidence_refs=tuple(evidence_refs),
        source_confidence=source_conf,
        research_version=rver,
        model_version=mver,
        content_sha256=digest,
        symbol=symbol.upper() if symbol else None,
        metadata=dict(
            freeze_mapping(
                {
                    "capture_source": "analyse_payload",
                    "engines_called": False,
                }
            )
            or {}
        ),
    )
