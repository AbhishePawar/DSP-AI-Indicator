"use client";

import { useFeedback } from "@/components/beta/FeedbackContext";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { TUTORIAL_STEPS } from "@/lib/beta/onboardingSteps";
import { setOnboardingState, trackFeature } from "@/lib/beta/betaModel";

export function TutorialStep({
  title,
  body,
  index,
  total,
}: {
  title: string;
  body: string;
  index: number;
  total: number;
}) {
  return (
    <div>
      <p className="text-xs text-[var(--muted)]">
        Step {index + 1} of {total}
      </p>
      <h2 className="mt-1 font-[family-name:var(--font-display)] text-xl">{title}</h2>
      <p className="mt-2 text-sm text-[var(--muted)]">{body}</p>
    </div>
  );
}

export function OnboardingOverlay() {
  const {
    tourOpen,
    tourStep,
    skipTour,
    nextTourStep,
    prevTourStep,
    restartTour,
  } = useFeedback();

  if (!tourOpen) return null;

  const step = TUTORIAL_STEPS[Math.min(tourStep, TUTORIAL_STEPS.length - 1)];
  const isLast = tourStep >= TUTORIAL_STEPS.length - 1;

  const finish = () => {
    setOnboardingState({ completed: true, step: 0 });
    trackFeature("onboarding_complete");
    skipTour();
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-end justify-center bg-black/50 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-label="Welcome tour"
    >
      <Card className="w-full max-w-md">
        <CardHeader
          title="Interactive walkthrough"
          action={
            <Button variant="ghost" size="sm" onClick={skipTour}>
              Skip tutorial
            </Button>
          }
        />
        <CardBody className="space-y-4">
          <TutorialStep
            title={step.title}
            body={step.body}
            index={Math.min(tourStep, TUTORIAL_STEPS.length - 1)}
            total={TUTORIAL_STEPS.length}
          />
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={prevTourStep} disabled={tourStep === 0}>
              Back
            </Button>
            {isLast ? (
              <Button onClick={finish}>Finish</Button>
            ) : (
              <Button
                onClick={() => {
                  trackFeature("onboarding_step");
                  nextTourStep();
                }}
              >
                Next
              </Button>
            )}
            <Button variant="ghost" onClick={restartTour}>
              Restart tutorial
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
