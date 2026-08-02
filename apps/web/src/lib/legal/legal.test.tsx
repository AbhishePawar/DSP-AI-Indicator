/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import {
  DISCLAIMER_ACK_BULLETS,
  LEGAL_DOCUMENTS,
  LEGAL_ROUTES,
  RESEARCH_DISCLAIMER_ACK_KEY,
  acknowledgeResearchDisclaimer,
  clearResearchDisclaimerAcknowledgement,
  isResearchDisclaimerAcknowledged,
} from "@/lib/legal";
import { LegalNavLinks } from "@/components/legal/LegalNavLinks";
import { ResearchDisclaimerGate } from "@/components/legal/ResearchDisclaimerGate";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";

describe("P4.1 legal content", () => {
  it("exposes required legal documents", () => {
    expect(Object.keys(LEGAL_DOCUMENTS).sort()).toEqual(
      [
        "cookies",
        "data-usage",
        "disclaimer",
        "privacy",
        "risk",
        "terms",
      ].sort(),
    );
    expect(LEGAL_ROUTES.privacy).toBe("/docs/privacy");
    expect(LEGAL_ROUTES.terms).toBe("/docs/terms");
    expect(LEGAL_ROUTES.disclaimer).toBe("/docs/disclaimer");
  });

  it("states research-not-advice requirements in disclaimer", () => {
    const text = LEGAL_DOCUMENTS.disclaimer.sections
      .flatMap((s) => s.body)
      .join(" ");
    expect(text).toMatch(/research and educational/i);
    expect(text).toMatch(/not personalized investment advice/i);
    expect(text).toMatch(/Investing involves risk/i);
    expect(text).toMatch(/Past performance/i);
    expect(text).toMatch(/due diligence/i);
    expect(DISCLAIMER_ACK_BULLETS.length).toBeGreaterThanOrEqual(5);
  });

  it("documents data transparency themes", () => {
    const text = LEGAL_DOCUMENTS["data-usage"].sections
      .flatMap((s) => s.body)
      .join(" ");
    expect(text).toMatch(/Unavailable/i);
    expect(text).toMatch(/confidence/i);
    expect(text).toMatch(/pipeline_version|versioning/i);
  });
});

describe("P4.1 acknowledgement storage", () => {
  beforeEach(() => {
    clearResearchDisclaimerAcknowledgement();
  });

  it("starts unacknowledged and persists acknowledgement", () => {
    expect(isResearchDisclaimerAcknowledged()).toBe(false);
    acknowledgeResearchDisclaimer();
    expect(isResearchDisclaimerAcknowledged()).toBe(true);
    expect(localStorage.getItem(RESEARCH_DISCLAIMER_ACK_KEY)).toBe("1");
  });
});

describe("P4.1 LegalNavLinks", () => {
  beforeEach(() => {
    cleanup();
  });

  it("renders Privacy, Terms, Disclaimer, and Support links", () => {
    render(<LegalNavLinks />);
    const privacy = screen.getByRole("link", { name: "Privacy Policy" });
    const terms = screen.getByRole("link", { name: "Terms of Service" });
    const disclaimer = screen.getByRole("link", { name: "Disclaimer" });
    const support = screen.getByRole("link", { name: "Support" });
    expect(privacy.getAttribute("href")).toBe("/docs/privacy");
    expect(terms.getAttribute("href")).toBe("/docs/terms");
    expect(disclaimer.getAttribute("href")).toBe("/docs/disclaimer");
    expect(support.getAttribute("href")).toBe("/docs/support");
  });
});

describe("P4.1 ResearchDisclaimerGate", () => {
  beforeEach(() => {
    cleanup();
    clearResearchDisclaimerAcknowledgement();
  });

  it("requires checkbox before acknowledge continues", async () => {
    const onAcknowledged = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <ResearchDisclaimerGate
        open
        onOpenChange={onOpenChange}
        onAcknowledged={onAcknowledged}
      />,
    );

    expect(
      screen.getByRole("heading", { name: /Investment research disclaimer/i }),
    ).toBeTruthy();
    const continueBtn = screen.getByRole("button", {
      name: /Acknowledge and continue/i,
    });
    expect(continueBtn).toHaveProperty("disabled", true);

    fireEvent.click(
      screen.getByLabelText(/I understand the investment research disclaimer/i),
    );
    await waitFor(() => {
      expect(continueBtn).toHaveProperty("disabled", false);
    });

    fireEvent.click(continueBtn);
    expect(onAcknowledged).toHaveBeenCalled();
    expect(isResearchDisclaimerAcknowledged()).toBe(true);
  });
});

describe("P4.1 foundation version", () => {
  it("tracks host foundation version", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc.1");
  });
});
