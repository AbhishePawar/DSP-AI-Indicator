import { api } from "@/lib/api/client";

/**
 * Indian listing selection ? thin client over /fundamentals/resolve?select_listing=true.
 *
 * Does not rank BSE vs NSE in the browser. Stage 4I still sends the selected
 * exchange on statements / quote / analyse.
 */

export const INDIAN_LISTING_EXCHANGES = ["BSE", "NSE"] as const;
export const US_LISTING_EXCHANGES = ["NASDAQ", "NYSE"] as const;

export type ListingSelectionStatus =
  | "SELECTED"
  | "NOT_FOUND"
  | "AMBIGUOUS"
  | "NOT_APPLICABLE"
  | "UNAVAILABLE";

export type ListingSelectionPayload = {
  ok?: boolean;
  available?: boolean;
  status?: ListingSelectionStatus | string | null;
  symbol?: string;
  exchange?: string | null;
  isin?: string | null;
  detail?: string | null;
  identity?: { exchange?: string | null } | null;
};

export function normalizeExchange(
  exchange: string | null | undefined,
): string | undefined {
  const value = (exchange ?? "").trim().toUpperCase();
  return value || undefined;
}

export function isIndianListingVenue(
  exchange: string | null | undefined,
): boolean {
  const value = normalizeExchange(exchange);
  return value === "BSE" || value === "NSE";
}

export function isUsListingVenue(exchange: string | null | undefined): boolean {
  const value = normalizeExchange(exchange);
  return value === "NASDAQ" || value === "NYSE";
}

/** Narrow quote-currency mapping: Indian venues INR, NASDAQ USD. */
export function quoteCurrencyForExchange(
  exchange: string | null | undefined,
): "INR" | "USD" {
  if (isIndianListingVenue(exchange)) return "INR";
  return "USD";
}

export function listingQueryKey(
  symbol: string,
  explicitExchange?: string | null,
): readonly [string, string, string] {
  return [
    "listing-select",
    symbol.trim().toUpperCase(),
    normalizeExchange(explicitExchange) ?? "",
  ];
}

export function exchangeScopedQueryKey(
  scope: readonly string[],
  symbol: string,
  selectedExchange: string | undefined,
): readonly string[] {
  return [...scope, symbol, selectedExchange ?? ""];
}

/**
 * Catalogue NASDAQ/NYSE names skip Indian policy.
 * Indian (or unknown) names use the listing payload exchange when SELECTED.
 * Explicit caller exchange is passed to the backend; this helper does not
 * override it locally.
 */
export function selectedExchangeFromListing(args: {
  catalogueExchange?: string | null;
  explicitExchange?: string | null;
  listing?: ListingSelectionPayload | null;
}): string | undefined {
  const explicit = normalizeExchange(args.explicitExchange);
  if (explicit && isUsListingVenue(explicit)) {
    return explicit;
  }
  const catalogue = normalizeExchange(args.catalogueExchange);
  if (isUsListingVenue(catalogue) && !isIndianListingVenue(explicit)) {
    return catalogue;
  }
  if (args.listing?.status === "SELECTED") {
    return (
      normalizeExchange(args.listing.exchange) ??
      normalizeExchange(args.listing.identity?.exchange)
    );
  }
  return undefined;
}

export function shouldFetchIndianListing(
  catalogueExchange?: string | null,
  explicitExchange?: string | null,
): boolean {
  const explicit = normalizeExchange(explicitExchange);
  if (explicit && isUsListingVenue(explicit)) return false;
  const catalogue = normalizeExchange(catalogueExchange);
  if (isUsListingVenue(catalogue) && !isIndianListingVenue(explicit)) {
    return false;
  }
  return true;
}


export async function fetchSelectedExchange(args: {
  symbol: string;
  token?: string | null;
  catalogueExchange?: string | null;
  explicitExchange?: string | null;
}): Promise<string | undefined> {
  const explicit = normalizeExchange(args.explicitExchange);
  if (!shouldFetchIndianListing(args.catalogueExchange, explicit)) {
    return selectedExchangeFromListing({
      catalogueExchange: args.catalogueExchange,
      explicitExchange: explicit,
    });
  }
  const listing = await api.selectIndianListing(args.symbol, {
    token: args.token,
    exchange: explicit,
  });
  return selectedExchangeFromListing({
    catalogueExchange: args.catalogueExchange,
    explicitExchange: explicit,
    listing,
  });
}
