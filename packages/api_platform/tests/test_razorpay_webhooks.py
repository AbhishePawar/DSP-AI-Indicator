"""Razorpay webhook/checkout HTTP routes — no live Razorpay network."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.saas_platform import reset_saas_overlay_store_for_tests
from enterprise import (
    EnterpriseService,
    RazorpayBillingAdapter,
    reset_enterprise_service_for_tests,
)
from enterprise.razorpay_http import webhook_signature


SECRET = "rzp_test_secret"
WEBHOOK_SECRET = "whsec_test"


class FakeRazorpayHttp:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, object]]] = []
        self.order_seq = 0

    def post_json(self, path: str, body: dict[str, object]) -> dict[str, object]:
        self.posts.append((path, dict(body)))
        self.order_seq += 1
        return {
            "id": f"order_api{self.order_seq}",
            "amount": body["amount"],
            "currency": body["currency"],
            "status": "created",
        }

    def get_json(self, path: str) -> dict[str, object]:
        pid = path.rsplit("/", 1)[-1]
        return {
            "id": pid,
            "status": "captured",
            "order_id": "order_api1",
            "amount": 49900,
            "currency": "INR",
        }


@pytest.fixture()
def razorpay_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DSP_RAZORPAY_PLAN_PRICES_PAISE", "starter=49900")
    monkeypatch.setenv("DSP_RAZORPAY_CURRENCY", "INR")
    billing = RazorpayBillingAdapter(
        key_id="rzp_test_key",
        key_secret=SECRET,
        webhook_secret=WEBHOOK_SECRET,
        http_client=FakeRazorpayHttp(),
    )
    reset_enterprise_service_for_tests(EnterpriseService(billing=billing))
    reset_saas_overlay_store_for_tests()
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    return TestClient(create_app(platform=platform))


def _authed_org(client: TestClient) -> tuple[dict[str, str], str]:
    register_user(client, user_id="rzp-owner", username="rzpowner")
    headers = bearer_headers(client, username="rzpowner")
    created = client.post(
        "/api/v1/saas/organization",
        headers=headers,
        json={"name": "Rzp Org", "slug": f"rzp-org-{uuid4().hex[:8]}"},
    )
    assert created.status_code == 200, created.text
    org_id = created.json()["result"]["organization"]["org_id"]
    return headers, org_id


def test_unauthorized_checkout_rejected(razorpay_client: TestClient) -> None:
    response = razorpay_client.post(
        "/api/v1/saas/checkout",
        json={"org_id": "org_x", "plan_id": "starter"},
    )
    assert response.status_code == 401


def test_checkout_order_ignores_client_amount(razorpay_client: TestClient) -> None:
    headers, org_id = _authed_org(razorpay_client)
    response = razorpay_client.post(
        "/api/v1/saas/checkout",
        headers=headers,
        json={
            "org_id": org_id,
            "plan_id": "starter",
            "amount": 1,
            "currency": "USD",
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["ok"] is True
    assert result["order_id"] == "order_api1"
    assert result["amount"] == 49900
    assert result["currency"] == "INR"
    assert "key_secret" not in result
    assert result["key_id"] == "rzp_test_key"


def test_webhook_valid_signature_entitles(razorpay_client: TestClient) -> None:
    headers, org_id = _authed_org(razorpay_client)
    checkout = razorpay_client.post(
        "/api/v1/saas/checkout",
        headers=headers,
        json={"org_id": org_id, "plan_id": "starter"},
    )
    order_id = checkout.json()["result"]["order_id"]
    payload = {
        "id": "evt_api_1",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_api_1",
                    "order_id": order_id,
                    "amount": 49900,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }
    raw = json.dumps(payload).encode()
    response = razorpay_client.post(
        "/api/v1/saas/webhooks/razorpay",
        content=raw,
        headers={"X-Razorpay-Signature": webhook_signature(raw, WEBHOOK_SECRET)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verified"] is True
    assert body["entitled"] is True
    license_row = razorpay_client.get(
        f"/api/v1/saas/organization/{org_id}/license",
        headers=headers,
    )
    assert license_row.status_code == 200
    assert license_row.json()["result"]["license"]["tier"] == "research"


def test_webhook_invalid_signature_rejected(razorpay_client: TestClient) -> None:
    raw = b'{"id":"evt_bad","event":"payment.captured"}'
    response = razorpay_client.post(
        "/api/v1/saas/webhooks/razorpay",
        content=raw,
        headers={"X-Razorpay-Signature": "invalid"},
    )
    assert response.status_code == 400
    assert response.json()["verified"] is False


def test_webhook_duplicate_delivery(razorpay_client: TestClient) -> None:
    headers, org_id = _authed_org(razorpay_client)
    checkout = razorpay_client.post(
        "/api/v1/saas/checkout",
        headers=headers,
        json={"org_id": org_id, "plan_id": "starter"},
    )
    order_id = checkout.json()["result"]["order_id"]
    payload = {
        "id": "evt_dup_api",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_dup_api",
                    "order_id": order_id,
                    "amount": 49900,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }
    raw = json.dumps(payload).encode()
    headers_wh = {"X-Razorpay-Signature": webhook_signature(raw, WEBHOOK_SECRET)}
    first = razorpay_client.post(
        "/api/v1/saas/webhooks/razorpay", content=raw, headers=headers_wh
    )
    second = razorpay_client.post(
        "/api/v1/saas/webhooks/razorpay", content=raw, headers=headers_wh
    )
    assert first.status_code == 200
    assert first.json()["entitled"] is True
    assert second.status_code == 200
    assert second.json()["duplicate"] is True


def test_webhook_missing_signature_rejected(razorpay_client: TestClient) -> None:
    raw = b'{"id":"evt_nosig","event":"payment.captured"}'
    response = razorpay_client.post("/api/v1/saas/webhooks/razorpay", content=raw)
    assert response.status_code == 400
    assert response.json()["verified"] is False


def test_webhook_altered_payload_rejected(razorpay_client: TestClient) -> None:
    original = b'{"id":"evt_orig","event":"payment.captured"}'
    altered = b'{"id":"evt_orig","event":"payment.captured","payload":{"x":1}}'
    response = razorpay_client.post(
        "/api/v1/saas/webhooks/razorpay",
        content=altered,
        headers={"X-Razorpay-Signature": webhook_signature(original, WEBHOOK_SECRET)},
    )
    assert response.status_code == 400
    assert response.json()["verified"] is False


def test_webhook_payment_failed(razorpay_client: TestClient) -> None:
    headers, org_id = _authed_org(razorpay_client)
    checkout = razorpay_client.post(
        "/api/v1/saas/checkout",
        headers=headers,
        json={"org_id": org_id, "plan_id": "starter"},
    )
    order_id = checkout.json()["result"]["order_id"]
    payload = {
        "id": "evt_fail_api",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_fail_api",
                    "order_id": order_id,
                    "amount": 49900,
                    "currency": "INR",
                    "status": "failed",
                }
            }
        },
    }
    raw = json.dumps(payload).encode()
    response = razorpay_client.post(
        "/api/v1/saas/webhooks/razorpay",
        content=raw,
        headers={"X-Razorpay-Signature": webhook_signature(raw, WEBHOOK_SECRET)},
    )
    assert response.status_code == 200
    assert response.json().get("entitled") is False
    license_row = razorpay_client.get(
        f"/api/v1/saas/organization/{org_id}/license",
        headers=headers,
    )
    meta = (license_row.json()["result"].get("license") or {}).get("metadata") or {}
    assert meta.get("source") != "razorpay"
