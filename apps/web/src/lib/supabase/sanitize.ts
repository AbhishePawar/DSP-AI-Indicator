/** Strip secrets, prompts, and provider internals before persistence. */

export const FORBIDDEN_PERSISTENCE_KEYS = new Set([
  "api_key",
  "apikey",
  "authorization",
  "bearer",
  "chain_of_thought",
  "client_secret",
  "cost",
  "cost_usd",
  "input_tokens",
  "output_tokens",
  "private_prompt",
  "prompt_parts",
  "provider_routing",
  "service_role",
  "system_instruction",
  "token_count",
  "tokens",
]);

const FORBIDDEN_SUBSTRINGS = [
  "api_key",
  "chain_of_thought",
  "private_prompt",
  "service_role",
  "provider_routing",
];

function isForbiddenKey(key: string): boolean {
  const lower = key.toLowerCase();
  if (FORBIDDEN_PERSISTENCE_KEYS.has(lower)) return true;
  return FORBIDDEN_SUBSTRINGS.some((needle) => lower.includes(needle));
}

export function sanitizeForPersistence(value: unknown, depth = 0): unknown {
  if (depth > 8) return undefined;
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) {
    return value
      .map((item) => sanitizeForPersistence(item, depth + 1))
      .filter((item) => item !== undefined);
  }
  const out: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    if (isForbiddenKey(key)) continue;
    const next = sanitizeForPersistence(item, depth + 1);
    if (next !== undefined) out[key] = next;
  }
  return out;
}

export type PublicSavedResearch = {
  id: string;
  ticker: string;
  company: string;
  exchange: string;
  analysisId: string | null;
  label: string | null;
  researchStatus: string | null;
  recommendationAction: string | null;
  analysedAt: string | null;
  savedAt: string;
  publicReport: Record<string, unknown>;
};

export function toPublicSavedResearch(input: {
  id: string;
  ticker: string;
  company?: string;
  exchange?: string;
  analysisId?: string | null;
  label?: string | null;
  researchStatus?: string | null;
  recommendation?: string | null;
  analysedAt?: string | null;
  savedAt: string;
  request?: unknown;
  response?: unknown;
}): PublicSavedResearch {
  const publicReport = sanitizeForPersistence({
    analysis_id: input.analysisId ?? null,
    ticker: input.ticker,
    company: input.company ?? "",
    exchange: input.exchange ?? "",
    recommendation_action: input.recommendation ?? null,
    analysed_at: input.analysedAt ?? null,
    request_ticker:
      input.request && typeof input.request === "object"
        ? (input.request as { ticker?: string }).ticker ?? input.ticker
        : input.ticker,
    response: input.response ?? null,
  }) as Record<string, unknown>;

  return {
    id: input.id,
    ticker: input.ticker.trim().toUpperCase(),
    company: input.company ?? "",
    exchange: input.exchange ?? "",
    analysisId: input.analysisId ?? null,
    label: input.label ?? null,
    researchStatus: input.researchStatus ?? null,
    recommendationAction: input.recommendation ?? null,
    analysedAt: input.analysedAt ?? null,
    savedAt: input.savedAt,
    publicReport,
  };
}
