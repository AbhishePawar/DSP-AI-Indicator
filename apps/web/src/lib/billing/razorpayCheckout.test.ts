/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

import { openRazorpayCheckout } from "@/lib/billing/razorpayCheckout";

describe("openRazorpayCheckout", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    delete window.Razorpay;
  });

  it("opens Checkout with server-supplied key and order_id only", async () => {
    const open = vi.fn();
    window.Razorpay = vi.fn().mockImplementation((opts: Record<string, unknown>) => {
      expect(opts.key).toBe("rzp_test_public");
      expect(opts.order_id).toBe("order_abc");
      expect(opts.amount).toBe(49900);
      expect(opts.currency).toBe("INR");
      return { open };
    }) as unknown as typeof window.Razorpay;

    await openRazorpayCheckout({
      keyId: "rzp_test_public",
      orderId: "order_abc",
      amount: 49900,
      currency: "INR",
      onSuccess: vi.fn(),
    });
    expect(open).toHaveBeenCalled();
  });
});
