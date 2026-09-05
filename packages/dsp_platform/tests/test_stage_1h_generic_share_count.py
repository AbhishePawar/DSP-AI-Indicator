"""Stage 1H — generic listed-equity share-count contracts.

The second fixture is SYNTHETIC — NOT PRODUCTION DATA. It must never be
copied into the production promoted_share_counts package directory.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from dsp_platform.current_outstanding_protocol.currentness import (
    SHARE_CHANGING_ACTION_TYPES,
    CorporateActionCurrentnessEvidence,
    ShareChangingCorporateAction,
    evaluate_option_b_currentness,
)
from dsp_platform.promoted_share_count import (
    DEFAULT_PROMOTED_SHARE_COUNT_DIR,
    SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
    SHARES_OUTSTANDING_IDENTITY_MISMATCH,
    SHARES_OUTSTANDING_STALE,
    DurablePromotedShareCountAdapter,
    ShareCountResolutionError,
    sign_promoted_snapshot,
)

_HORIZON = datetime(2026, 9, 5, 14, 6, tzinfo=UTC)
_TCS_JSON = DEFAULT_PROMOTED_SHARE_COUNT_DIR / "INE467B01029_XNSE.json"

# SYNTHETIC — NOT PRODUCTION DATA
_SYNTHETIC_ISIN = "INE999Z01019"
_SYNTHETIC_SYMBOL = "SYNTH"
_SYNTHETIC_SHARES = "1000000001"


def _tcs_instrument(*, exchange: str = "NSE", isin: str | None = "INE467B01029") -> Instrument:
    return Instrument(
        symbol="TCS",
        asset_class=AssetClass.EQUITY,
        currency="INR",
        exchange=exchange,
        isin=isin,
        name="Tata Consultancy Services",
    )


def _synth_instrument(*, exchange: str = "NSE") -> Instrument:
    return Instrument(
        symbol=_SYNTHETIC_SYMBOL,
        asset_class=AssetClass.EQUITY,
        currency="INR",
        exchange=exchange,
        isin=_SYNTHETIC_ISIN,
        name="Synthetic Test Equity — NOT PRODUCTION DATA",
    )


def _synthetic_payload() -> dict:
    return {
        "schema_version": "dsp.promoted_share_count.v1",
        "identity": {
            "symbol": _SYNTHETIC_SYMBOL,
            "exchange": "NSE",
            "mic": "XNSE",
            "isin": _SYNTHETIC_ISIN,
            "company_name": "SYNTHETIC — NOT PRODUCTION DATA",
        },
        "shares_outstanding": _SYNTHETIC_SHARES,
        "basis": "current_outstanding",
        "unit": "shares",
        "as_of": "2026-06-30",
        "effective_date": "2026-06-30",
        "complete_through": "2026-09-05",
        "source_tier": "TIER_1_PRIMARY",
        "corporate_action_adjusted": True,
        "source": {
            "provider_id": "promoted_t1_share_count",
            "provider_name": "Synthetic architecture fixture",
            "source_type": "primary_filing",
            "source_url": "https://fixtures.dsp.test/synthetic/outstanding",
            "evidence_reference": (
                "SYNTHETIC — NOT PRODUCTION DATA. As of June 30, 2026, "
                "outstanding shares were 1,000,000,001."
            ),
        },
        "corporate_action_events": [
            {
                "action_type": "dividend",
                "effective_date": "2026-07-01",
                "changes_outstanding_shares": False,
                "description": "Synthetic non-dilutive dividend",
            }
        ],
    }


def _write_signed(directory: Path, name: str, payload: dict) -> None:
    (directory / name).write_text(
        json.dumps(sign_promoted_snapshot(payload)), encoding="utf-8"
    )


def _ca_evidence(
    *,
    as_of: date = date(2026, 6, 30),
    complete_through: date = date(2026, 9, 5),
    events: tuple[ShareChangingCorporateAction, ...] = (),
) -> CorporateActionCurrentnessEvidence:
    return CorporateActionCurrentnessEvidence(
        events=events,
        complete_through=complete_through,
        share_count_as_of=as_of,
        source_tier="TIER_1_PRIMARY",
        source_url="https://fixtures.dsp.test/ca",
        evidence_reference="Synthetic corporate-action completeness.",
    )


class TestCanonicalIdentity:
    def test_same_isin_nse_and_bse_are_equivalent(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _HORIZON)
        nse = adapter.get_share_count(_tcs_instrument(exchange="NSE"))
        bse = adapter.get_share_count(_tcs_instrument(exchange="BSE"))
        assert nse is not None and bse is not None
        assert nse.shares_value() == bse.shares_value()
        assert nse.isin == "INE467B01029"

    def test_correct_isin_wrong_mic_is_rejected(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _HORIZON)
        with pytest.raises(
            ShareCountResolutionError, match=SHARES_OUTSTANDING_IDENTITY_MISMATCH
        ):
            adapter.get_share_count(_tcs_instrument(exchange="NYSE"))

    def test_wrong_isin_does_not_resolve(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _HORIZON)
        assert adapter.get_share_count(_tcs_instrument(isin=_SYNTHETIC_ISIN)) is None

    def test_ticker_collision_does_not_steal_another_isin(self, tmp_path: Path) -> None:
        tcs = json.loads(_TCS_JSON.read_text(encoding="utf-8"))
        tcs.pop("integrity", None)
        _write_signed(tmp_path, "tcs.json", tcs)
        synth = _synthetic_payload()
        synth["identity"]["symbol"] = "TCS"
        _write_signed(tmp_path, "synth.json", synth)
        adapter = DurablePromotedShareCountAdapter(
            directory=tmp_path, now=lambda: _HORIZON
        )
        tcs_snap = adapter.get_share_count(_tcs_instrument())
        synth_snap = adapter.get_share_count(
            Instrument(
                symbol="TCS",
                asset_class=AssetClass.EQUITY,
                currency="INR",
                exchange="NSE",
                isin=_SYNTHETIC_ISIN,
            )
        )
        assert tcs_snap is not None
        assert synth_snap is not None
        assert tcs_snap.shares_value() != synth_snap.shares_value()
        assert tcs_snap.isin != synth_snap.isin


class TestShareSemantics:
    @pytest.mark.parametrize(
        "forbidden_key",
        (
            "float",
            "weighted_average_shares",
            "market_cap_implied_shares",
            "issued_shares",
            "authorized_shares",
            "treasury_shares",
        ),
    )
    def test_forbidden_metrics_are_rejected(
        self, tmp_path: Path, forbidden_key: str
    ) -> None:
        payload = _synthetic_payload()
        payload[forbidden_key] = _SYNTHETIC_SHARES
        _write_signed(tmp_path, "bad.json", payload)
        adapter = DurablePromotedShareCountAdapter(
            directory=tmp_path, now=lambda: _HORIZON
        )
        with pytest.raises(ShareCountResolutionError):
            adapter.get_share_count(_synth_instrument())

    def test_malformed_count_is_rejected(self, tmp_path: Path) -> None:
        payload = _synthetic_payload()
        payload["shares_outstanding"] = "not-a-number"
        _write_signed(tmp_path, "bad.json", payload)
        adapter = DurablePromotedShareCountAdapter(
            directory=tmp_path, now=lambda: _HORIZON
        )
        with pytest.raises(ShareCountResolutionError):
            adapter.get_share_count(_synth_instrument())


class TestOptionBTemporalValidity:
    def test_current_snapshot_is_proven(self) -> None:
        verdict = evaluate_option_b_currentness(
            share_count_as_of=date(2026, 6, 30),
            retrieved_at=_HORIZON,
            evidence=_ca_evidence(),
        )
        assert verdict.proven is True

    def test_stale_complete_through_is_unproven(self) -> None:
        verdict = evaluate_option_b_currentness(
            share_count_as_of=date(2026, 6, 30),
            retrieved_at=_HORIZON,
            evidence=_ca_evidence(complete_through=date(2026, 8, 1)),
        )
        assert verdict.proven is False
        assert "does not reach retrieved_at" in verdict.reason

    def test_future_as_of_is_unproven(self) -> None:
        future = date(2026, 12, 31)
        verdict = evaluate_option_b_currentness(
            share_count_as_of=future,
            retrieved_at=_HORIZON,
            evidence=_ca_evidence(as_of=future, complete_through=date(2027, 1, 31)),
        )
        assert verdict.proven is False
        assert "future" in verdict.reason

    def test_complete_through_before_as_of_is_unproven(self) -> None:
        verdict = evaluate_option_b_currentness(
            share_count_as_of=date(2026, 6, 30),
            retrieved_at=_HORIZON,
            evidence=_ca_evidence(complete_through=date(2026, 1, 1)),
        )
        assert verdict.proven is False

    def test_stale_promoted_snapshot_fails_closed(self, tmp_path: Path) -> None:
        payload = _synthetic_payload()
        payload["complete_through"] = "2026-08-01"
        _write_signed(tmp_path, "stale.json", payload)
        adapter = DurablePromotedShareCountAdapter(
            directory=tmp_path, now=lambda: _HORIZON
        )
        with pytest.raises(ShareCountResolutionError, match=SHARES_OUTSTANDING_STALE):
            adapter.get_share_count(_synth_instrument())

    def test_missing_as_of_is_rejected(self, tmp_path: Path) -> None:
        payload = _synthetic_payload()
        payload["as_of"] = ""
        _write_signed(tmp_path, "missing.json", payload)
        adapter = DurablePromotedShareCountAdapter(
            directory=tmp_path, now=lambda: _HORIZON
        )
        with pytest.raises(
            ShareCountResolutionError, match=SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN
        ):
            adapter.get_share_count(_synth_instrument())


class TestCorporateActionInvalidation:
    @pytest.mark.parametrize(
        "action_type",
        (
            "stock_split",
            "reverse_split",
            "bonus",
            "rights",
            "new_issue",
            "buyback",
            "cancellation",
            "merger",
            "demerger",
            "conversion",
        ),
    )
    def test_later_share_changing_event_is_unproven(self, action_type: str) -> None:
        assert action_type.replace("-", "_") in SHARE_CHANGING_ACTION_TYPES or (
            action_type in SHARE_CHANGING_ACTION_TYPES
        )
        verdict = evaluate_option_b_currentness(
            share_count_as_of=date(2026, 6, 30),
            retrieved_at=_HORIZON,
            evidence=_ca_evidence(
                events=(
                    ShareChangingCorporateAction(
                        action_type=action_type,
                        effective_date=date(2026, 7, 15),
                        changes_outstanding_shares=True,
                    ),
                )
            ),
        )
        assert verdict.proven is False
        assert "later share-changing" in verdict.reason

    def test_reverse_split_on_or_before_as_of_does_not_invalidate(self) -> None:
        verdict = evaluate_option_b_currentness(
            share_count_as_of=date(2026, 6, 30),
            retrieved_at=_HORIZON,
            evidence=_ca_evidence(
                events=(
                    ShareChangingCorporateAction(
                        action_type="reverse_split",
                        effective_date=date(2026, 6, 30),
                        changes_outstanding_shares=True,
                    ),
                )
            ),
        )
        assert verdict.proven is True


class TestIntegrityAndConflict:
    def test_tampered_hash_fails_closed(self, tmp_path: Path) -> None:
        payload = sign_promoted_snapshot(_synthetic_payload())
        payload["shares_outstanding"] = "9"
        (tmp_path / "tampered.json").write_text(json.dumps(payload), encoding="utf-8")
        adapter = DurablePromotedShareCountAdapter(
            directory=tmp_path, now=lambda: _HORIZON
        )
        with pytest.raises(ShareCountResolutionError):
            adapter.get_share_count(_synth_instrument())

    def test_conflicting_counts_fail_closed(self, tmp_path: Path) -> None:
        first = _synthetic_payload()
        second = _synthetic_payload()
        second["shares_outstanding"] = "2"
        _write_signed(tmp_path, "a.json", first)
        _write_signed(tmp_path, "b.json", second)
        adapter = DurablePromotedShareCountAdapter(
            directory=tmp_path, now=lambda: _HORIZON
        )
        with pytest.raises(ShareCountResolutionError):
            adapter.get_share_count(_synth_instrument())


class TestGenericity:
    def test_synthetic_fixture_is_not_in_production_package(self) -> None:
        names = {path.name for path in DEFAULT_PROMOTED_SHARE_COUNT_DIR.glob("*.json")}
        assert "INE467B01029_XNSE.json" in names
        assert _SYNTHETIC_ISIN not in "".join(names)
        for path in DEFAULT_PROMOTED_SHARE_COUNT_DIR.glob("*.json"):
            text = path.read_text(encoding="utf-8")
            assert "SYNTHETIC — NOT PRODUCTION DATA" not in text
            assert _SYNTHETIC_SHARES not in text

    def test_tcs_and_synthetic_resolve_independently(self, tmp_path: Path) -> None:
        tcs = json.loads(_TCS_JSON.read_text(encoding="utf-8"))
        tcs.pop("integrity", None)
        _write_signed(tmp_path, "tcs.json", tcs)
        _write_signed(tmp_path, "synth.json", _synthetic_payload())
        adapter = DurablePromotedShareCountAdapter(
            directory=tmp_path, now=lambda: _HORIZON
        )
        tcs_snap = adapter.get_share_count(_tcs_instrument())
        synth_snap = adapter.get_share_count(_synth_instrument())
        assert tcs_snap is not None and synth_snap is not None
        assert Decimal(str(int(tcs_snap.shares_value() or 0))) != Decimal(
            _SYNTHETIC_SHARES
        )
        assert synth_snap.shares_value() == pytest.approx(float(_SYNTHETIC_SHARES))
        assert tcs_snap.isin != synth_snap.isin

    def test_unknown_equity_returns_none(self, tmp_path: Path) -> None:
        _write_signed(tmp_path, "synth.json", _synthetic_payload())
        adapter = DurablePromotedShareCountAdapter(
            directory=tmp_path, now=lambda: _HORIZON
        )
        unknown = Instrument(
            symbol="INFY",
            asset_class=AssetClass.EQUITY,
            currency="INR",
            exchange="NSE",
            isin="INE009A01021",
        )
        assert adapter.get_share_count(unknown) is None
