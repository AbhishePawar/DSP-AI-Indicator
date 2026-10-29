import { describe, expect, it } from "vitest";
import { resolveAssetEntry } from "./resolver";

describe("Dynamic Asset Resolver (Frontend)", () => {
  it("resolves catalog equity Apple", () => {
    const asset = resolveAssetEntry("AAPL");
    expect(asset).not.toBeNull();
    expect(asset?.symbol).toBe("AAPL");
    expect(asset?.assetClass).toBe("equity");
    expect(asset?.allowsEquityValuation).toBe(true);
  });

  it("resolves extended equity Tata Motors with dual-listing and BSE code", () => {
    const asset = resolveAssetEntry("Tata Motors");
    expect(asset).not.toBeNull();
    expect(asset?.symbol).toBe("TATAMOTORS");
    expect(asset?.exchange).toBe("NSE");
    expect(asset?.bseCode).toBe("500570");
    expect(asset?.isDualListed).toBe(true);
    expect(asset?.assetClass).toBe("equity");
  });

  it("resolves numeric BSE scrip code 500570 to Tata Motors on BSE", () => {
    const asset = resolveAssetEntry("500570");
    expect(asset).not.toBeNull();
    expect(asset?.symbol).toBe("TATAMOTORS");
    expect(asset?.exchange).toBe("BSE");
    expect(asset?.assetClass).toBe("equity");
  });

  it("resolves Commodity Gold on MCX and flags it as not eligible for equity valuation", () => {
    const asset = resolveAssetEntry("Gold");
    expect(asset).not.toBeNull();
    expect(asset?.symbol).toBe("GOLD");
    expect(asset?.exchange).toBe("MCX");
    expect(asset?.assetClass).toBe("commodity");
    expect(asset?.allowsEquityValuation).toBe(false);
    expect(asset?.allowsBuffettAnalysis).toBe(false);
    expect(asset?.allowsCommodityResearch).toBe(true);
  });

  it("resolves Crude Oil commodity on MCX", () => {
    const asset = resolveAssetEntry("Crude Oil");
    expect(asset).not.toBeNull();
    expect(asset?.symbol).toBe("CRUDEOIL");
    expect(asset?.assetClass).toBe("commodity");
  });

  it("resolves Index Nifty 50 and SENSEX", () => {
    const n50 = resolveAssetEntry("NIFTY50");
    expect(n50?.assetClass).toBe("index");
    expect(n50?.exchange).toBe("NSE");

    const sensex = resolveAssetEntry("SENSEX");
    expect(sensex?.assetClass).toBe("index");
    expect(sensex?.exchange).toBe("BSE");
  });

  it("flags ambiguous query with candidate list", () => {
    const asset = resolveAssetEntry("Tata");
    expect(asset).not.toBeNull();
    expect(asset?.ambiguous).toBe(true);
    expect(asset?.candidates && asset.candidates.length > 1).toBe(true);
  });

  it("falls back to single-token ticker safely", () => {
    const asset = resolveAssetEntry("ANYTICKER");
    expect(asset).not.toBeNull();
    expect(asset?.symbol).toBe("ANYTICKER");
    expect(asset?.assetClass).toBe("equity");
  });
});
