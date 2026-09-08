"use client";

import { createClient } from "@/lib/supabase/client";

export interface OnboardingState {
  completed: boolean;
  skipped: boolean;
  lastStepSeen: number;
}

const LOCAL_KEY = "dsp.onboarding.v2";

function readLocal(): OnboardingState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(LOCAL_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as OnboardingState;
  } catch {
    return null;
  }
}

function writeLocal(state: OnboardingState) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LOCAL_KEY, JSON.stringify(state));
  } catch {
    /* quota */
  }
}

export async function getOnboardingState(userId: string): Promise<OnboardingState> {
  try {
    const supabase = createClient();
    const { data, error } = await supabase
      .from("user_onboarding_state")
      .select("completed, skipped, last_step_seen")
      .eq("user_id", userId)
      .maybeSingle();

    if (error) throw error;

    if (data) {
      const state: OnboardingState = {
        completed: data.completed,
        skipped: data.skipped,
        lastStepSeen: data.last_step_seen,
      };
      writeLocal(state);
      return state;
    }

    // No row yet — new user, show onboarding
    return { completed: false, skipped: false, lastStepSeen: 0 };
  } catch {
    // Fallback to localStorage if Supabase unavailable
    return readLocal() ?? { completed: false, skipped: false, lastStepSeen: 0 };
  }
}

export async function upsertOnboardingState(
  userId: string,
  patch: Partial<OnboardingState>,
): Promise<void> {
  const now = new Date().toISOString();
  const row: Record<string, unknown> = {
    user_id: userId,
    updated_at: now,
  };

  if (patch.completed !== undefined) {
    row.completed = patch.completed;
    if (patch.completed) row.completed_at = now;
  }
  if (patch.skipped !== undefined) {
    row.skipped = patch.skipped;
    if (patch.skipped) row.skipped_at = now;
  }
  if (patch.lastStepSeen !== undefined) {
    row.last_step_seen = patch.lastStepSeen;
  }

  // Optimistic local update
  const current = readLocal() ?? { completed: false, skipped: false, lastStepSeen: 0 };
  writeLocal({ ...current, ...patch });

  try {
    const supabase = createClient();
    await supabase
      .from("user_onboarding_state")
      .upsert(row, { onConflict: "user_id" });
  } catch {
    /* silently fail — local state already updated */
  }
}
