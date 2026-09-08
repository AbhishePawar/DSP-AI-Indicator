/** Security Master identity helpers — ISIN + MIC, never ticker-only. */

export type SecurityListingView = {
  company_name: string;
  ticker: string;
  isin: string;
  exchange: string;
  mic: string;
  security_type: string;
  eligibility: boolean;
  currency?: string | null;
  country?: string | null;
  listing_id?: string | null;
  series?: string | null;
};

export type SecuritySearchResponse = {
  ok: boolean;
  status: "MATCHES" | "UNKNOWN" | "REJECTED" | "UNSUPPORTED";
  query: string;
  results: SecurityListingView[];
  authority?: { source?: string; source_type?: string; retrieved_at?: string };
  detail?: string;
  message?: string | null;
};

export type SecurityResolveResponse = {
  ok: boolean;
  status: "RESOLVED" | "AMBIGUOUS" | "UNKNOWN" | "UNSUPPORTED" | "REJECTED";
  query: string;
  exchange?: string | null;
  isin?: string | null;
  mic?: string | null;
  identity: SecurityListingView | null;
  candidates: SecurityListingView[];
  detail?: string;
  message?: string | null;
};

export function analysisPath(listing: {
  ticker: string;
  exchange?: string | null;
  isin?: string | null;
  mic?: string | null;
}): string {
  const params = new URLSearchParams();
  params.set("symbol", listing.ticker.trim().toUpperCase());
  if (listing.exchange) params.set("exchange", listing.exchange);
  if (listing.isin) params.set("isin", listing.isin);
  if (listing.mic) params.set("mic", listing.mic);
  return `/analysis?${params.toString()}`;
}

export function identityFromSearchParams(params: {
  get: (name: string) => string | null;
}): {
  ticker: string;
  exchange: string;
  isin: string;
  mic: string;
} {
  return {
    ticker: (params.get("symbol") || "").trim().toUpperCase(),
    exchange: (params.get("exchange") || "").trim().toUpperCase(),
    isin: (params.get("isin") || "").trim().toUpperCase(),
    mic: (params.get("mic") || "").trim().toUpperCase(),
  };
}

export function hasExactListingIdentity(identity: {
  ticker: string;
  exchange: string;
  isin: string;
  mic: string;
}): boolean {
  return Boolean(identity.ticker && identity.exchange && identity.isin && identity.mic);
}
