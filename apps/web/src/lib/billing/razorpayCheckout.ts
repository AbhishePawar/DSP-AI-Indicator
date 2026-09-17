/**
 * Thin Razorpay Checkout.js loader.
 * Amounts and order_id must come from POST /api/v1/saas/checkout — never from the browser.
 */

export type RazorpayCheckoutSuccess = {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
};

export type RazorpayCheckoutOptions = {
  keyId: string;
  orderId: string;
  amount: number;
  currency: string;
  name?: string;
  description?: string;
  onSuccess: (payload: RazorpayCheckoutSuccess) => void;
  onDismiss?: () => void;
};

type RazorpayCtor = new (options: Record<string, unknown>) => { open: () => void };

declare global {
  interface Window {
    Razorpay?: RazorpayCtor;
  }
}

const CHECKOUT_SCRIPT = "https://checkout.razorpay.com/v1/checkout.js";

function scriptNonce(): string | null {
  if (typeof document === "undefined") return null;
  const tagged = document.querySelector("script[nonce]");
  const nonce = tagged?.getAttribute("nonce");
  if (nonce) return nonce;
  return document.querySelector('meta[name="csp-nonce"]')?.getAttribute("content") || null;
}

export function loadRazorpayCheckoutScript(): Promise<RazorpayCtor> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Razorpay Checkout unavailable."));
  }
  if (window.Razorpay) {
    return Promise.resolve(window.Razorpay);
  }
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${CHECKOUT_SCRIPT}"]`,
    );
    const finish = () => {
      if (window.Razorpay) {
        resolve(window.Razorpay);
        return;
      }
      reject(new Error("Razorpay Checkout unavailable."));
    };
    if (existing) {
      existing.addEventListener("load", finish);
      existing.addEventListener("error", () =>
        reject(new Error("Razorpay Checkout unavailable.")),
      );
      return;
    }
    const el = document.createElement("script");
    el.src = CHECKOUT_SCRIPT;
    el.async = true;
    const nonce = scriptNonce();
    if (nonce) el.setAttribute("nonce", nonce);
    el.onload = finish;
    el.onerror = () => reject(new Error("Razorpay Checkout unavailable."));
    document.head.appendChild(el);
  });
}

export async function openRazorpayCheckout(
  options: RazorpayCheckoutOptions,
): Promise<void> {
  const Razorpay = await loadRazorpayCheckoutScript();
  const checkout = new Razorpay({
    key: options.keyId,
    order_id: options.orderId,
    amount: options.amount,
    currency: options.currency,
    name: options.name || "DSP AI Indicator",
    description: options.description || "Subscription",
    handler: (response: RazorpayCheckoutSuccess) => {
      options.onSuccess({
        razorpay_order_id: String(response.razorpay_order_id || ""),
        razorpay_payment_id: String(response.razorpay_payment_id || ""),
        razorpay_signature: String(response.razorpay_signature || ""),
      });
    },
    modal: {
      ondismiss: () => {
        options.onDismiss?.();
      },
    },
  });
  checkout.open();
}
