# Razorpay integration (self-hosted FastAPI)

This is the implementation path for India SaaS billing. There is no Vercel
function and no Google Cloud Function in the payment path. Razorpay talks only
to **our** FastAPI process.

Razorpay Dashboard webhook should NOT be configured until the endpoint has been
deployed to our own HTTPS server and externally tested.

This document does not claim production readiness. Local tests prove signature
handling, order creation against a fake HTTP client, and entitlement
idempotency. They do not prove a live Razorpay account, HTTPS termination, or
dashboard configuration.

## Credentials (three different secrets)

| Variable | What it is | Where it lives | Who sees it |
|---|---|---|---|
| `DSP_RAZORPAY_KEY_ID` | API Key ID (public identifier) | Server env; also returned to Checkout.js | Browser may receive it from **our** checkout API |
| `DSP_RAZORPAY_KEY_SECRET` | API Key Secret | Server env only | Razorpay Orders API Basic Auth + checkout HMAC |
| `DSP_RAZORPAY_WEBHOOK_SECRET` | Webhook signing secret | Server env only | HMAC of the **raw** webhook body |

Never set `NEXT_PUBLIC_RAZORPAY_KEY_SECRET` or
`NEXT_PUBLIC_RAZORPAY_WEBHOOK_SECRET`. Never log these values.

Also required:

- `DSP_BILLING_PROVIDER=razorpay`
- `DSP_RAZORPAY_PLAN_PRICES_PAISE` (server-side paise, e.g. `starter=49900`)
- `DSP_RAZORPAY_CURRENCY=INR` (optional; default INR)

`is_available()` is true only when Key ID, Key Secret, **and** Webhook Secret
are all set **and** the adapter implements Orders + HMAC verification. Missing
credentials stay `Billing provider unavailable.` Stripe/Paddle/Null stay
unavailable.

## Checkout

```
Browser
  → POST /api/v1/saas/checkout          (authenticated JWT/session)
  → BillingPort.create_checkout_session
  → RazorpayBillingAdapter
  → HTTPS POST https://api.razorpay.com/v1/orders
  → response: key_id, order_id, amount, currency, plan_id
  → Razorpay Checkout.js (amount is display-only; server already locked it)
  → POST /api/v1/saas/checkout/verify   (authenticated)
  → HMAC(order_id|payment_id, KEY_SECRET)
  → fetch payment from Razorpay
  → match internal checkout intent (org, order, amount, currency)
  → existing EnterpriseService.apply_paid_license
```

Amount and currency are taken from `DSP_RAZORPAY_PLAN_PRICES_PAISE` /
`DSP_RAZORPAY_CURRENCY`. Client `amount` / `currency` are discarded on the
checkout route. Unpriced plans return **Unable to calculate.**

The browser never decides entitlement. Checkout.js “success” is not enough.

## Webhook

```
Razorpay
  → POST /api/v1/saas/webhooks/razorpay
  → read raw body (before JSON parsing)
  → HMAC-SHA256(raw body, WEBHOOK_SECRET)
  → constant-time compare with X-Razorpay-Signature
  → reject missing/invalid/altered signatures (HTTP 400)
  → claim provider event id (persistent idempotency)
  → update checkout intent / billing overlay
  → existing license/entitlement system on captured/paid only
```

This route is **not** JWT-authenticated. Razorpay cannot send our cookies or
CSRF token. CSRF and rate-limit public prefixes include only this webhook path.
Webhook authentication **is** the HMAC signature.

## Events handled

Subscriptions are **not** implemented. `subscription.*` events are ignored.

| Event | Effect |
|---|---|
| `payment.authorized` | Record intent status; **no** license |
| `payment.captured` | Entitle if amount/currency match the server checkout intent |
| `order.paid` | Same as captured |
| `payment.failed` | Mark intent failed; do **not** grant or revoke paid license |

## Idempotency

Duplicate Razorpay deliveries must not grant twice.

- Provider **event id** is claimed in `saas_billing_event_keys` (and the overlay snapshot).
- Provider **payment id** is claimed in `saas_billing_payment_keys`.
- Checkout intents live in the SaaS overlay (order_id → org, plan, amount, currency).

These tables are created with `CREATE TABLE IF NOT EXISTS` on
`DatabaseSaasOverlayStore.ensure_schema`. They do not drop existing data.
Reversal (operators only, not auto-run):

```sql
DROP TABLE IF EXISTS saas_billing_payment_keys;
DROP TABLE IF EXISTS saas_billing_event_keys;
```

In-memory overlay (tests without a DatabasePort) uses the same claim methods on
process-local dicts. Production SaaS overlay must use `DatabaseSaasOverlayStore`.

## Why urllib instead of the official Razorpay SDK

The billing boundary is `BillingPort`. Orders and payment fetch are a small
HTTPS JSON surface (`/v1/orders`, `/v1/payments/{id}`) with Basic Auth. HMAC
schemes are documented and implemented with the stdlib (`hmac`, `hashlib`,
`urllib`). Adding `razorpay` would pull a vendor SDK that is not required for
this contract and is harder to fake in tests. Tests inject
`RazorpayHttpClient`; no live charges are created.

## Security notes

- Checkout and verify require the authenticated actor and `billing.view`.
- Webhook HMAC uses the raw body, not a re-serialized JSON object.
- Signature compare is `hmac.compare_digest` after equal-length encoding.
- Payment fetch must show `order_id` equal to the internal checkout order.
- Claimed `org_id` on verify must match the intent org; another org’s order is rejected.
- Failed payments never call `apply_paid_license`.
- Key Secret / Webhook Secret are never returned in API payloads.
