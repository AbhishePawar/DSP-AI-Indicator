"""SaaS Razorpay checkout orchestration — no live charges."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from dsp_platform.saas_platform import (
    handle_razorpay_webhook,
    reset_saas_overlay_store_for_tests,
    resolve_plan_checkout_price,
    run_saas_platform,
)
from enterprise import EnterpriseService, RazorpayBillingAdapter, reset_enterprise_service_for_tests
from enterprise.razorpay_http import RazorpayRequestError, checkout_signature, webhook_signature


class FakeRazorpayHttp:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, object]]] = []
        self.payments: dict[str, dict[str, object]] = {}
        self.order_seq = 0

    def post_json(self, path: str, body: dict[str, object]) -> dict[str, object]:
        self.posts.append((path, dict(body)))
        if path != "/v1/orders":
            raise RazorpayRequestError(path)
        self.order_seq += 1
        return {
            "id": f"order_test{self.order_seq}",
            "amount": body["amount"],
            "currency": body["currency"],
            "status": "created",
        }

    def get_json(self, path: str) -> dict[str, object]:
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


SECRET = "rzp_test_secret"
WEBHOOK_SECRET = "whsec_test"


@pytest.fixture()
def prices(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_RAZORPAY_PLAN_PRICES_PAISE", "starter=49900,professional=149900")
    monkeypatch.setenv("DSP_RAZORPAY_CURRENCY", "INR")


@pytest.fixture()
def http() -> FakeRazorpayHttp:
    return FakeRazorpayHttp()


@pytest.fixture()
def stack(prices: None, http: FakeRazorpayHttp) -> tuple[EnterpriseService, FakeRazorpayHttp]:
    billing = RazorpayBillingAdapter(
        key_id="rzp_test_key",
        key_secret=SECRET,
        webhook_secret=WEBHOOK_SECRET,
        http_client=http,
    )
    svc = EnterpriseService(billing=billing)
    reset_enterprise_service_for_tests(svc)
    reset_saas_overlay_store_for_tests()
    return svc, http


def _org(owner: str = "owner-rzp") -> str:
    created = run_saas_platform(
        "create_organization",
        payload={
            "name": "Pay Org",
            "slug": f"pay-org-{uuid4().hex[:8]}",
            "owner_user_id": owner,
        },
    )
    return str(created["result"]["organization"]["org_id"])


def test_resolve_price_ignores_unlisted_and_custom(prices: None) -> None:
    starter = resolve_plan_checkout_price("starter")
    assert starter == {"plan_id": "starter", "amount_paise": 49900, "currency": "INR"}
    assert resolve_plan_checkout_price("custom") is None
    assert resolve_plan_checkout_price("enterprise") is None


def test_checkout_creates_order_and_ignores_client_amount(stack: tuple) -> None:
    _svc, http = stack
    org_id = _org()
    checkout = run_saas_platform(
        "checkout",
        payload={
            "org_id": org_id,
            "plan_id": "starter",
            "actor_user_id": "owner-rzp",
            "amount": 1,
            "amount_paise": 1,
            "currency": "USD",
        },
    )
    assert checkout["ok"] is True
    result = checkout["result"]
    assert result["ok"] is True
    assert result["order_id"] == "order_test1"
    assert result["amount"] == 49900
    assert result["currency"] == "INR"
    assert result["key_id"] == "rzp_test_key"
    assert "key_secret" not in result
    assert http.posts[0][1]["amount"] == 49900
    assert http.posts[0][1]["currency"] == "INR"


def test_checkout_unpriced_plan_unable_to_calculate(stack: tuple) -> None:
    org_id = _org()
    checkout = run_saas_platform(
        "checkout",
        payload={
            "org_id": org_id,
            "plan_id": "enterprise",
            "actor_user_id": "owner-rzp",
        },
    )
    result = checkout["result"]
    assert result["ok"] is False
    assert result["message"] == "Unable to calculate."


def test_payment_captured_grants_existing_license(stack: tuple) -> None:
    svc, _http = stack
    org_id = _org()
    run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    body = json.dumps(
        {
            "id": "evt_captured_1",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_1",
                        "order_id": "order_test1",
                        "amount": 49900,
                        "currency": "INR",
                        "status": "captured",
                    }
                }
            },
        }
    ).encode()
    outcome = handle_razorpay_webhook(
        body, webhook_signature(body, WEBHOOK_SECRET), enterprise=svc
    )
    assert outcome["verified"] is True
    assert outcome["entitled"] is True
    assert outcome["duplicate"] is False
    license_info = svc.get_license(org_id, actor_user_id="owner-rzp")
    assert license_info["available"] is True
    assert license_info["license"]["tier"] == "research"
    assert license_info["license"]["metadata"]["payment_id"] == "pay_1"


def test_duplicate_webhook_does_not_double_entitle(stack: tuple) -> None:
    svc, _http = stack
    org_id = _org()
    run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    payload = {
        "id": "evt_dup",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_dup",
                    "order_id": "order_test1",
                    "amount": 49900,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }
    body = json.dumps(payload).encode()
    sig = webhook_signature(body, WEBHOOK_SECRET)
    first = handle_razorpay_webhook(body, sig, enterprise=svc)
    second = handle_razorpay_webhook(body, sig, enterprise=svc)
    assert first["entitled"] is True
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["entitled"] is False
    licenses = [row for row in svc.store.licenses.values() if row.org_id == org_id]
    assert len(licenses) == 1


def test_order_paid_entitles(stack: tuple) -> None:
    svc, _http = stack
    org_id = _org()
    run_saas_platform(
        "checkout",
        payload={
            "org_id": org_id,
            "plan_id": "professional",
            "actor_user_id": "owner-rzp",
        },
    )
    body = json.dumps(
        {
            "id": "evt_paid",
            "event": "order.paid",
            "payload": {
                "order": {
                    "entity": {
                        "id": "order_test1",
                        "amount": 149900,
                        "currency": "INR",
                        "status": "paid",
                    }
                },
                "payment": {
                    "entity": {
                        "id": "pay_paid",
                        "order_id": "order_test1",
                        "amount": 149900,
                        "currency": "INR",
                        "status": "captured",
                    }
                },
            },
        }
    ).encode()
    outcome = handle_razorpay_webhook(
        body, webhook_signature(body, WEBHOOK_SECRET), enterprise=svc
    )
    assert outcome["entitled"] is True
    assert svc.get_license(org_id, actor_user_id="owner-rzp")["license"]["tier"] == "professional"


def test_payment_authorized_does_not_entitle(stack: tuple) -> None:
    svc, _http = stack
    org_id = _org()
    run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    body = json.dumps(
        {
            "id": "evt_auth",
            "event": "payment.authorized",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_auth",
                        "order_id": "order_test1",
                        "amount": 49900,
                        "currency": "INR",
                        "status": "authorized",
                    }
                }
            },
        }
    ).encode()
    outcome = handle_razorpay_webhook(
        body, webhook_signature(body, WEBHOOK_SECRET), enterprise=svc
    )
    assert outcome["verified"] is True
    assert outcome.get("entitled") is False
    license_info = svc.get_license(org_id, actor_user_id="owner-rzp")
    # Org create assigns a trial starter license — Razorpay must not mark it paid.
    assert (license_info.get("license") or {}).get("metadata", {}).get("source") != "razorpay"


def test_payment_failed_does_not_revoke_or_grant(stack: tuple) -> None:
    svc, _http = stack
    org_id = _org()
    run_saas_platform(
        "assign_license",
        payload={
            "org_id": org_id,
            "plan_id": "starter",
            "actor_user_id": "owner-rzp",
            "seats": 1,
        },
    )
    run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    body = json.dumps(
        {
            "id": "evt_fail",
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fail",
                        "order_id": "order_test1",
                        "amount": 49900,
                        "currency": "INR",
                        "status": "failed",
                    }
                }
            },
        }
    ).encode()
    outcome = handle_razorpay_webhook(
        body, webhook_signature(body, WEBHOOK_SECRET), enterprise=svc
    )
    assert outcome.get("status") == "failed"
    assert outcome.get("entitled") is False
    existing = svc.get_license(org_id, actor_user_id="owner-rzp")
    assert existing["available"] is True
    assert existing["license"]["metadata"].get("payment_id") is None


def test_invalid_webhook_signature_rejected(stack: tuple) -> None:
    svc, _http = stack
    body = b'{"id":"evt_bad","event":"payment.captured"}'
    outcome = handle_razorpay_webhook(body, "not-a-signature", enterprise=svc)
    assert outcome["verified"] is False
    assert outcome["ok"] is False


def test_checkout_verify_captured_entitles(stack: tuple) -> None:
    svc, http = stack
    org_id = _org()
    run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    sig = checkout_signature("order_test1", "pay_verify", SECRET)
    http.payments["pay_verify"] = {
        "id": "pay_verify",
        "status": "captured",
        "order_id": "order_test1",
        "amount": 49900,
        "currency": "INR",
    }
    verified = run_saas_platform(
        "checkout_verify",
        payload={
            "org_id": org_id,
            "actor_user_id": "owner-rzp",
            "razorpay_order_id": "order_test1",
            "razorpay_payment_id": "pay_verify",
            "razorpay_signature": sig,
        },
    )
    result = verified["result"]
    assert result["verified"] is True
    assert result["entitled"] is True
    assert svc.get_license(org_id, actor_user_id="owner-rzp")["available"] is True


def test_checkout_verify_rejects_bad_signature(stack: tuple) -> None:
    org_id = _org()
    run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    verified = run_saas_platform(
        "checkout_verify",
        payload={
            "org_id": org_id,
            "actor_user_id": "owner-rzp",
            "razorpay_order_id": "order_test1",
            "razorpay_payment_id": "pay_x",
            "razorpay_signature": "00" * 32,
        },
    )
    assert verified["result"]["verified"] is False
    assert verified["result"].get("entitled") is not True


def _verify(
    *,
    org_id: str,
    actor: str,
    order_id: str,
    payment_id: str,
    secret: str = SECRET,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "org_id": org_id,
        "actor_user_id": actor,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": checkout_signature(order_id, payment_id, secret),
    }
    if extra:
        payload.update(extra)
    return run_saas_platform("checkout_verify", payload=payload)


def test_checkout_verify_rejects_wrong_order_id(stack: tuple) -> None:
    svc, http = stack
    org_id = _org()
    run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    http.payments["pay_wrong_order"] = {
        "id": "pay_wrong_order",
        "status": "captured",
        "order_id": "order_other",
        "amount": 49900,
        "currency": "INR",
    }
    verified = _verify(
        org_id=org_id,
        actor="owner-rzp",
        order_id="order_test1",
        payment_id="pay_wrong_order",
    )
    assert verified["result"]["verified"] is True
    assert verified["result"]["entitled"] is False
    assert verified["result"]["detail"] == "order mismatch"
    assert (svc.get_license(org_id, actor_user_id="owner-rzp").get("license") or {}).get(
        "metadata", {}
    ).get("source") != "razorpay"


def test_checkout_verify_rejects_wrong_amount(stack: tuple) -> None:
    svc, http = stack
    org_id = _org()
    run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    http.payments["pay_wrong_amt"] = {
        "id": "pay_wrong_amt",
        "status": "captured",
        "order_id": "order_test1",
        "amount": 1,
        "currency": "INR",
    }
    verified = _verify(
        org_id=org_id,
        actor="owner-rzp",
        order_id="order_test1",
        payment_id="pay_wrong_amt",
    )
    assert verified["result"]["entitled"] is False
    assert verified["result"]["detail"] == "Payment amount mismatch."
    assert (svc.get_license(org_id, actor_user_id="owner-rzp").get("license") or {}).get(
        "metadata", {}
    ).get("source") != "razorpay"


def test_checkout_verify_rejects_wrong_currency(stack: tuple) -> None:
    _svc, http = stack
    org_id = _org()
    run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    http.payments["pay_wrong_ccy"] = {
        "id": "pay_wrong_ccy",
        "status": "captured",
        "order_id": "order_test1",
        "amount": 49900,
        "currency": "USD",
    }
    verified = _verify(
        org_id=org_id,
        actor="owner-rzp",
        order_id="order_test1",
        payment_id="pay_wrong_ccy",
    )
    assert verified["result"]["entitled"] is False
    assert verified["result"]["detail"] == "Payment amount mismatch."


def test_checkout_verify_rejects_other_organization_order(stack: tuple) -> None:
    svc, http = stack
    org_a = _org("owner-rzp")
    org_b = _org("owner-b")
    run_saas_platform(
        "checkout",
        payload={"org_id": org_a, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    http.payments["pay_cross"] = {
        "id": "pay_cross",
        "status": "captured",
        "order_id": "order_test1",
        "amount": 49900,
        "currency": "INR",
    }
    claimed = _verify(
        org_id=org_b,
        actor="owner-b",
        order_id="order_test1",
        payment_id="pay_cross",
    )
    assert claimed["result"]["entitled"] is False
    assert claimed["result"]["detail"] == "organization mismatch"
    forbidden = run_saas_platform(
        "checkout_verify",
        payload={
            "actor_user_id": "owner-b",
            "razorpay_order_id": "order_test1",
            "razorpay_payment_id": "pay_cross",
            "razorpay_signature": checkout_signature(
                "order_test1", "pay_cross", SECRET
            ),
        },
    )
    assert forbidden["ok"] is False
    assert forbidden.get("error_type") == "ForbiddenError"
    assert (svc.get_license(org_a, actor_user_id="owner-rzp").get("license") or {}).get(
        "metadata", {}
    ).get("source") != "razorpay"


def test_missing_webhook_signature_rejected(stack: tuple) -> None:
    svc, _http = stack
    body = b'{"id":"evt_nosig","event":"payment.captured"}'
    outcome = handle_razorpay_webhook(body, None, enterprise=svc)
    assert outcome["verified"] is False
    assert outcome["ok"] is False


def test_altered_webhook_payload_rejected(stack: tuple) -> None:
    svc, _http = stack
    original = b'{"id":"evt_orig","event":"payment.captured"}'
    altered = b'{"id":"evt_orig","event":"payment.captured","payload":{"tampered":true}}'
    outcome = handle_razorpay_webhook(
        altered, webhook_signature(original, WEBHOOK_SECRET), enterprise=svc
    )
    assert outcome["verified"] is False
    assert outcome["ok"] is False


def test_billing_event_keys_persist_on_database_port(stack: tuple) -> None:
    from production_platform import InMemoryDatabasePort

    from dsp_platform.saas_platform.db_store import DatabaseSaasOverlayStore

    svc, _http = stack
    db = InMemoryDatabasePort()
    overlay = DatabaseSaasOverlayStore(db)
    reset_saas_overlay_store_for_tests(overlay)
    org_id = _org()
    run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "starter", "actor_user_id": "owner-rzp"},
    )
    body = json.dumps(
        {
            "id": "evt_persist_1",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_persist",
                        "order_id": "order_test1",
                        "amount": 49900,
                        "currency": "INR",
                        "status": "captured",
                    }
                }
            },
        }
    ).encode()
    first = handle_razorpay_webhook(
        body, webhook_signature(body, WEBHOOK_SECRET), enterprise=svc, overlay=overlay
    )
    assert first["entitled"] is True
    restored = DatabaseSaasOverlayStore(db)
    assert restored.has_processed_billing_event("evt_persist_1") is True
    assert restored.has_processed_payment("pay_persist") is True
    second = handle_razorpay_webhook(
        body, webhook_signature(body, WEBHOOK_SECRET), enterprise=svc, overlay=restored
    )
    assert second["duplicate"] is True
    assert second["entitled"] is False
    licenses = [row for row in svc.store.licenses.values() if row.org_id == org_id]
    assert len(licenses) == 1
