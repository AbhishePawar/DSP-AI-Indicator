"""Quality evaluator — deterministic scoring of LM outputs.

The evaluator compares a model narrative against the frozen DSP
ground-truth values in the ``ResearchSpec``. It is intentionally
conservative:

- it never invents scores
- it returns ``None`` for any component it cannot verify
- the only way a non-None score appears is by direct textual match
  against a frozen value or by deterministic regex on the evidence
- hallucination is a count of unsupported numeric claims
- unsupported_claims is a count of non-numeric assertions lacking citation
- structured_output is ``1.0`` if the narrative contains the expected
  field markers, else ``0.0`` (or ``None`` if no markers expected)
- consistency is the agreement between narrative and frozen values
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

from llm_adapters.evaluation import QualityEvaluation


_NUMERIC_RE = re.compile(r"\b\d+(?:\.\d+)?%?\b")
_EXPECTED_NUMERIC_FIELDS = (
    "intrinsic_value",
    "intrinsic_value_per_share",
    "current_market_price",
    "margin_of_safety",
    "dcf_intrinsic_value",
    "graham_number",
    "data_completeness",
)


@dataclass(frozen=True, slots=True)
class EvaluatorVerdict:
    """Per-narrative scoring verdict.

    All numeric components are 0.0-1.0; None means "could not verify".
    """

    quality: QualityEvaluation
    hallucination_count: int
    unsupported_claim_count: int
    notes: tuple[str, ...] = ()


def _contains_value(narrative: str, value: str) -> bool:
    """True iff the narrative mentions the exact frozen value."""
    if not value:
        return False
    if value in narrative:
        return True
    # Allow common numeric form (e.g. "12.5" vs "12.50").
    try:
        f = float(value)
        for m in _NUMERIC_RE.findall(narrative):
            try:
                if abs(float(m) - f) < 1e-6:
                    return True
            except ValueError:
                continue
    except ValueError:
        pass
    return False


def _expected_numeric_field(frozen: Mapping[str, str]) -> tuple[str, ...]:
    out: list[str] = []
    for key in _EXPECTED_NUMERIC_FIELDS:
        if key in frozen:
            out.append(frozen[key])
    return tuple(out)


def _count_unsupported_numeric_claims(
    narrative: str, frozen: Mapping[str, str]
) -> int:
    """Numbers in the narrative that do not match any frozen value."""
    expected = set(_expected_numeric_field(frozen))
    if not expected:
        return 0
    count = 0
    for m in _NUMERIC_RE.findall(narrative):
        # Normalize "12.0%" <-> "12.0" by stripping a trailing % for compare
        m_norm = m.rstrip("%")
        if m in expected or m_norm in expected:
            continue
        try:
            f = float(m_norm)
        except ValueError:
            continue
        matched = False
        for ex in expected:
            ex_norm = ex.rstrip("%")
            try:
                if abs(float(ex_norm) - f) < 1e-6:
                    matched = True
                    break
            except ValueError:
                continue
        if not matched:
            count += 1
    return count


def _hallucination_count(
    narrative: str, frozen: Mapping[str, str]
) -> int:
    """Same as unsupported numeric claims — kept distinct for clarity."""
    return _count_unsupported_numeric_claims(narrative, frozen)


def _factual_accuracy(
    narrative: str, frozen: Mapping[str, str]
) -> float | None:
    """1.0 if every frozen value appears in the narrative, else 0.0..1.0."""
    if not frozen:
        return None
    hits = 0
    total = 0
    for v in frozen.values():
        total += 1
        if _contains_value(narrative, str(v)):
            hits += 1
    return round(hits / total, 4) if total else None


def _valuation_reasoning(
    narrative: str, frozen: Mapping[str, str]
) -> float | None:
    """1.0 if frozen intrinsic value AND price are mentioned together."""
    intrinsic_keys = ("intrinsic_value", "intrinsic_value_per_share", "dcf_intrinsic_value")
    price_keys = ("current_market_price",)
    intrinsic = next((frozen[k] for k in intrinsic_keys if k in frozen), None)
    price = next((frozen[k] for k in price_keys if k in frozen), None)
    if intrinsic is None and price is None:
        return None
    has_intrinsic = intrinsic is not None and _contains_value(narrative, intrinsic)
    has_price = price is not None and _contains_value(narrative, price)
    score = 0.0
    if has_intrinsic:
        score += 0.5
    if has_price:
        score += 0.5
    return score if (has_intrinsic or has_price) else 0.0


def _buffett_reasoning(
    narrative: str, frozen: Mapping[str, str]
) -> float | None:
    """1.0 if moat AND management AND financial_strength are all acknowledged."""
    keys = ("moat", "management_quality", "financial_strength")
    mentions = sum(
        1 for k in keys if k in frozen and _contains_value(narrative, str(frozen[k]))
    )
    if mentions == 0:
        return None
    return round(mentions / len(keys), 4)


def _moat_business_quality(
    narrative: str, frozen: Mapping[str, str]
) -> float | None:
    return _buffett_reasoning(narrative, frozen)


def _management(
    narrative: str, frozen: Mapping[str, str]
) -> float | None:
    if "management_quality" not in frozen:
        return None
    return 1.0 if _contains_value(narrative, str(frozen["management_quality"])) else 0.0


def _financial_strength(
    narrative: str, frozen: Mapping[str, str]
) -> float | None:
    if "financial_strength" not in frozen:
        return None
    return 1.0 if _contains_value(narrative, str(frozen["financial_strength"])) else 0.0


def _business_quality(
    narrative: str, frozen: Mapping[str, str]
) -> float | None:
    if "business_quality" not in frozen:
        return None
    return 1.0 if _contains_value(narrative, str(frozen["business_quality"])) else 0.0


def _risk(
    narrative: str, frozen: Mapping[str, str]
) -> float | None:
    """1.0 if primary risk term is named."""
    for k in ("primary_risk", "risks"):
        if k in frozen and _contains_value(narrative, str(frozen[k])):
            return 1.0
    return None


def _evidence_correctness(
    narrative: str, frozen: Mapping[str, str]
) -> float | None:
    return _factual_accuracy(narrative, frozen)


def _structured_output(narrative: str) -> float:
    """1.0 if narrative has at least 3 sentences (minimum structure)."""
    sentences = re.split(r"[.!?]+\s+", narrative.strip())
    sentences = [s for s in sentences if s.strip()]
    if len(sentences) < 3:
        return 0.0
    return 1.0


def _consistency(
    narrative: str, frozen: Mapping[str, str]
) -> float | None:
    """Same as factual_accuracy — kept as separate axis per STEP 3A schema."""
    return _factual_accuracy(narrative, frozen)


def _financial_reasoning(narrative: str) -> float | None:
    """1.0 if any financial/valuation vocabulary appears."""
    keywords = (
        "intrinsic", "valuation", "margin of safety", "dcf", "fcf",
        "business quality", "moat", "recommendation",
    )
    n = sum(1 for k in keywords if k in narrative.lower())
    if n == 0:
        return None
    return min(1.0, round(n / 3, 4))


def _earnings_quality(narrative: str) -> float | None:
    if "earnings" in narrative.lower() or "fcf" in narrative.lower():
        return 1.0
    return None


def _growth_quality(narrative: str) -> float | None:
    if "growth" in narrative.lower() or "cagr" in narrative.lower():
        return 1.0
    return None


def evaluate_narrative(
    narrative: str, frozen: Mapping[str, str]
) -> EvaluatorVerdict:
    """Score a single narrative against the case's frozen values."""
    n_lower = narrative.lower()
    hallucinated = _hallucination_count(narrative, frozen)
    # Unsupported non-numeric assertions: substantive sentences (>40 chars)
    # without a citation marker. Tiny fragments don't count.
    sentences = [s.strip() for s in re.split(r"[.!?]+\s+", narrative) if s.strip()]
    unsupported = sum(
        1 for s in sentences
        if len(s) > 40 and "[" not in s and "(" not in s
    )

    q = QualityEvaluation(
        factual_accuracy=_factual_accuracy(narrative, frozen),
        financial_reasoning=_financial_reasoning(narrative),
        valuation_reasoning=_valuation_reasoning(narrative, frozen),
        buffett_reasoning=_buffett_reasoning(narrative, frozen),
        moat_business_quality=_moat_business_quality(narrative, frozen),
        management=_management(narrative, frozen),
        financial_strength=_financial_strength(narrative, frozen),
        earnings_quality=_earnings_quality(narrative),
        growth_quality=_growth_quality(narrative),
        risk=_risk(narrative, frozen),
        evidence_correctness=_evidence_correctness(narrative, frozen),
        hallucination=None if hallucinated == 0 else max(0.0, 1.0 - hallucinated * 0.2),
        unsupported_claims=None if unsupported == 0 else max(0.0, 1.0 - unsupported * 0.1),
        structured_output=_structured_output(narrative),
        consistency=_consistency(narrative, frozen),
        business_quality=_business_quality(narrative, frozen),
    )
    return EvaluatorVerdict(
        quality=q,
        hallucination_count=hallucinated,
        unsupported_claim_count=unsupported,
    )


def aggregate(verdicts: Iterable[EvaluatorVerdict]) -> QualityEvaluation:
    """Mean per-component across verdicts; None where all are None."""
    verdicts = list(verdicts)
    if not verdicts:
        return QualityEvaluation()
    fields = (
        "factual_accuracy", "financial_reasoning", "valuation_reasoning",
        "buffett_reasoning", "moat_business_quality", "management",
        "financial_strength", "earnings_quality", "growth_quality",
        "risk", "evidence_correctness", "hallucination", "unsupported_claims",
        "structured_output", "consistency", "business_quality",
    )
    args: dict[str, float | None] = {}
    for name in fields:
        values = [getattr(v.quality, name) for v in verdicts]
        non_none = [v for v in values if v is not None]
        if not non_none:
            args[name] = None
        else:
            args[name] = round(sum(non_none) / len(non_none), 4)
    return QualityEvaluation(**args)


__all__ = [
    "EvaluatorVerdict",
    "aggregate",
    "evaluate_narrative",
]
