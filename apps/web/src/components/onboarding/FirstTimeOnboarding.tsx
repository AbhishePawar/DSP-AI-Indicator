"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Bell,
  Bookmark,
  Building2,
  Briefcase,
  X,
  ArrowRight,
  ArrowLeft,
  CheckCircle,
} from "lucide-react";

import { useAuth } from "@/lib/auth/AuthProvider";
import { upsertOnboardingState } from "@/lib/onboarding/onboardingService";

interface OnboardingStep {
  id: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  highlight: string;
  href: string;
  linkLabel: string;
  accentClass: string;
  bgClass: string;
}

const STEPS: OnboardingStep[] = [
  {
    id: "alerts",
    icon: <Bell className="h-7 w-7" />,
    title: "Smart Alerts",
    description:
      "Set threshold-based alerts on any metric — price, P/E, revenue growth, and more. Get notified the moment a company crosses your criteria.",
    highlight: "Never miss a signal that matters to your research.",
    href: "/alerts",
    linkLabel: "Go to Alerts →",
    accentClass: "text-amber-400",
    bgClass: "bg-amber-500/10 border-amber-500/20",
  },
  {
    id: "watchlists",
    icon: <Bookmark className="h-7 w-7" />,
    title: "Watchlists",
    description:
      "Organise tickers into named watchlists and track their performance with sparklines. Add, remove, and manage tickers in seconds.",
    highlight: "Keep your research universe organised and at a glance.",
    href: "/watchlists",
    linkLabel: "Go to Watchlists →",
    accentClass: "text-blue-400",
    bgClass: "bg-blue-500/10 border-blue-500/20",
  },
  {
    id: "company-research",
    icon: <Building2 className="h-7 w-7" />,
    title: "Company Research",
    description:
      "Deep-dive into any company with tabbed research covering valuation, financials, economic moat, quality, risk, and investment recommendations.",
    highlight: "Institutional-grade analysis for every ticker you cover.",
    href: "/company-research",
    linkLabel: "Go to Company Research →",
    accentClass: "text-emerald-400",
    bgClass: "bg-emerald-500/10 border-emerald-500/20",
  },
  {
    id: "portfolio",
    icon: <Briefcase className="h-7 w-7" />,
    title: "Portfolio",
    description:
      "Track your holdings, monitor allocation, and get AI-powered portfolio intelligence including diversification analysis and rebalancing insights.",
    highlight: "Turn your holdings into actionable portfolio intelligence.",
    href: "/portfolio",
    linkLabel: "Go to Portfolio →",
    accentClass: "text-violet-400",
    bgClass: "bg-violet-500/10 border-violet-500/20",
  },
];

interface Props {
  onDismiss: () => void;
}

export function FirstTimeOnboarding({ onDismiss }: Props) {
  const [step, setStep] = useState(0);
  const [exiting, setExiting] = useState(false);
  const { session } = useAuth();
  const overlayRef = useRef<HTMLDivElement>(null);

  const userId = session?.subject ?? null;

  const dismiss = useCallback(
    async (opts: { completed?: boolean; skipped?: boolean } = {}) => {
      setExiting(true);
      if (userId) {
        await upsertOnboardingState(userId, {
          completed: opts.completed ?? false,
          skipped: opts.skipped ?? false,
          lastStepSeen: step,
        });
      }
      setTimeout(() => {
        onDismiss();
      }, 200);
    },
    [userId, step, onDismiss],
  );

  const handleFinish = useCallback(() => {
    dismiss({ completed: true });
  }, [dismiss]);

  const handleSkip = useCallback(() => {
    dismiss({ skipped: true });
  }, [dismiss]);

  const handleNext = useCallback(async () => {
    if (step < STEPS.length - 1) {
      const next = step + 1;
      setStep(next);
      if (userId) {
        await upsertOnboardingState(userId, { lastStepSeen: next });
      }
    } else {
      handleFinish();
    }
  }, [step, userId, handleFinish]);

  const handlePrev = useCallback(() => {
    setStep((s) => Math.max(0, s - 1));
  }, []);

  // Trap focus inside overlay
  useEffect(() => {
    const el = overlayRef.current;
    if (!el) return;
    const focusable = el.querySelectorAll<HTMLElement>(
      "button, a[href], [tabindex]:not([tabIndex='-1'])",
    );
    focusable[0]?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleSkip();
      if (e.key === "ArrowRight") handleNext();
      if (e.key === "ArrowLeft") handlePrev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleSkip, handleNext, handlePrev]);

  const current = STEPS[step]!;
  const isLast = step === STEPS.length - 1;

  return (
    <div
      className={`fixed inset-0 z-[70] flex items-center justify-center p-4 transition-opacity duration-200 ${
        exiting ? "opacity-0" : "opacity-100"
      }`}
      role="dialog"
      aria-modal="true"
      aria-label="Welcome walkthrough"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleSkip}
        aria-hidden="true"
      />

      {/* Card */}
      <div
        ref={overlayRef}
        className="relative z-10 w-full max-w-lg rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[var(--fg)]">
              Getting started
            </span>
            <span className="rounded-full bg-[var(--accent)]/10 px-2 py-0.5 text-xs font-semibold text-[var(--accent)]">
              {step + 1} / {STEPS.length}
            </span>
          </div>
          <button
            type="button"
            onClick={handleSkip}
            className="rounded-lg p-1.5 text-[var(--muted)] transition-colors hover:bg-[var(--border)] hover:text-[var(--fg)]"
            aria-label="Skip walkthrough"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Wave 3: Progress label + bar above step dots */}
        <div className="px-6 pt-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs text-[var(--muted)]">
              Step {step + 1} of {STEPS.length}
            </span>
            <span className="text-xs font-medium text-[var(--accent)]">
              {Math.round(((step + 1) / STEPS.length) * 100)}% complete
            </span>
          </div>
          <div
            className="h-1 w-full overflow-hidden rounded-full bg-[var(--border)]"
            role="progressbar"
            aria-valuenow={step + 1}
            aria-valuemin={1}
            aria-valuemax={STEPS.length}
            aria-label={`Onboarding progress: step ${step + 1} of ${STEPS.length}`}
          >
            <div
              className="h-full rounded-full bg-[var(--accent)] transition-all duration-300"
              style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Step indicator dots */}
        <div className="flex justify-center gap-2 px-6 pt-3">
          {STEPS.map((s, i) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setStep(i)}
              aria-label={`Go to step ${i + 1}: ${s.title}`}
              className={`h-2 rounded-full transition-all duration-200 ${
                i === step
                  ? "w-6 bg-[var(--accent)]"
                  : i < step
                  ? "w-2 bg-[var(--accent)]/40"
                  : "w-2 bg-[var(--border)]"
              }`}
            />
          ))}
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          {/* Icon + title */}
          <div
            className={`mb-4 inline-flex items-center gap-3 rounded-xl border p-3 ${current.bgClass} ${current.accentClass}`}
          >
            {current.icon}
            <h2 className="text-lg font-semibold text-[var(--fg)]">
              {current.title}
            </h2>
          </div>

          {/* Description */}
          <p className="text-sm leading-relaxed text-[var(--muted)]">
            {current.description}
          </p>

          {/* Highlight callout */}
          <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-4 py-3">
            <p className={`text-sm font-medium ${current.accentClass}`}>
              {current.highlight}
            </p>
          </div>

          {/* Feature link */}
          <div className="mt-4">
            <Link
              href={current.href}
              onClick={() => dismiss({ completed: false, skipped: true })}
              className={`inline-flex items-center gap-1 text-sm font-medium underline-offset-2 hover:underline ${current.accentClass}`}
            >
              {current.linkLabel}
            </Link>
          </div>
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between border-t border-[var(--border)] px-6 py-4">
          <button
            type="button"
            onClick={handleSkip}
            className="text-sm text-[var(--muted)] transition-colors hover:text-[var(--fg)]"
          >
            Skip tour
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrev}
              disabled={step === 0}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm font-medium text-[var(--fg)] transition-colors hover:bg-[var(--border)] disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back
            </button>

            {isLast ? (
              <button
                type="button"
                onClick={handleFinish}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-4 py-1.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
              >
                <CheckCircle className="h-4 w-4" />
                Get started
              </button>
            ) : (
              <button
                type="button"
                onClick={handleNext}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-4 py-1.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
              >
                Next
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
