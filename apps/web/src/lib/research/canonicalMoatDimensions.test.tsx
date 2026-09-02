/**
 * @vitest-environment jsdom
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CanonicalMoatDimensionsSection } from "@/components/research/CanonicalMoatDimensionsSection";
import type { StageSectionView } from "@/lib/research/mapResearchView";
import {
  CANONICAL_MOAT_DIMENSION_IDS,
  CANONICAL_MOAT_DISPLAY_NAMES,
  MOAT_RATING_UNAVAILABLE_DISPLAY,
  mapCanonicalMoatDimensions,
  privateFieldsPresentIn,
  type CanonicalMoatDimensionId,
} from "@/lib/research/canonicalMoatDimensions";

const MAPPER_SOURCE = readFileSync(
  path.join(
    path.dirname(fileURLToPath(import.meta.url)),
    "canonicalMoatDimensions.ts",
  ),
  "utf8",
);

function row(
  identifier: string,
  extras: Record<string, unknown> = {},
): Record<string, unknown> {
  return { identifier, ...extras };
}

function assessed(
  identifier: CanonicalMoatDimensionId,
  rating: string,
  score: number,
): Record<string, unknown> {
  return row(identifier, {
    name: CANONICAL_MOAT_DISPLAY_NAMES[identifier],
    canonical_score_100: score,
    presentation_rating_10: rating,
    presentation_rating_status: "assessed",
    engine_status: "assessed",
  });
}

function emptyOverallMoat(): StageSectionView {
  return {
    stage: "economic_moat",
    status: "succeeded",
    label: "Wide",
    decision: "Durable",
    score: "0.85",
    confidence: "Unavailable",
    error: null,
    warnings: [],
    metrics: [
      { label: "Score", value: "0.85" },
      { label: "Moat", value: "Wide" },
      { label: "Competitive Position", value: "Durable" },
      { label: "Confidence", value: "Unavailable" },
    ],
  };
}

describe("canonical Economic Moat dimensions contract", () => {
  it("accepts the six frozen identifiers in frozen order", () => {
    const raw = [
      assessed("efficient_scale", "6.0/10", 60),
      assessed("brand", "8.0/10", 80),
      assessed("intangible_assets", "5.0/10", 50),
      assessed("network_effects", "7.6/10", 76),
      assessed("cost_advantage", "4.0/10", 40),
      assessed("switching_costs", "7.5/10", 75),
    ];
    const mapped = mapCanonicalMoatDimensions(raw);
    expect(mapped.dimensions.map((d) => d.identifier)).toEqual([
      ...CANONICAL_MOAT_DIMENSION_IDS,
    ]);
    expect(mapped.dimensions.map((d) => d.name)).toEqual([
      "Brand",
      "Network Effects",
      "Switching Costs",
      "Cost Advantage",
      "Intangible Assets",
      "Efficient Scale",
    ]);
    expect(mapped.rejectedUnknownIdentifiers).toEqual([]);
  });

  it("fails closed on an unknown seventh dimension", () => {
    const raw = [
      assessed("brand", "8.0/10", 80),
      assessed("network_effects", "7.6/10", 76),
      assessed("switching_costs", "7.5/10", 75),
      assessed("cost_advantage", "8.2/10", 82),
      assessed("intangible_assets", "5.0/10", 50),
      assessed("efficient_scale", "6.0/10", 60),
      row("pricing_power", {
        presentation_rating_10: "9.9/10",
        presentation_rating_status: "assessed",
        canonical_score_100: 99,
      }),
    ];
    const mapped = mapCanonicalMoatDimensions(raw);
    expect(mapped.dimensions).toHaveLength(6);
    expect(mapped.dimensions.map((d) => d.identifier)).toEqual([
      ...CANONICAL_MOAT_DIMENSION_IDS,
    ]);
    expect(mapped.rejectedUnknownIdentifiers).toEqual(["pricing_power"]);
    expect(JSON.stringify(mapped.dimensions)).not.toContain("pricing_power");
    expect(JSON.stringify(mapped.dimensions)).not.toContain("9.9/10");
  });

  it("renders DSP-supplied 76 → 7.6/10 without recalculating", () => {
    const mapped = mapCanonicalMoatDimensions([
      assessed("brand", "7.6/10", 76),
    ]);
    expect(mapped.dimensions[0]?.displayRating).toBe("7.6/10");
  });

  it("renders DSP-supplied 80 → 8.0/10 without recalculating", () => {
    const mapped = mapCanonicalMoatDimensions([
      assessed("brand", "8.0/10", 80),
    ]);
    expect(mapped.dimensions[0]?.displayRating).toBe("8.0/10");
  });

  it("renders DSP-supplied 75 → 7.5/10 without recalculating", () => {
    const mapped = mapCanonicalMoatDimensions([
      assessed("switching_costs", "7.5/10", 75),
    ]);
    expect(
      mapped.dimensions.find((d) => d.identifier === "switching_costs")
        ?.displayRating,
    ).toBe("7.5/10");
  });

  it("renders null presentation rating as N/A even when a score exists", () => {
    const mapped = mapCanonicalMoatDimensions([
      row("brand", {
        canonical_score_100: 76,
        presentation_rating_10: null,
        presentation_rating_status: "assessed",
        engine_status: "assessed",
      }),
    ]);
    expect(mapped.dimensions[0]?.displayRating).toBe(
      MOAT_RATING_UNAVAILABLE_DISPLAY,
    );
    expect(mapped.dimensions[0]?.displayRating).not.toBe("7.6/10");
    expect(mapped.dimensions[0]?.displayRating).not.toBe("0/10");
  });

  it("renders insufficient_data as N/A", () => {
    const mapped = mapCanonicalMoatDimensions([
      row("brand", {
        presentation_rating_10: null,
        presentation_rating_status: "insufficient_data",
        engine_status: "insufficient_data",
      }),
    ]);
    expect(mapped.dimensions[0]?.displayRating).toBe("N/A");
    expect(mapped.dimensions[0]?.displayRating).not.toBe("0/10");
  });

  it("renders unavailable as N/A", () => {
    const mapped = mapCanonicalMoatDimensions([
      row("network_effects", {
        presentation_rating_10: null,
        presentation_rating_status: "unavailable",
        engine_status: "unavailable",
      }),
    ]);
    expect(
      mapped.dimensions.find((d) => d.identifier === "network_effects")
        ?.displayRating,
    ).toBe("N/A");
  });

  it("renders not_implemented as N/A", () => {
    const mapped = mapCanonicalMoatDimensions([
      row("efficient_scale", {
        presentation_rating_10: null,
        presentation_rating_status: "not_implemented",
        engine_status: "not_implemented",
      }),
    ]);
    expect(
      mapped.dimensions.find((d) => d.identifier === "efficient_scale")
        ?.displayRating,
    ).toBe("N/A");
  });

  it("can render assessed zero as 0.0/10 when DSP supplies that value", () => {
    const mapped = mapCanonicalMoatDimensions([
      assessed("brand", "0.0/10", 0),
    ]);
    expect(mapped.dimensions[0]?.displayRating).toBe("0.0/10");
  });

  it("does not display 0/10 for closed statuses even if a zero rating is stuffed", () => {
    for (const status of [
      "insufficient_data",
      "unavailable",
      "not_implemented",
    ] as const) {
      const mapped = mapCanonicalMoatDimensions([
        row("brand", {
          presentation_rating_10: "0.0/10",
          presentation_rating_status: status,
          canonical_score_100: 0,
        }),
      ]);
      expect(mapped.dimensions[0]?.displayRating).toBe("N/A");
    }
  });

  it("never fills missing dimensions from overall moat", () => {
    const mapped = mapCanonicalMoatDimensions({
      overall_moat_score: 80,
      overall: assessed("brand", "8.0/10", 80),
      economic_moat: { score: 80, rating: "wide" },
    });
    expect(mapped.dimensions).toHaveLength(6);
    expect(
      mapped.dimensions.every((d) => d.displayRating === "N/A"),
    ).toBe(true);
  });

  it("does not recreate the authoritative X/10 calculation", () => {
    expect(MAPPER_SOURCE).not.toMatch(/canonical_score_100\s*\/\s*10/);
    expect(MAPPER_SOURCE).not.toContain("scoreOutOf10FromExisting");
    expect(MAPPER_SOURCE).not.toContain("/ 10.0");
    expect(MAPPER_SOURCE).not.toContain("/ 10)");
    const mapped = mapCanonicalMoatDimensions([
      row("brand", {
        canonical_score_100: 82,
        presentation_rating_10: null,
        presentation_rating_status: "assessed",
      }),
    ]);
    expect(mapped.dimensions[0]?.displayRating).toBe("N/A");
    expect(mapped.dimensions[0]?.displayRating).not.toBe("8.2/10");
  });

  it("keeps overall economic moat out of the dimension rows", () => {
    const mapped = mapCanonicalMoatDimensions([
      assessed("brand", "8.0/10", 80),
    ]);
    expect(mapped.dimensions.map((d) => d.identifier)).not.toContain(
      "overall",
    );
    expect(mapped.dimensions.map((d) => d.name)).not.toContain(
      "Overall Economic Moat",
    );
  });

  it("does not copy private fields into the public UI view", () => {
    const mapped = mapCanonicalMoatDimensions([
      row("brand", {
        presentation_rating_10: "8.0/10",
        presentation_rating_status: "assessed",
        provider: "openai",
        model_name: "gpt-forbidden",
        prompt: "private methodology",
        routing: "tier-1",
        token_count: 99,
        ai_cost: 1.23,
        chain_of_thought: "secret reasoning",
        tool_calls: [{ name: "internal" }],
      }),
    ]);
    expect(privateFieldsPresentIn(mapped.dimensions)).toEqual([]);
    expect(JSON.stringify(mapped.dimensions)).not.toContain("openai");
    expect(JSON.stringify(mapped.dimensions)).not.toContain("gpt-forbidden");
    expect(JSON.stringify(mapped.dimensions)).not.toContain(
      "private methodology",
    );
  });

  it("renders the six dimensions and overall moat as separate UI regions", () => {
    const mapped = mapCanonicalMoatDimensions([
      assessed("brand", "7.6/10", 76),
      assessed("network_effects", "8.0/10", 80),
      row("switching_costs", {
        presentation_rating_10: null,
        presentation_rating_status: "insufficient_data",
      }),
      row("cost_advantage", {
        presentation_rating_10: null,
        presentation_rating_status: "unavailable",
      }),
      row("intangible_assets", {
        presentation_rating_10: null,
        presentation_rating_status: "not_implemented",
      }),
      assessed("efficient_scale", "0.0/10", 0),
    ]);
    render(
      <CanonicalMoatDimensionsSection
        dimensions={mapped.dimensions}
        overallMoat={emptyOverallMoat()}
      />,
    );
    expect(screen.getByText("Individual dimensions")).toBeTruthy();
    expect(screen.getByText("Overall economic moat")).toBeTruthy();
    expect(screen.getByText("Brand")).toBeTruthy();
    expect(screen.getByText("Network Effects")).toBeTruthy();
    expect(screen.getByText("Switching Costs")).toBeTruthy();
    expect(screen.getByText("Cost Advantage")).toBeTruthy();
    expect(screen.getByText("Intangible Assets")).toBeTruthy();
    expect(screen.getByText("Efficient Scale")).toBeTruthy();
    expect(screen.getByText("7.6/10")).toBeTruthy();
    expect(screen.getByText("8.0/10")).toBeTruthy();
    expect(screen.getByText("0.0/10")).toBeTruthy();
    expect(screen.getAllByText("N/A")).toHaveLength(3);
    expect(screen.getByText("Wide")).toBeTruthy();
    expect(screen.queryByText("0/10")).toBeNull();
  });
});
