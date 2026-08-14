# Billing Architecture (EPIC-016)

## Principle

No fabricated payments, invoices, or checkout success. Until a vendor is fully wired with credentials + webhook verification, all adapters return:

**Billing provider unavailable.**

## Port

`BillingPort` (`packages/enterprise/src/enterprise/billing.py`):

- `provider_name()`
- `is_available()`
- `get_subscription(org_id)`
- `list_invoices(org_id)`
- `payment_status(org_id)`
- `create_checkout_session(org_id, plan=...)` (architecture)
- `verify_webhook(payload, signature=...)` (architecture)

## Adapters

| Adapter | Provider | Live payments |
|---|---|---|
| `NullBillingAdapter` | `null` | No |
| `StripeBillingAdapter` | `stripe` | No (credentials detected only) |
| `RazorpayBillingAdapter` | `razorpay` | No |
| `PaddleBillingAdapter` | `paddle` | No |

Select via `DSP_BILLING_PROVIDER` / `build_billing_adapter()`.

## Environment (future wiring)

- Stripe: `DSP_STRIPE_SECRET_KEY`, `DSP_STRIPE_WEBHOOK_SECRET`
- Razorpay: `DSP_RAZORPAY_KEY_ID`, `DSP_RAZORPAY_KEY_SECRET`, `DSP_RAZORPAY_WEBHOOK_SECRET`
- Paddle: `DSP_PADDLE_API_KEY`, `DSP_PADDLE_WEBHOOK_SECRET`

Presence of credentials does **not** enable `is_available()` in EPIC-016 — that requires a dedicated vendor integration epic with verified webhooks and entitlement sync.

## Entitlements

Licensing remains in `EnterpriseService.assign_license` / `validate_license` and is independent of payment execution. Billing status must never invent paid state.
