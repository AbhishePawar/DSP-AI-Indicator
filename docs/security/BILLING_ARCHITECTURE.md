# Billing Architecture (EPIC-016 + Razorpay)

## Principle

No fabricated payments, invoices, or checkout success.

- **Null / Stripe / Paddle** adapters remain **Billing provider unavailable.**
- **Razorpay** is live only when `DSP_RAZORPAY_KEY_ID`, `DSP_RAZORPAY_KEY_SECRET`, and `DSP_RAZORPAY_WEBHOOK_SECRET` are set **and** the adapter performs real Order API calls plus HMAC verification.

## Port

`BillingPort` (`packages/enterprise/src/enterprise/billing.py`):

- `provider_name()`
- `is_available()`
- `get_subscription(org_id)`
- `list_invoices(org_id)`
- `payment_status(org_id)`
- `create_checkout_session(org_id, plan=..., **kwargs)`
- `verify_webhook(payload, signature=...)`
- `verify_checkout_signature(order_id=..., payment_id=..., signature=...)`

Select via `DSP_BILLING_PROVIDER` / `build_billing_adapter()` (default `null`).

## Razorpay (self-hosted FastAPI)

Razorpay talks to **our API process**. There is no Vercel function and no Google Cloud Function in this path.

Webhook URL to register in the Razorpay dashboard:

`POST https://<DSP_PUBLIC_API_ORIGIN>/api/v1/saas/webhooks/razorpay`

The route is unauthenticated. Razorpay authenticates with `X-Razorpay-Signature` (HMAC-SHA256 of the **raw body** using `DSP_RAZORPAY_WEBHOOK_SECRET`). CSRF and JWT are not required. Invalid signatures return **400**.

Checkout HMAC (`order_id|payment_id` with `DSP_RAZORPAY_KEY_SECRET`) is verified on `POST /api/v1/saas/checkout/verify` (authenticated). Entitlements change only after a **captured** payment that matches the server-side checkout intent (amount + currency). Frontend “success” is never enough.

### Events

| Event | Effect |
|---|---|
| `payment.authorized` | Record intent; **no** license |
| `payment.captured` | Idempotent entitlement if amount matches intent |
| `order.paid` | Same as captured |
| `payment.failed` | Mark intent failed; do not revoke admin licenses |
| other | Ignored (extensible, including future `subscription.*`) |

Amounts are resolved server-side from `DSP_RAZORPAY_PLAN_PRICES_PAISE` (paise). Client `amount` / `currency` are discarded. Unpriced or `custom` plans return **Unable to calculate.**

Paid entitlements reuse `EnterpriseService.apply_paid_license` → existing `License` + `PLAN_TO_LICENSE_TIER` and overlay `upsert_subscription`. No second licensing system.

Webhook event ids and payment ids are persisted on `DatabaseSaasOverlayStore` in `saas_billing_event_keys` / `saas_billing_payment_keys` (plus the overlay snapshot). This is not an in-memory set.

See `docs/security/RAZORPAY_INTEGRATION.md` for the full checkout/webhook flow and credential split.

Razorpay Dashboard webhook should NOT be configured until the endpoint has been deployed to our own HTTPS server and externally tested.

## Environment

- `DSP_BILLING_PROVIDER` — `null` / `stripe` / `razorpay` / `paddle`
- Razorpay: `DSP_RAZORPAY_KEY_ID`, `DSP_RAZORPAY_KEY_SECRET`, `DSP_RAZORPAY_WEBHOOK_SECRET`
- Optional: `DSP_RAZORPAY_CURRENCY` (default `INR`), `DSP_RAZORPAY_PLAN_PRICES_PAISE` (`starter=49900,professional=149900`)
- Stripe (still unavailable): `DSP_STRIPE_SECRET_KEY`, `DSP_STRIPE_WEBHOOK_SECRET`
- Paddle (still unavailable): `DSP_PADDLE_API_KEY`, `DSP_PADDLE_WEBHOOK_SECRET`

Never put Razorpay secrets in `NEXT_PUBLIC_*`. The browser receives only `key_id` + `order_id` + server amount from checkout.

## Entitlements

Admin `POST /api/v1/saas/subscription` still assigns licenses without payment (operator provisioning). Paid checkout is a separate path. Billing status must never invent paid state without a verified capture/paid event.
