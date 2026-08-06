/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  PORTFOLIO_SECTIONS,
  isPortfolioSectionId,
} from "@/lib/portfolio-intelligence";
import {
  DriftSection,
  IntegrationsSection,
  OverviewV2Extras,
  ScenariosSection,
} from "@/components/portfolio-intelligence/PortfolioV2Sections";
import { featureFlags } from "@/lib/featureFlags";

describe("EPIC-015 Portfolio Intelligence 2.0", () => {
  it("registers v2 sections", () => {
    const ids = PORTFOLIO_SECTIONS.map((s) => s.id);
    expect(ids).toEqual(
      expect.arrayContaining([
        "scenarios",
        "drift",
        "timeline",
        "integrations",
      ]),
    );
    expect(isPortfolioSectionId("scenarios")).toBe(true);
  });

  it("shows honest unavailable for scenarios and drift", () => {
    render(<ScenariosSection intel={null} />);
    expect(screen.getAllByText(/Analysis unavailable|Data unavailable/i).length).toBeGreaterThan(
      0,
    );

    render(<DriftSection intel={null} holdings={[]} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("never recommends transactions in integrations copy", () => {
    render(
      <IntegrationsSection
        holdings={[
          {
            company: "Apple",
            ticker: "AAPL",
            sector: "Technology",
            allocationPercent: 10,
            recommendation: "Data unavailable.",
            researchAvailable: true,
          },
        ]}
      />,
    );
    expect(screen.getByText(/never recommends transactions/i)).toBeTruthy();
    expect(screen.queryByText(/BUY|SELL|place order/i)).toBeNull();
  });

  it("overview extras stay honest about missing value fields", () => {
    if (!featureFlags.portfolioIntelligenceV2) return;
    render(<OverviewV2Extras holdings={[]} intel={null} />);
    expect(
      screen.getByText(/No portfolio market-value API/i),
    ).toBeTruthy();
  });
});
