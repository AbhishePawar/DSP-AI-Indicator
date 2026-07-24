"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname } from "next/navigation";

import {
  getOnboardingState,
  setOnboardingState,
  trackPageVisit,
  trackTimeOnPage,
  type FeedbackCategory,
  type FeedbackSeverity,
} from "@/lib/beta/betaModel";

type FeedbackContextValue = {
  dialogOpen: boolean;
  openFeedback: (opts?: { sectionId?: string | null; category?: FeedbackCategory }) => void;
  closeFeedback: () => void;
  sectionId: string | null;
  presetCategory: FeedbackCategory | null;
  presetSeverity: FeedbackSeverity | null;
  tourOpen: boolean;
  tourStep: number;
  startTour: () => void;
  skipTour: () => void;
  nextTourStep: () => void;
  prevTourStep: () => void;
  restartTour: () => void;
  refreshTick: number;
  bumpRefresh: () => void;
};

const FeedbackContext = createContext<FeedbackContextValue | null>(null);

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [sectionId, setSectionId] = useState<string | null>(null);
  const [presetCategory, setPresetCategory] = useState<FeedbackCategory | null>(null);
  const [tourOpen, setTourOpen] = useState(false);
  const [tourStep, setTourStep] = useState(0);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    if (pathname === "/login") return;
    trackPageVisit(pathname);
    const started = Date.now();
    return () => {
      trackTimeOnPage(pathname, Date.now() - started);
    };
  }, [pathname]);

  useEffect(() => {
    const state = getOnboardingState();
    if (!state.completed && pathname !== "/login") {
      setTourOpen(true);
      setTourStep(state.step || 0);
    }
  }, [pathname]);

  const openFeedback = useCallback(
    (opts?: { sectionId?: string | null; category?: FeedbackCategory }) => {
      setSectionId(opts?.sectionId ?? null);
      setPresetCategory(opts?.category ?? null);
      setDialogOpen(true);
    },
    [],
  );

  const closeFeedback = useCallback(() => setDialogOpen(false), []);

  const skipTour = useCallback(() => {
    setOnboardingState({ completed: true, step: 0 });
    setTourOpen(false);
  }, []);

  const startTour = useCallback(() => {
    setOnboardingState({ completed: false, step: 0 });
    setTourStep(0);
    setTourOpen(true);
  }, []);

  const restartTour = startTour;

  const nextTourStep = useCallback(() => {
    setTourStep((s) => {
      const next = s + 1;
      setOnboardingState({ completed: false, step: next });
      return next;
    });
  }, []);

  const prevTourStep = useCallback(() => {
    setTourStep((s) => Math.max(0, s - 1));
  }, []);

  const bumpRefresh = useCallback(() => setRefreshTick((n) => n + 1), []);

  const value = useMemo(
    () => ({
      dialogOpen,
      openFeedback,
      closeFeedback,
      sectionId,
      presetCategory,
      presetSeverity: null as FeedbackSeverity | null,
      tourOpen,
      tourStep,
      startTour,
      skipTour,
      nextTourStep,
      prevTourStep,
      restartTour,
      refreshTick,
      bumpRefresh,
    }),
    [
      dialogOpen,
      openFeedback,
      closeFeedback,
      sectionId,
      presetCategory,
      tourOpen,
      tourStep,
      startTour,
      skipTour,
      nextTourStep,
      prevTourStep,
      restartTour,
      refreshTick,
      bumpRefresh,
    ],
  );

  return (
    <FeedbackContext.Provider value={value}>{children}</FeedbackContext.Provider>
  );
}

export function useFeedback(): FeedbackContextValue {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error("useFeedback requires FeedbackProvider");
  return ctx;
}

export function useFeedbackOptional(): FeedbackContextValue | null {
  return useContext(FeedbackContext);
}
