import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  dspSubjectToProfileId,
  dspSubjectToProfileIdSync,
} from "./identity";
import {
  readSupabasePublicConfig,
  SUPABASE_PUBLIC_ENV_NAMES,
  SUPABASE_SERVER_ONLY_ENV_NAMES,
} from "./publicConfig";
import {
  FORBIDDEN_PERSISTENCE_KEYS,
  sanitizeForPersistence,
  toPublicSavedResearch,
} from "./sanitize";

function readMigration(): string {
  const candidates = [
    path.resolve(process.cwd(), "supabase/migrations/20260903120000_application_infrastructure.sql"),
    path.resolve(process.cwd(), "../../supabase/migrations/20260903120000_application_infrastructure.sql"),
    path.resolve(__dirname, "../../../../../supabase/migrations/20260903120000_application_infrastructure.sql"),
  ];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return readFileSync(candidate, "utf8");
  }
  throw new Error("Supabase application migration not found");
}


describe("supabase public config", () => {
  it("requires url and anon key", () => {
    expect(readSupabasePublicConfig({})).toBeNull();
  });

  it("rejects service-role material in the public anon key", () => {
    expect(
      readSupabasePublicConfig({
        NEXT_PUBLIC_SUPABASE_URL: "https://example.supabase.co",
        NEXT_PUBLIC_SUPABASE_ANON_KEY: "service_role-secret",
      }),
    ).toBeNull();
  });

  it("accepts https project url with a non-service anon key", () => {
    const config = readSupabasePublicConfig({
      NEXT_PUBLIC_SUPABASE_URL: "https://example.supabase.co",
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.anon",
    });
    expect(config?.url).toBe("https://example.supabase.co");
  });

  it("does not publish server-only env names as public", () => {
    for (const name of SUPABASE_SERVER_ONLY_ENV_NAMES) {
      expect(name.startsWith("NEXT_PUBLIC_")).toBe(false);
      expect(SUPABASE_PUBLIC_ENV_NAMES).not.toContain(name);
    }
  });
});

describe("persistence sanitizer", () => {
  it("strips prompts, tokens, costs, and provider routing", () => {
    const cleaned = sanitizeForPersistence({
      ticker: "DSPX",
      private_prompt: "secret methodology",
      prompt_parts: ["do not store"],
      chain_of_thought: "hidden",
      api_key: "sk-live",
      provider_routing: { model: "hidden" },
      token_count: 99,
      cost_usd: 1.23,
      recommendation_action: "Hold",
    }) as Record<string, unknown>;
    expect(cleaned.ticker).toBe("DSPX");
    expect(cleaned.recommendation_action).toBe("Hold");
    for (const key of FORBIDDEN_PERSISTENCE_KEYS) {
      expect(cleaned).not.toHaveProperty(key);
    }
  });

  it("stores public saved-research metadata without inventing share counts", () => {
    const saved = toPublicSavedResearch({
      id: "saved-1",
      ticker: "dspx",
      company: "DSP Test",
      exchange: "TESTEX",
      recommendation: "Unable to calculate.",
      analysedAt: "2026-09-03T00:00:00.000Z",
      savedAt: "2026-09-03T01:00:00.000Z",
      request: { ticker: "DSPX", private_prompt: "nope" },
      response: { ok: true, prompt_parts: ["nope"] },
    });
    expect(saved.ticker).toBe("DSPX");
    expect(JSON.stringify(saved.publicReport)).not.toMatch(/private_prompt/);
    expect(JSON.stringify(saved.publicReport)).not.toMatch(/prompt_parts/);
    expect(saved.publicReport).not.toHaveProperty("current_outstanding");
  });
});

describe("dsp subject identity", () => {
  it("maps the same DSP subject to the same profile id", async () => {
    const a = await dspSubjectToProfileId("user-1");
    const b = dspSubjectToProfileIdSync("user-1");
    expect(a).toBe(b);
    expect(a).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });
});

describe("supabase schema architecture", () => {
  const sql = readMigration();

  it("enables RLS on user-owned tables", () => {
    expect(sql).toContain("enable row level security");
    expect(sql).toContain("profiles_own");
    expect(sql).toContain("saved_research_own");
    expect(sql).toContain("watchlists_own");
  });

  it("does not implement DSP intelligence in SQL", () => {
    const uncommented = sql.replace(/--.*$/gm, "");
    expect(uncommented).not.toMatch(/intrinsic_value/i);
    expect(uncommented).not.toMatch(/share_count/i);
    expect(uncommented).not.toMatch(/current_outstanding/i);
    expect(uncommented).not.toMatch(/margin_of_safety/i);
    expect(uncommented).not.toMatch(/gemini|openai|perplexity/i);
    expect(uncommented).not.toMatch(/\bdcf\b/i);
  });

  it("keeps the user-documents bucket private", () => {
    expect(sql).toContain("user-documents");
    expect(sql).toMatch(/'user-documents',\s+false/);
  });
});
