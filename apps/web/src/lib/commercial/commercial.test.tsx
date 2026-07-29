/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LegalNavLinks } from "@/components/legal/LegalNavLinks";
import { TUTORIAL_STEPS } from "@/lib/beta/onboardingSteps";
import {
  FEATURE_MATRIX_ROWS,
  PRODUCT_EDITIONS,
  SUPPORT_CONTACT,
} from "@/lib/commercial";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";

describe("P6.1 commercial packaging", () => {
  it("defines three editions with usage limits", () => {
    expect(PRODUCT_EDITIONS).toHaveLength(3);
    expect(FEATURE_MATRIX_ROWS.length).toBeGreaterThan(5);
    const research = PRODUCT_EDITIONS.find((e) => e.id === "research");
    expect(research?.analysesPerMonth).toBe(25);
    expect(research?.monthlyPriceUsd).toBe(0);
  });

  it("exposes support contact path metadata", () => {
    expect(SUPPORT_CONTACT.knowledgeBasePath).toBe("/docs");
    expect(SUPPORT_CONTACT.faqPath).toBe("/docs/faq");
  });

  it("keeps onboarding steps actionable", () => {
    const bodies = TUTORIAL_STEPS.map((s) => s.body).join(" ");
    expect(bodies).toMatch(/AAPL/);
    expect(bodies).toMatch(/Support|Feedback/i);
  });
});

describe("P6.1 support nav", () => {
  it("renders Support link alongside legal links", () => {
    cleanup();
    render(<LegalNavLinks />);
    const support = screen.getByRole("link", { name: "Support" });
    expect(support.getAttribute("href")).toBe("/docs/support");
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
  });
});
