/** Browser-safe Supabase public configuration. Never includes service-role keys. */

export type SupabasePublicConfig = {
  url: string;
  anonKey: string;
};

function trimEnv(value: string | undefined): string {
  return (value ?? "").trim();
}

export function readSupabasePublicConfig(
  env: NodeJS.ProcessEnv = process.env,
): SupabasePublicConfig | null {
  const url = trimEnv(env.NEXT_PUBLIC_SUPABASE_URL);
  const anonKey = trimEnv(env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
  if (!url || !anonKey) return null;
  if (!url.startsWith("https://") && !url.startsWith("http://localhost")) {
    return null;
  }
  if (anonKey.toLowerCase().includes("service_role")) {
    return null;
  }
  return { url, anonKey };
}

export function isSupabaseBrowserConfigured(): boolean {
  return readSupabasePublicConfig() !== null;
}

export const SUPABASE_PUBLIC_ENV_NAMES = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_ANON_KEY",
] as const;

export const SUPABASE_SERVER_ONLY_ENV_NAMES = [
  "SUPABASE_SERVICE_ROLE_KEY",
  "SUPABASE_JWT_SECRET",
] as const;
