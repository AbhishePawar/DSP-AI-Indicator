import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { readSupabasePublicConfig } from "./publicConfig";

function requireServerRuntime(): void {
  if (typeof window !== "undefined") {
    throw new Error("Supabase admin client is server-only");
  }
}

export function readSupabaseServiceRoleKey(
  env: NodeJS.ProcessEnv = process.env,
): string | null {
  requireServerRuntime();
  const key = (env.SUPABASE_SERVICE_ROLE_KEY ?? "").trim();
  if (!key) return null;
  if (key === (env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "").trim()) return null;
  return key;
}

export function getSupabaseAdminClient(): SupabaseClient | null {
  requireServerRuntime();
  const publicConfig = readSupabasePublicConfig();
  const serviceKey = readSupabaseServiceRoleKey();
  if (!publicConfig || !serviceKey) return null;
  return createClient(publicConfig.url, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

export function isSupabaseServerConfigured(): boolean {
  return getSupabaseAdminClient() !== null;
}
