"use client";

import { FeedbackButton, FeedbackDialog } from "@/components/beta/FeedbackDialog";
import { OnboardingOverlay } from "@/components/beta/OnboardingOverlay";

/** Shell widgets for Private Beta — mount inside FeedbackProvider. */
export function BetaShellWidgets() {
  return (
    <>
      <FeedbackButton />
      <FeedbackDialog />
      <OnboardingOverlay />
    </>
  );
}
