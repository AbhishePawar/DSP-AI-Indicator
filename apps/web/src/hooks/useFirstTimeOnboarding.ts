"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { getOnboardingState } from "@/lib/onboarding/onboardingService";

export function useFirstTimeOnboarding() {
  const { session, status } = useAuth();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (status !== "authenticated" || !session?.subject || checked) return;

    let cancelled = false;
    setChecked(true);

    getOnboardingState(session?.subject)?.then((state) => {
      if (cancelled) return;
      if (!state?.completed && !state?.skipped) {
        setShowOnboarding(true);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [status, session?.subject, checked]);

  const dismiss = useCallback(() => {
    setShowOnboarding(false);
  }, []);

  return { showOnboarding, dismiss };
}
