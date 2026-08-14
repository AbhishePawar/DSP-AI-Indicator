"""Validate authenticated historical time-series — reject invalid / fabricated."""

from __future__ import annotations

from data_engine.exceptions import InvalidProviderDataError
from data_engine.historical_series.models import (
    BAR_FREQUENCIES,
    SERIES_KINDS,
    AuthenticatedHistoricalBundle,
    AuthenticatedOhlcvBar,
    AuthenticatedPoint,
    AuthenticatedSnapshot,
    HistoricalField,
)

__all__ = ["validate_authenticated_historical_bundle"]

_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)


def _check_field(name: str, field: HistoricalField) -> None:
    if field.available and field.value is None:
        raise InvalidProviderDataError(
            f"historical field '{name}' marked available with null value"
        )
    if not field.available and field.value is not None:
        raise InvalidProviderDataError(
            f"historical field '{name}' has value but marked unavailable"
        )


def _validate_bar(bar: AuthenticatedOhlcvBar, index: int) -> None:
    prefix = f"bars[{index}]"
    if bar.frequency not in BAR_FREQUENCIES:
        raise InvalidProviderDataError(
            f"{prefix}.frequency must be daily|weekly|monthly, got {bar.frequency!r}"
        )
    for name in ("open", "high", "low", "close", "volume"):
        _check_field(f"{prefix}.{name}", getattr(bar, name))
    # OHLC consistency when all present — validation only, no fabrication
    vals = {
        n: getattr(bar, n).value
        for n in ("open", "high", "low", "close")
        if getattr(bar, n).available and getattr(bar, n).value is not None
    }
    if len(vals) == 4:
        if vals["high"] < vals["low"]:
            raise InvalidProviderDataError(f"{prefix} high < low")
        if vals["high"] < vals["open"] or vals["high"] < vals["close"]:
            raise InvalidProviderDataError(f"{prefix} high below open/close")
        if vals["low"] > vals["open"] or vals["low"] > vals["close"]:
            raise InvalidProviderDataError(f"{prefix} low above open/close")


def _validate_point(point: AuthenticatedPoint, index: int) -> None:
    prefix = f"points[{index}]"
    if point.series_kind not in {"market_cap", "volume", "enterprise_value"}:
        raise InvalidProviderDataError(
            f"{prefix}.series_kind invalid: {point.series_kind!r}"
        )
    _check_field(f"{prefix}.value", point.value)


def _validate_snapshot(snap: AuthenticatedSnapshot, index: int) -> None:
    prefix = f"snapshots[{index}]"
    if snap.series_kind not in {"fundamentals", "ratios"}:
        raise InvalidProviderDataError(
            f"{prefix}.series_kind invalid: {snap.series_kind!r}"
        )
    if not snap.fields:
        raise InvalidProviderDataError(f"{prefix} has empty fields")
    for key, field in snap.fields.items():
        _check_field(f"{prefix}.fields.{key}", field)


def validate_authenticated_historical_bundle(
    bundle: AuthenticatedHistoricalBundle,
) -> None:
    """Reject structurally invalid historical bundles. Never invent replacements."""
    if not bundle.identity.symbol or not str(bundle.identity.symbol).strip():
        raise InvalidProviderDataError("historical bundle missing identity.symbol")
    if not bundle.provenance.provider_id.strip():
        raise InvalidProviderDataError("historical bundle missing provider_id")
    if not bundle.provenance.provider_name.strip():
        raise InvalidProviderDataError("historical bundle missing provider_name")
    if bundle.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={bundle.provenance.source_type!r}"
        )
    if bundle.series_kind not in SERIES_KINDS:
        raise InvalidProviderDataError(
            f"series_kind must be one of {sorted(SERIES_KINDS)}, "
            f"got {bundle.series_kind!r}"
        )
    if bundle.frequency is not None and bundle.frequency not in BAR_FREQUENCIES:
        raise InvalidProviderDataError(
            f"frequency must be daily|weekly|monthly or null, got {bundle.frequency!r}"
        )
    if (
        bundle.start_date
        and bundle.end_date
        and bundle.start_date > bundle.end_date
    ):
        raise InvalidProviderDataError("start_date after end_date")
    if not bundle.has_any_observation():
        raise InvalidProviderDataError(
            "authenticated historical bundle must include observations "
            "(use None from adapter when unavailable)"
        )

    if bundle.series_kind == "ohlcv":
        if not bundle.bars:
            raise InvalidProviderDataError("ohlcv series requires bars")
        for i, bar in enumerate(bundle.bars):
            _validate_bar(bar, i)
        # Deterministic chronological order required
        dates = [b.bar_date for b in bundle.bars]
        if dates != sorted(dates):
            raise InvalidProviderDataError("ohlcv bars must be ascending by date")
    elif bundle.series_kind in {"market_cap", "volume", "enterprise_value"}:
        if not bundle.points:
            raise InvalidProviderDataError(f"{bundle.series_kind} requires points")
        for i, point in enumerate(bundle.points):
            _validate_point(point, i)
            if point.series_kind != bundle.series_kind:
                raise InvalidProviderDataError(
                    f"points[{i}].series_kind mismatch bundle"
                )
        dates = [p.point_date for p in bundle.points]
        if dates != sorted(dates):
            raise InvalidProviderDataError("points must be ascending by date")
    else:
        if not bundle.snapshots:
            raise InvalidProviderDataError(f"{bundle.series_kind} requires snapshots")
        for i, snap in enumerate(bundle.snapshots):
            _validate_snapshot(snap, i)
            if snap.series_kind != bundle.series_kind:
                raise InvalidProviderDataError(
                    f"snapshots[{i}].series_kind mismatch bundle"
                )
        dates = [s.as_of for s in bundle.snapshots]
        if dates != sorted(dates):
            raise InvalidProviderDataError("snapshots must be ascending by as_of")
