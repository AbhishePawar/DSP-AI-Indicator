"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { readSupabasePublicConfig } from "./publicConfig";

let browserClient: SupabaseClient | null = null;

export function getBrowserSupabaseClient(): SupabaseClient | null {
  const config = readSupabasePublicConfig();
  if (!config) return null;
  if (typeof window === "undefined") return null;
  if (!browserClient) {
    browserClient = createClient(config.url, config.anonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: false,
        storageKey: "dsp.supabase.auth.v1",
      },
    });
  }
  return browserClient;
}

export function _resetBrowserSupabaseClient(): void {
  browserClient = null;
}
