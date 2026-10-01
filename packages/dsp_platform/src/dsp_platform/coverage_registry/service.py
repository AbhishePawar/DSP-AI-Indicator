"""Coverage registry service — record after ``/analyse``; serve coverage views.

Pure consumer of the public ``/analyse`` payload. Never calls engines or
providers. Every aggregate is a count / copy over recorded rows; every signal
is a deterministic comparison between two consecutive records of the same
symbol with both values quoted.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from dsp_platform.coverage_registry.models import CoverageRecord, letter_rating
from dsp_platform.coverage_registry.store import (
    CoverageRegistryStore,
    get_coverage_registry_store,
)
from dsp_platform.research_intelligence.capture import extract_nested

__all__ = [
    "RATING_ORDER",
    "CoverageRegistryService",
    "get_coverage_registry_service",
]

RATING_ORDER: tuple[str, ...] = ("A+", "A", "B+", "B", "C", "D", "F")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _f(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Mapping):
        return _f(value.get("value"))
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if out != out else out


def _s(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _bounded_score(value: Any) -> float | None:
    """Keep a published 0–100 stage score. Never rescale a ratio into one."""
    score = _f(value)
    if score is None or score < 0 or score > 100:
        return None
    return score


def _stage_score(payload: Mapping[str, Any], stage: str) -> float | None:
    rows = payload.get("stage_summaries")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, Mapping) and str(row.get("stage") or "") == stage:
            return _bounded_score(row.get("score"))
    return None


_QUALITY_SHAPE_AXES: tuple[str, ...] = (
    "profitability",
    "growth",
    "margins",
    "valuation",
    "cash_flow",
    "low_debt",
)
_RADAR_LABELS: tuple[tuple[str, str], ...] = (
    ("Profitability", "profitability"),
    ("Growth", "growth"),
    ("Margins", "margins"),
    ("Valuation", "valuation"),
    ("Cash Flow", "cash_flow"),
    ("Low Debt", "low_debt"),
)


def quality_shape_from_record(row: Mapping[str, Any] | None) -> dict[str, float | None]:
    """ZIP comparison axes. Only Growth can be filled, and only from the
    published ``growth_quality`` stage score. Ratios are not renormalised.
    """
    shape = {axis: None for axis in _QUALITY_SHAPE_AXES}
    if not row:
        return shape
    shape["growth"] = _bounded_score(row.get("growth_quality_score"))
    return shape


def radar_from_shape(shape: Mapping[str, float | None]) -> dict[str, float | None]:
    return {label: shape.get(key) for label, key in _RADAR_LABELS}


def _rank(rating: str | None) -> int | None:
    if rating is None or rating not in RATING_ORDER:
        return None
    # Higher is better: A+ → 6 … F → 0
    return len(RATING_ORDER) - 1 - RATING_ORDER.index(rating)


class CoverageRegistryService:
    def __init__(self, store: CoverageRegistryStore | None = None) -> None:
        self._store = store or get_coverage_registry_store()

    @property
    def store(self) -> CoverageRegistryStore:
        return self._store

    # -- write ------------------------------------------------------------
    def record_from_payload(
        self,
        payload: Mapping[str, Any],
        *,
        ticker: str | None,
        exchange: str | None = None,
        company: str | None = None,
        owner_user_id: str | None = None,
        research_id: str | None = None,
        as_of: str | None = None,
    ) -> CoverageRecord | None:
        symbol = _s(ticker) or _s(
            extract_nested(payload, "dsp_analysis.identity.ticker", "symbol", "ticker")
        )
        if not symbol:
            return None
        score = _f(extract_nested(payload, "business_quality.score"))
        record = CoverageRecord(
            record_id=str(uuid.uuid4()),
            symbol=symbol.upper(),
            exchange=_s(exchange),
            company_name=_s(company)
            or _s(extract_nested(payload, "dsp_analysis.identity.company_name")),
            sector=_s(
                extract_nested(
                    payload, "dsp_analysis.identity.sector", "fundamental_metrics.sector.value"
                )
            ),
            industry=_s(
                extract_nested(
                    payload,
                    "dsp_analysis.identity.industry",
                    "fundamental_metrics.industry.value",
                )
            ),
            as_of=as_of or datetime.now(tz=UTC).isoformat(),
            business_quality_score=score,
            rating=letter_rating(score),
            recommendation=_s(
                extract_nested(
                    payload, "recommendation_summary.label", "recommendation_summary.decision"
                )
            ),
            price=_f(
                extract_nested(
                    payload,
                    "server_valuation.current_market_price",
                    "fundamental_metrics.price.value",
                )
            ),
            market_cap=_f(extract_nested(payload, "fundamental_metrics.market_cap.value")),
            pe=_f(extract_nested(payload, "fundamental_metrics.pe.value")),
            roe=_f(extract_nested(payload, "fundamental_metrics.roe.value")),
            roce=_f(extract_nested(payload, "fundamental_metrics.roce.value")),
            debt_to_equity=_f(
                extract_nested(payload, "fundamental_metrics.debt_to_equity.value")
            ),
            revenue_growth=_f(
                extract_nested(payload, "fundamental_metrics.revenue_growth.value")
            ),
            fcf=_f(extract_nested(payload, "fundamental_metrics.fcf.value")),
            growth_quality_score=_stage_score(payload, "growth_quality"),
            price_change=_f(extract_nested(payload, "server_valuation.price_change")),
            price_change_percent=_f(
                extract_nested(payload, "server_valuation.price_change_percent")
            ),
            intrinsic_value=_f(
                extract_nested(payload, "server_valuation.intrinsic_value_per_share")
            ),
            margin_of_safety=_f(
                extract_nested(
                    payload,
                    "recommendation_summary.margin_of_safety_assessment.margin_of_safety",
                )
            ),
            risk_score=_f(extract_nested(payload, "risk.score", "risk.overall_score")),
            research_id=_s(research_id),
            owner_user_id=_s(owner_user_id),
            metadata={"capture_source": "analyse_payload", "engines_called": False},
        )
        return self._store.append(record)

    # -- reads ------------------------------------------------------------
    def latest(self, symbol: str) -> dict[str, Any] | None:
        row = self._store.latest_for(symbol)
        return row.to_dict() if row else None

    def latest_map(self) -> dict[str, CoverageRecord]:
        return self._store.latest_by_symbol()

    def stats(self) -> dict[str, Any]:
        latest = self._store.latest_by_symbol()
        rated = [r for r in latest.values() if r.rating is not None]
        last = max((r.as_of for r in latest.values()), default=None)
        return {
            "securities_covered": len(latest),
            "dsp_rated": len(rated),
            "a_rated": sum(1 for r in rated if r.rating in {"A", "A+"}),
            "a_plus_rated": sum(1 for r in rated if r.rating == "A+"),
            "last_updated": last,
        }

    def screener(self, rating: str | None = None) -> list[dict[str, Any]]:
        latest = self._store.latest_by_symbol()
        rows = sorted(
            latest.values(),
            key=lambda r: (
                -(r.business_quality_score if r.business_quality_score is not None else -1),
                r.symbol,
            ),
        )
        if rating and rating.upper() != "ALL":
            rows = [r for r in rows if r.rating == rating]
        return [
            {
                "symbol": r.symbol,
                "company_name": r.company_name,
                "rating": r.rating,
                "business_quality_score": r.business_quality_score,
                "sector": r.sector,
                "pe": r.pe,
                "roe": r.roe,
                "roce": r.roce,
                "revenue_growth": r.revenue_growth,
                "fcf": r.fcf,
                "price": r.price,
                "market_cap": r.market_cap,
                "as_of": r.as_of,
                "research_id": r.research_id,
            }
            for r in rows
        ]

    def directory(self) -> list[dict[str, Any]]:
        latest = self._store.latest_by_symbol()
        return [
            {
                "symbol": r.symbol,
                "company_name": r.company_name,
                "exchange": r.exchange,
                "sector": r.sector,
                "industry": r.industry,
                "market_cap": r.market_cap,
                "rating": r.rating,
                "price": r.price,
                "change": r.price_change,
                "change_percent": r.price_change_percent,
                "as_of": r.as_of,
            }
            for r in sorted(latest.values(), key=lambda r: r.symbol)
        ]

    def rating_distribution(self) -> list[dict[str, Any]]:
        latest = self._store.latest_by_symbol()
        counts = {grade: 0 for grade in RATING_ORDER}
        for r in latest.values():
            if r.rating in counts:
                counts[r.rating] += 1
        return [{"rating": grade, "count": counts[grade]} for grade in RATING_ORDER]

    def coverage_growth(self, months: int = 6, *, now: datetime | None = None) -> list[dict[str, Any]]:
        """Cumulative distinct symbols covered / rated at each month end."""
        months = max(1, min(int(months), 24))
        current = (now or datetime.now(tz=UTC)).astimezone(UTC)
        anchors: list[datetime] = []
        y, m = current.year, current.month
        for _ in range(months):
            anchors.append(datetime(y, m, 1, tzinfo=UTC))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        anchors.reverse()

        records = sorted(
            (r for r in self._store.list_all() if _parse_ts(r.as_of) is not None),
            key=lambda r: r.as_of,
        )
        out: list[dict[str, Any]] = []
        for idx, start in enumerate(anchors):
            end = anchors[idx + 1] if idx + 1 < len(anchors) else start.replace(
                year=start.year + (1 if start.month == 12 else 0),
                month=1 if start.month == 12 else start.month + 1,
            )
            covered: set[str] = set()
            rated: set[str] = set()
            for r in records:
                ts = _parse_ts(r.as_of)
                if ts is None or ts >= end:
                    continue
                covered.add(r.symbol)
                if r.rating is not None:
                    rated.add(r.symbol)
            out.append(
                {
                    "month": _MONTHS[start.month - 1],
                    "period": start.strftime("%Y-%m"),
                    "covered": len(covered),
                    "rated": len(rated),
                }
            )
        return out

    def signals(self, *, limit: int = 50, symbol: str | None = None) -> list[dict[str, Any]]:
        """Deterministic changes between consecutive records of a symbol."""
        symbols = [symbol.upper()] if symbol else list(self._store.latest_by_symbol())
        out: list[dict[str, Any]] = []
        for sym in symbols:
            rows = self._store.list_by_symbol(sym)
            for prev, cur in zip(rows, rows[1:]):
                out.extend(self._diff_signals(prev, cur))
        out.sort(key=lambda s: s["timestamp"], reverse=True)
        return out[: max(0, int(limit))]

    @staticmethod
    def _diff_signals(prev: CoverageRecord, cur: CoverageRecord) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        base = {
            "symbol": cur.symbol,
            "company_name": cur.company_name,
            "sector": cur.sector,
            "timestamp": cur.as_of,
            "research_id": cur.research_id,
        }
        pr, cr = _rank(prev.rating), _rank(cur.rating)
        if pr is not None and cr is not None and pr != cr:
            up = cr > pr
            signals.append(
                {
                    **base,
                    "signal_id": f"{cur.record_id}:rating",
                    "type": "upgrade" if up else "downgrade",
                    "label": "Quality upgrade" if up else "Quality downgrade",
                    "from_rating": prev.rating,
                    "to_rating": cur.rating,
                    "severity": "info" if up else "warning",
                    "status": "active",
                    "source": "coverage_registry",
                    "dsp_context": {
                        "from_rating": prev.rating,
                        "to_rating": cur.rating,
                        "from_score": prev.business_quality_score,
                        "to_score": cur.business_quality_score,
                        "research_id": cur.research_id,
                    },
                    "text": (
                        f"DSP rating moved {prev.rating} → {cur.rating} "
                        f"(business quality {prev.business_quality_score:.0f} → "
                        f"{cur.business_quality_score:.0f})"
                        if prev.business_quality_score is not None
                        and cur.business_quality_score is not None
                        else f"DSP rating moved {prev.rating} → {cur.rating}"
                    ),
                }
            )
        if prev.risk_score is not None and cur.risk_score is not None and cur.risk_score > prev.risk_score:
            signals.append(
                {
                    **base,
                    "signal_id": f"{cur.record_id}:risk",
                    "type": "risk",
                    "label": "Risk flag raised",
                    "from_value": prev.risk_score,
                    "to_value": cur.risk_score,
                    "severity": "alert",
                    "status": "active",
                    "source": "coverage_registry",
                    "dsp_context": {
                        "from_risk": prev.risk_score,
                        "to_risk": cur.risk_score,
                        "rating": cur.rating,
                        "research_id": cur.research_id,
                    },
                    "text": f"Risk score rose {prev.risk_score:.0f} → {cur.risk_score:.0f}",
                }
            )
        if (
            prev.margin_of_safety is not None
            and cur.margin_of_safety is not None
            and (prev.margin_of_safety >= 0) != (cur.margin_of_safety >= 0)
        ):
            signals.append(
                {
                    **base,
                    "signal_id": f"{cur.record_id}:valuation",
                    "type": "valuation",
                    "label": "Valuation signal",
                    "from_value": prev.margin_of_safety,
                    "to_value": cur.margin_of_safety,
                    "severity": "warning",
                    "status": "active",
                    "source": "coverage_registry",
                    "dsp_context": {
                        "from_mos": prev.margin_of_safety,
                        "to_mos": cur.margin_of_safety,
                        "price": cur.price,
                        "intrinsic_value": cur.intrinsic_value,
                        "research_id": cur.research_id,
                    },
                    "text": (
                        f"Margin of safety moved {prev.margin_of_safety * 100:+.1f}% → "
                        f"{cur.margin_of_safety * 100:+.1f}%"
                    ),
                }
            )
        return signals

    def today_summary(self, *, now: datetime | None = None) -> dict[str, Any]:
        current = (now or datetime.now(tz=UTC)).astimezone(UTC)
        day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
        todays = [
            s
            for s in self.signals(limit=10_000)
            if (ts := _parse_ts(s["timestamp"])) is not None and ts >= day_start
        ]
        return {
            "new_signals": len(todays),
            "upgrades": sum(1 for s in todays if s["type"] == "upgrade"),
            "downgrades": sum(1 for s in todays if s["type"] == "downgrade"),
            "risk_flags": sum(1 for s in todays if s["type"] == "risk"),
            "as_of": current.isoformat(),
        }

    def recent_research(self, owner_user_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
        rows = sorted(
            self._store.list_by_owner(owner_user_id), key=lambda r: r.as_of, reverse=True
        )
        return [
            {
                "symbol": r.symbol,
                "company_name": r.company_name,
                "title": (
                    f"{r.company_name} — Company Analysis" if r.company_name else f"{r.symbol} — Company Analysis"
                ),
                "rating": r.rating,
                "recommendation": r.recommendation,
                "tags": [t for t in (r.rating, r.recommendation, r.sector) if t],
                "timestamp": r.as_of,
                "research_id": r.research_id,
                "href": f"/analysis?symbol={r.symbol}",
            }
            for r in rows[: max(0, int(limit))]
        ]

    def sectors(self) -> list[str]:
        return sorted(
            {r.sector for r in self._store.latest_by_symbol().values() if r.sector}
        )

    def directory_page(
        self,
        *,
        sector: str | None = None,
        rating: str | None = None,
        q: str | None = None,
        sort: str = "symbol",
        order: str = "asc",
        limit: int = 48,
        offset: int = 0,
    ) -> dict[str, Any]:
        rows = self.directory()
        if sector and sector.lower() not in {"all", "all sectors"}:
            rows = [r for r in rows if (r.get("sector") or "").lower() == sector.lower()]
        if rating and rating.upper() not in {"ALL", "ALL RATINGS"}:
            rows = [r for r in rows if r.get("rating") == rating.upper()]
        if q:
            needle = q.strip().lower()
            rows = [
                r
                for r in rows
                if needle in r["symbol"].lower() or needle in (r.get("company_name") or "").lower()
            ]
        key = sort if sort in {"symbol", "rating", "sector", "market_cap", "price"} else "symbol"
        reverse = order.lower() == "desc"

        def sort_value(row: dict[str, Any]) -> tuple:
            raw = row.get(key)
            if raw is None:
                return (1, "")
            if isinstance(raw, (int, float)):
                return (0, -raw if reverse else raw)
            return (0, str(raw).lower())

        rows = sorted(rows, key=sort_value, reverse=reverse and key in {"symbol", "rating", "sector"})
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        page = rows[offset : offset + limit]
        return {
            "items": page,
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "sectors": self.sectors(),
            "ratings": list(RATING_ORDER),
        }

    def compare(self, symbol_a: str, symbol_b: str) -> dict[str, Any]:
        """Side-by-side Figma Security Compare contract from coverage records."""
        left = self.latest(symbol_a)
        right = self.latest(symbol_b)
        metrics = (
            {"key": "pe", "label": "P/E", "suffix": "×", "inverse": True},
            {"key": "roe", "label": "ROE", "suffix": "%", "inverse": False},
            {"key": "roce", "label": "ROCE", "suffix": "%", "inverse": False},
            {"key": "revenue_growth", "label": "Rev Growth", "suffix": "%", "inverse": False},
            {"key": "fcf", "label": "FCF", "suffix": "", "inverse": False},
        )
        table: list[dict[str, Any]] = []
        for spec in metrics:
            av = None if left is None else left.get(spec["key"])
            bv = None if right is None else right.get(spec["key"])
            winner = None
            if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
                a_wins = av < bv if spec["inverse"] else av > bv
                winner = (symbol_a if a_wins else symbol_b).upper()
            table.append(
                {
                    "key": spec["key"],
                    "label": spec["label"],
                    "suffix": spec["suffix"],
                    "a": av,
                    "b": bv,
                    "winner": winner,
                }
            )

        shape_a = quality_shape_from_record(left)
        shape_b = quality_shape_from_record(right)

        return {
            "ok": True,
            "available": left is not None and right is not None,
            "a": left,
            "b": right,
            "metrics": table,
            "radar": {"a": radar_from_shape(shape_a), "b": radar_from_shape(shape_b)},
            "quality_shape": {"a": shape_a, "b": shape_b},
            "formula": {
                "Profitability": "No 0–100 profitability score is published by the analysis pipeline.",
                "Growth": "Published growth_quality stage score when present. Revenue growth is not rescaled.",
                "Margins": "No 0–100 margin score is published by the analysis pipeline.",
                "Valuation": "Margin of safety is not converted into a radar score.",
                "Cash Flow": "No 0–100 cash-flow score is published by the analysis pipeline.",
                "Low Debt": "Debt ratios are not converted into a radar score.",
            },
            "message": None
            if left is not None and right is not None
            else "Data unavailable. Both symbols need a recorded server analysis.",
        }

    def stale_after(self, *, hours: int = 24, now: datetime | None = None) -> bool:
        latest = self._store.latest_by_symbol()
        if not latest:
            return True
        current = (now or datetime.now(tz=UTC)).astimezone(UTC)
        newest = max((_parse_ts(r.as_of) for r in latest.values()), default=None)
        return newest is None or current - newest > timedelta(hours=hours)


_SERVICE: CoverageRegistryService | None = None


def get_coverage_registry_service() -> CoverageRegistryService:
    """Process-local service bound to the registry store singleton."""
    global _SERVICE
    store = get_coverage_registry_store()
    if _SERVICE is None or _SERVICE.store is not store:
        _SERVICE = CoverageRegistryService(store)
    return _SERVICE
