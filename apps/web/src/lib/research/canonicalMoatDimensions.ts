/**
 * Canonical Economic Moat dimension contract for Research UI.
 *
 * Why a frontend mapping exists:
 * DSP already owns identifier, display name, and presentation_rating_10.
 * The web app only needs a fail-closed indexer so it can render exactly the
 * six frozen rows in frozen order, ignore unknown identifiers, and never
 * invent a second moat taxonomy or recalculate X/10.
 *
 * This mapper copies DSP presentation_rating_10. It does not divide
 * canonical_score_100 by 10. It does not fill missing rows from overall moat.
 */

export const CANONICAL_MOAT_DIMENSION_IDS = [
  "brand",
  "network_effects",
  "switching_costs",
  "cost_advantage",
  "intangible_assets",
  "efficient_scale",
] as const;

export type CanonicalMoatDimensionId =
  (typeof CANONICAL_MOAT_DIMENSION_IDS)[number];

export const CANONICAL_MOAT_DISPLAY_NAMES: Record<
  CanonicalMoatDimensionId,
  string
> = {
  brand: "Brand",
  network_effects: "Network Effects",
  switching_costs: "Switching Costs",
  cost_advantage: "Cost Advantage",
  intangible_assets: "Intangible Assets",
  efficient_scale: "Efficient Scale",
};

export const PRESENTATION_RATING_STATUSES = [
  "assessed",
  "insufficient_data",
  "unavailable",
  "not_implemented",
] as const;

export type PresentationRatingStatus =
  (typeof PRESENTATION_RATING_STATUSES)[number];

export const MOAT_RATING_UNAVAILABLE_DISPLAY = "N/A";

const PRIVATE_UI_FIELD_NAMES = new Set([
  "api_key",
  "api_keys",
  "canary",
  "chain_of_thought",
  "completion_tokens",
  "cost",
  "ai_cost",
  "estimated_cost_usd",
  "input_tokens",
  "internal_prompt",
  "internal_validation",
  "model",
  "model_name",
  "output_tokens",
  "private_prompt",
  "prompt",
  "provider",
  "provider_id",
  "raw_ai_response",
  "research_package",
  "routing",
  "routing_reason",
  "routing_reasons",
  "routing_tier",
  "secret",
  "system_prompt",
  "token_count",
  "tokens",
  "tool_calls",
  "tool_internals",
  "tool_results",
  "access_token",
  "refresh_token",
  "client_secret",
  "authorization",
  "auth_header",
  "raw_http_response",
  "raw_authenticated_http_response",
]);

export type CanonicalMoatDimensionView = {
  identifier: CanonicalMoatDimensionId;
  name: string;
  presentationRatingStatus: PresentationRatingStatus;
  engineStatus: string;
  displayRating: string;
  canonicalScore100: number | null;
};

export type CanonicalMoatDimensionsMapping = {
  dimensions: CanonicalMoatDimensionView[];
  rejectedUnknownIdentifiers: string[];
};

function isCanonicalId(value: string): value is CanonicalMoatDimensionId {
  return (CANONICAL_MOAT_DIMENSION_IDS as readonly string[]).includes(value);
}

function normalizeStatus(value: unknown): PresentationRatingStatus {
  if (
    typeof value === "string" &&
    (PRESENTATION_RATING_STATUSES as readonly string[]).includes(value)
  ) {
    return value as PresentationRatingStatus;
  }
  return "unavailable";
}

function unavailableRow(
  identifier: CanonicalMoatDimensionId,
): CanonicalMoatDimensionView {
  return {
    identifier,
    name: CANONICAL_MOAT_DISPLAY_NAMES[identifier],
    presentationRatingStatus: "unavailable",
    engineStatus: "unavailable",
    displayRating: MOAT_RATING_UNAVAILABLE_DISPLAY,
    canonicalScore100: null,
  };
}

function displayRatingFromContract(
  status: PresentationRatingStatus,
  presentationRating10: unknown,
): string {
  if (status !== "assessed") {
    return MOAT_RATING_UNAVAILABLE_DISPLAY;
  }
  if (typeof presentationRating10 !== "string") {
    return MOAT_RATING_UNAVAILABLE_DISPLAY;
  }
  const trimmed = presentationRating10.trim();
  if (trimmed === "") {
    return MOAT_RATING_UNAVAILABLE_DISPLAY;
  }
  return trimmed;
}

function projectRow(
  identifier: CanonicalMoatDimensionId,
  raw: Record<string, unknown>,
): CanonicalMoatDimensionView {
  const status = normalizeStatus(raw.presentation_rating_status);
  const score =
    typeof raw.canonical_score_100 === "number" &&
    Number.isFinite(raw.canonical_score_100)
      ? raw.canonical_score_100
      : null;
  return {
    identifier,
    name: CANONICAL_MOAT_DISPLAY_NAMES[identifier],
    presentationRatingStatus: status,
    engineStatus:
      typeof raw.engine_status === "string" && raw.engine_status.trim() !== ""
        ? raw.engine_status
        : "unavailable",
    displayRating: displayRatingFromContract(
      status,
      raw.presentation_rating_10,
    ),
    canonicalScore100: score,
  };
}

function asObjectRows(raw: unknown): Record<string, unknown>[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter(
    (item): item is Record<string, unknown> =>
      item !== null && typeof item === "object" && !Array.isArray(item),
  );
}

/** Index DSP `economic_moat_dimensions` without creating a second taxonomy. */
export function mapCanonicalMoatDimensions(
  raw: unknown,
): CanonicalMoatDimensionsMapping {
  const rows = asObjectRows(raw);
  const byId = new Map<CanonicalMoatDimensionId, Record<string, unknown>>();
  const rejectedUnknownIdentifiers: string[] = [];

  for (const row of rows) {
    const identifier =
      typeof row.identifier === "string" ? row.identifier : "";
    if (!isCanonicalId(identifier)) {
      if (identifier) rejectedUnknownIdentifiers.push(identifier);
      continue;
    }
    if (!byId.has(identifier)) {
      byId.set(identifier, row);
    }
  }

  const dimensions = CANONICAL_MOAT_DIMENSION_IDS.map((id) => {
    const row = byId.get(id);
    return row ? projectRow(id, row) : unavailableRow(id);
  });

  return { dimensions, rejectedUnknownIdentifiers };
}

export function collectViewKeys(
  dimensions: CanonicalMoatDimensionView[],
): string[] {
  const keys = new Set<string>();
  for (const row of dimensions) {
    for (const key of Object.keys(row)) keys.add(key);
  }
  return [...keys].sort();
}

export function privateFieldsPresentIn(value: unknown): string[] {
  const found = new Set<string>();
  const walk = (node: unknown): void => {
    if (!node || typeof node !== "object") return;
    if (Array.isArray(node)) {
      for (const item of node) walk(item);
      return;
    }
    for (const [key, child] of Object.entries(node)) {
      if (PRIVATE_UI_FIELD_NAMES.has(key)) found.add(key);
      walk(child);
    }
  };
  walk(value);
  return [...found].sort();
}
