/** Dynamic Asset Resolution and Classification for Web Client.
 * Supports:
 * - Dynamic NSE & BSE listed equities
 * - BSE numeric scrip codes (e.g. 500570, 500112, 532540)
 * - Commodities (Gold, Silver, Crude Oil, Natural Gas, Copper) on MCX
 * - Indices (Nifty 50, BSE Sensex, Bank Nifty)
 * - Candidate lists for ambiguous queries
 * - Safe fallback for arbitrary single-token market tickers
 */

import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";

export interface ResolvedAsset {
  symbol: string;
  name: string;
  exchange: string;
  assetClass: "equity" | "commodity" | "index" | "etf";
  currency: string;
  unit?: string;
  bseCode?: string;
  isDualListed?: boolean;
  ambiguous?: boolean;
  candidates?: Array<{ symbol: string; name: string; exchange: string; assetClass?: string }>;
  allowsEquityValuation: boolean;
  allowsBuffettAnalysis: boolean;
  allowsCommodityResearch: boolean;
}

const COMMODITIES: Array<Omit<ResolvedAsset, "allowsEquityValuation" | "allowsBuffettAnalysis" | "allowsCommodityResearch">> = [
  {
    symbol: "GOLD",
    name: "Gold",
    exchange: "MCX",
    assetClass: "commodity",
    currency: "INR",
    unit: "10 grams",
  },
  {
    symbol: "SILVER",
    name: "Silver",
    exchange: "MCX",
    assetClass: "commodity",
    currency: "INR",
    unit: "1 kilogram",
  },
  {
    symbol: "CRUDEOIL",
    name: "Crude Oil",
    exchange: "MCX",
    assetClass: "commodity",
    currency: "INR",
    unit: "1 barrel (bbl)",
  },
  {
    symbol: "NATURALGAS",
    name: "Natural Gas",
    exchange: "MCX",
    assetClass: "commodity",
    currency: "INR",
    unit: "1 MMBtu",
  },
  {
    symbol: "COPPER",
    name: "Copper",
    exchange: "MCX",
    assetClass: "commodity",
    currency: "INR",
    unit: "1 kilogram",
  },
];

const INDICES: Array<Omit<ResolvedAsset, "allowsEquityValuation" | "allowsBuffettAnalysis" | "allowsCommodityResearch">> = [
  {
    symbol: "NIFTY50",
    name: "Nifty 50 Index",
    exchange: "NSE",
    assetClass: "index",
    currency: "INR",
    unit: "points",
  },
  {
    symbol: "SENSEX",
    name: "S&P BSE Sensex Index",
    exchange: "BSE",
    assetClass: "index",
    currency: "INR",
    unit: "points",
  },
  {
    symbol: "BANKNIFTY",
    name: "Nifty Bank Index",
    exchange: "NSE",
    assetClass: "index",
    currency: "INR",
    unit: "points",
  },
];

const EXTENDED_EQUITIES: Array<{
  symbol: string;
  name: string;
  exchange: string;
  bseCode?: string;
  isDualListed?: boolean;
  aliases: string[];
}> = [
  {
    symbol: "TATAMOTORS",
    name: "Tata Motors Limited",
    exchange: "NSE",
    bseCode: "500570",
    isDualListed: true,
    aliases: ["tata motors", "tatamotors", "tml"],
  },
  {
    symbol: "TATASTEEL",
    name: "Tata Steel Limited",
    exchange: "NSE",
    bseCode: "500470",
    isDualListed: true,
    aliases: ["tata steel", "tatasteel"],
  },
  {
    symbol: "SBIN",
    name: "State Bank of India",
    exchange: "NSE",
    bseCode: "500112",
    isDualListed: true,
    aliases: ["sbi", "state bank of india", "sbin"],
  },
  {
    symbol: "BHARTIARTL",
    name: "Bharti Airtel Limited",
    exchange: "NSE",
    bseCode: "532454",
    isDualListed: true,
    aliases: ["airtel", "bharti airtel", "bhartiartl"],
  },
  {
    symbol: "KOTAKBANK",
    name: "Kotak Mahindra Bank Limited",
    exchange: "NSE",
    bseCode: "500247",
    isDualListed: true,
    aliases: ["kotak", "kotak bank", "kotak mahindra bank"],
  },
  {
    symbol: "LT",
    name: "Larsen & Toubro Limited",
    exchange: "NSE",
    bseCode: "500510",
    isDualListed: true,
    aliases: ["l&t", "larsen & toubro", "larsen and toubro", "lt"],
  },
  {
    symbol: "AXISBANK",
    name: "Axis Bank Limited",
    exchange: "NSE",
    bseCode: "532215",
    isDualListed: true,
    aliases: ["axis", "axis bank", "axisbank"],
  },
  {
    symbol: "MARUTI",
    name: "Maruti Suzuki India Limited",
    exchange: "NSE",
    bseCode: "532500",
    isDualListed: true,
    aliases: ["maruti", "maruti suzuki"],
  },
  {
    symbol: "SUNPHARMA",
    name: "Sun Pharmaceutical Industries Limited",
    exchange: "NSE",
    bseCode: "524715",
    isDualListed: true,
    aliases: ["sun pharma", "sun pharmaceutical", "sunpharma"],
  },
  {
    symbol: "BAJFINANCE",
    name: "Bajaj Finance Limited",
    exchange: "NSE",
    bseCode: "500034",
    isDualListed: true,
    aliases: ["bajaj finance", "bajfinance"],
  },
  {
    symbol: "WIPRO",
    name: "Wipro Limited",
    exchange: "NSE",
    bseCode: "507685",
    isDualListed: true,
    aliases: ["wipro", "wipro limited"],
  },
  {
    symbol: "HCLTECH",
    name: "HCL Technologies Limited",
    exchange: "NSE",
    bseCode: "532281",
    isDualListed: true,
    aliases: ["hcl", "hcl tech", "hcl technologies", "hcltech"],
  },
  {
    symbol: "TATAPOWER",
    name: "Tata Power Company Limited",
    exchange: "NSE",
    bseCode: "500400",
    isDualListed: true,
    aliases: ["tata power", "tatapower"],
  },
  {
    symbol: "TATACONSUM",
    name: "Tata Consumer Products Limited",
    exchange: "NSE",
    bseCode: "500800",
    isDualListed: true,
    aliases: ["tata consumer", "tata consumer products", "tataconsum"],
  },
  {
    symbol: "ZOMATO",
    name: "Zomato Limited",
    exchange: "NSE",
    bseCode: "543320",
    isDualListed: true,
    aliases: ["zomato", "zomato limited"],
  },
  {
    symbol: "POLYCAB",
    name: "Polycab India Limited",
    exchange: "NSE",
    bseCode: "542651",
    isDualListed: true,
    aliases: ["polycab", "polycab india"],
  },
];

function normalize(s: string): string {
  return s.toLowerCase().replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
}

export function resolveAssetEntry(
  rawQuery: string,
  preferredExchange?: string | null,
): ResolvedAsset | null {
  const query = rawQuery.trim();
  if (!query) return null;

  const upper = query.toUpperCase();
  const norm = normalize(query);

  // 1. Check Commodities
  for (const c of COMMODITIES) {
    if (upper === c.symbol || norm === normalize(c.name)) {
      return {
        ...c,
        exchange: preferredExchange ? preferredExchange.toUpperCase() : c.exchange,
        allowsEquityValuation: false,
        allowsBuffettAnalysis: false,
        allowsCommodityResearch: true,
      };
    }
  }

  // 2. Check Indices
  for (const idx of INDICES) {
    if (upper === idx.symbol || norm === normalize(idx.name)) {
      return {
        ...idx,
        exchange: preferredExchange ? preferredExchange.toUpperCase() : idx.exchange,
        allowsEquityValuation: false,
        allowsBuffettAnalysis: false,
        allowsCommodityResearch: false,
      };
    }
  }

  // 3. Numeric BSE Scrip Code
  if (/^\d{5,6}$/.test(query)) {
    for (const eq of EXTENDED_EQUITIES) {
      if (eq.bseCode === query) {
        return {
          symbol: eq.symbol,
          name: eq.name,
          exchange: preferredExchange ? preferredExchange.toUpperCase() : "BSE",
          assetClass: "equity",
          currency: "INR",
          bseCode: query,
          isDualListed: true,
          allowsEquityValuation: true,
          allowsBuffettAnalysis: true,
          allowsCommodityResearch: false,
        };
      }
    }
    return {
      symbol: query,
      name: `BSE Scrip ${query}`,
      exchange: preferredExchange ? preferredExchange.toUpperCase() : "BSE",
      assetClass: "equity",
      currency: "INR",
      bseCode: query,
      allowsEquityValuation: true,
      allowsBuffettAnalysis: true,
      allowsCommodityResearch: false,
    };
  }

  // 4. Core Featured Catalogue
  const catMatch = COMPANY_CATALOGUE.find(
    (c) =>
      c.ticker.toUpperCase() === upper ||
      normalize(c.name) === norm,
  );
  if (catMatch) {
    return {
      symbol: catMatch.ticker,
      name: catMatch.name,
      exchange: preferredExchange ? preferredExchange.toUpperCase() : catMatch.exchange,
      assetClass: "equity",
      currency: catMatch.exchange === "NSE" || catMatch.exchange === "BSE" ? "INR" : "USD",
      allowsEquityValuation: true,
      allowsBuffettAnalysis: true,
      allowsCommodityResearch: false,
    };
  }

  // 5. Extended Equities
  for (const eq of EXTENDED_EQUITIES) {
    if (
      eq.symbol.toUpperCase() === upper ||
      normalize(eq.name) === norm ||
      eq.aliases.some((a) => normalize(a) === norm)
    ) {
      return {
        symbol: eq.symbol,
        name: eq.name,
        exchange: preferredExchange ? preferredExchange.toUpperCase() : eq.exchange,
        assetClass: "equity",
        currency: "INR",
        bseCode: eq.bseCode,
        isDualListed: eq.isDualListed,
        allowsEquityValuation: true,
        allowsBuffettAnalysis: true,
        allowsCommodityResearch: false,
      };
    }
  }

  // 6. Ambiguous substring match (e.g. "Tata")
  const equityMatches = EXTENDED_EQUITIES.filter(
    (eq) =>
      normalize(eq.name).includes(norm) ||
      eq.aliases.some((a) => normalize(a).includes(norm)),
  );
  if (equityMatches.length > 1) {
    return {
      symbol: upper,
      name: query,
      exchange: preferredExchange ? preferredExchange.toUpperCase() : "NSE",
      assetClass: "equity",
      currency: "INR",
      ambiguous: true,
      candidates: equityMatches.map((m) => ({
        symbol: m.symbol,
        name: m.name,
        exchange: m.exchange,
        assetClass: "equity",
      })),
      allowsEquityValuation: true,
      allowsBuffettAnalysis: true,
      allowsCommodityResearch: false,
    };
  }

  // 7. Single-token valid ticker fallback
  if (/^[A-Za-z0-9.\-]{1,32}$/.test(upper) && !/\s/.test(query)) {
    return {
      symbol: upper,
      name: upper,
      exchange: preferredExchange ? preferredExchange.toUpperCase() : "NSE",
      assetClass: "equity",
      currency: "INR",
      allowsEquityValuation: true,
      allowsBuffettAnalysis: true,
      allowsCommodityResearch: false,
    };
  }

  return null;
}
