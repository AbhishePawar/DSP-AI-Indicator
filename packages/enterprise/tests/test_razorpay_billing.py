"""Razorpay BillingPort — orders and HMAC, no live network."""

from __future__ import annotations

import json

import pytest

from enterprise import (
    BILLING_PROVIDER_UNAVAILABLE,
    NullBillingAdapter,
    PaddleBillingAdapter,
    RazorpayBillingAdapter,
    StripeBillingAdapter,
    build_billing_adapter,
)
from enterprise.razorpay_http import (
    RazorpayRequestError,
    checkout_signature,
    webhook_signature,
)


class FakeRazorpayHttp:
    def __init__(self, *, fail_orders: bool = False) -> None:
        self.posts: list[tuple[str, dict[str, object]]] = []
        self.gets: list[str] = []
        self.fail_orders = fail_orders
        self.order_seq = 0
        self.payments: dict[str, dict[str, object]] = {}

    def post_json(self, path: str, body: dict[str, object]) -> dict[str, object]:
        self.posts.append((path, dict(body)))
        if self.fail_orders:
            raise RazorpayRequestError("HTTP 401 for Razorpay /v1/orders")
        if path != "/v1/orders":
            raise AssertionError(path)
        self.order_seq += 1
        return {
            "id": f"order_test{self.order_seq}",
            "amount": body["amount"],
            "currency": body["currency"],
            "status": "created",
        }

    def get_json(self, path: str) -> dict[str, object]:
        self.gets.append(path)
        pid = path.rsplit("/", 1)[-1]
        if pid in self.payments:
            return dict(self.payments[pid])
        return {
            "id": pid,
            "status": "captured",
            "order_id": "order_test1",
            "amount": 49900,
            "currency": "INR",
        }


def _configured(http: FakeRazorpayHttp | None = None) -> RazorpayBillingAdapter:
    return RazorpayBillingAdapter(
        key_id="rzp_test_key",
        key_secret="rzp_test_secret",
        webhook_secret="whsec_test",
        http_client=http or FakeRazorpayHttp(),
    )


def test_missing_credentials_remain_unavailable() -> None:
    adapter = RazorpayBillingAdapter(key_id="", key_secret="", webhook_secret="")
    assert adapter.is_available() is False
    created = adapter.create_checkout_session("org_x", plan="starter", amount_paise=49900)
    assert created["ok"] is False
    assert created["message"] == BILLING_PROVIDER_UNAVAILABLE


def test_partial_credentials_remain_unavailable() -> None:
    adapter = RazorpayBillingAdapter(
        key_id="rzp_test_key", key_secret="rzp_test_secret", webhook_secret=""
    )
    assert adapter.is_available() is False
    assert adapter.create_checkout_session("org_x", plan="starter")["ok"] is False


def test_stripe_paddle_null_remain_unavailable() -> None:
    for adapter in (
        NullBillingAdapter(),
        StripeBillingAdapter(api_key="sk_test"),
        PaddleBillingAdapter(api_key="pdl"),
        build_billing_adapter("null"),
        build_billing_adapter("stripe"),
        build_billing_adapter("paddle"),
    ):
        assert adapter.is_available() is False


def test_order_creation_posts_server_amount() -> None:
    http = FakeRazorpayHttp()
    adapter = _configured(http)
    assert adapter.is_available() is True
    created = adapter.create_checkout_session(
        "org_1",
        plan="starter",
        amount_paise=49900,
        currency="INR",
        receipt="dsp_receipt_1",
        notes={"org_id": "org_1", "plan_id": "starter"},
    )
    assert created["ok"] is True
    assert created["order_id"] == "order_test1"
    assert created["key_id"] == "rzp_test_key"
    assert "key_secret" not in created
    assert created["amount"] == 49900
    assert created["currency"] == "INR"
    path, body = http.posts[0]
    assert path == "/v1/orders"
    assert body["amount"] == 49900
    assert body["currency"] == "INR"
    assert body["notes"]["plan_id"] == "starter"
    dumped = json.dumps(created)
    assert "rzp_test_secret" not in dumped
    assert "whsec_test" not in dumped
    assert "key_secret" not in created
    assert "webhook_secret" not in created


def test_order_creation_without_amount_is_unable_to_calculate() -> None:
    adapter = _configured()
    created = adapter.create_checkout_session("org_1", plan="starter")
    assert created["ok"] is False
    assert created["message"] == "Unable to calculate."


def test_order_http_failure_is_unavailable() -> None:
    adapter = _configured(FakeRazorpayHttp(fail_orders=True))
    created = adapter.create_checkout_session(
        "org_1", plan="starter", amount_paise=49900, currency="INR"
    )
    assert created["ok"] is False
    assert created["message"] == BILLING_PROVIDER_UNAVAILABLE


def test_checkout_signature_valid_and_invalid() -> None:
    adapter = _configured()
    expected = checkout_signature("order_1", "pay_1", "rzp_test_secret")
    ok = adapter.verify_checkout_signature(
        order_id="order_1", payment_id="pay_1", signature=expected
    )
    assert ok["verified"] is True
    bad = adapter.verify_checkout_signature(
        order_id="order_1", payment_id="pay_1", signature="deadbeef"
    )
    assert bad["verified"] is False
    assert bad["ok"] is False


def test_webhook_signature_valid_and_invalid() -> None:
    adapter = _configured()
    payload = b'{"event":"payment.captured"}'
    expected = webhook_signature(payload, "whsec_test")
    ok = adapter.verify_webhook(payload, signature=expected)
    assert ok["verified"] is True
    bad = adapter.verify_webhook(payload, signature="nope")
    assert bad["verified"] is False
    missing = adapter.verify_webhook(payload, signature=None)
    assert missing["verified"] is False


def test_configured_adapter_is_not_available_via_factory_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DSP_RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("DSP_RAZORPAY_KEY_SECRET", raising=False)
    monkeypatch.delenv("DSP_RAZORPAY_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("DSP_BILLING_PROVIDER", "razorpay")
    adapter = build_billing_adapter("razorpay")
    assert adapter.is_available() is False
