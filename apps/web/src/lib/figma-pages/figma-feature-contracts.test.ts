/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/advisor",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({ children }: { children: unknown }) => children,
}));

import { formatInr } from "@/components/pages/AdvisorClients";
import { validateContact } from "@/components/marketing/ContactForm";
import { SETTING_SECTIONS } from "@/components/pages/ControlCenterSettings";
import { toneOf } from "@/components/pages/DiagnosticsStatus";

describe("Figma Advisor display helpers", () => {
  it("does not invent a currency figure when value is missing", () => {
    expect(formatInr(null)).toBe("Data unavailable.");
    expect(formatInr(undefined)).toBe("Data unavailable.");
    expect(formatInr(Number.NaN)).toBe("Data unavailable.");
  });

  it("formats advisor-entered rupee amounts compactly", () => {
    expect(formatInr(75_000)).toBe("₹75,000");
    expect(formatInr(450_000)).toMatch(/^₹4\.5L$/);
    expect(formatInr(12_000_000)).toMatch(/^₹1\.2Cr$/);
  });
});

describe("Figma Contact form validation", () => {
  it("rejects incomplete payloads before they hit the API", () => {
    expect(validateContact({ name: "", email: "a@b.co", message: "Hello there" })).toMatch(/name/i);
    expect(validateContact({ name: "Ada", email: "not-an-email", message: "Hello there" })).toMatch(/email/i);
    expect(validateContact({ name: "Ada", email: "ada@example.com", message: "short" })).toMatch(/10/);
  });

  it("accepts a valid message", () => {
    expect(
      validateContact({
        name: "Ada",
        email: "ada@example.com",
        message: "I would like enterprise access.",
      }),
    ).toBeNull();
  });
});

describe("Figma Control Center and Diagnostics", () => {
  it("covers every Figma settings toggle with a preference key", () => {
    const keys = SETTING_SECTIONS.flatMap((s) => s.items.map((i) => i.key));
    expect(keys).toEqual(
      expect.arrayContaining([
        "notifications",
        "dsp_alerts",
        "email_digest",
        "peer_comparisons",
        "auto_research",
        "dark_mode",
        "compact_view",
        "beta_features",
      ]),
    );
    expect(keys).toHaveLength(8);
  });

  it("maps health statuses without inventing operational copy", () => {
    expect(toneOf("ready")).toBe("pass");
    expect(toneOf("degraded")).toBe("warn");
    expect(toneOf("fail")).toBe("fail");
    expect(toneOf("mystery")).toBe("unknown");
  });
});
