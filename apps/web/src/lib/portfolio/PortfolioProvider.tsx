"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/lib/auth/AuthProvider";
import {
  addHoldingToView,
  createActivity,
  getDemoPortfolio,
  getEmptyPortfolio,
  hasHolding,
  removeHoldingFromView,
} from "@/lib/portfolio/data";
import type {
  AddHoldingInput,
  PortfolioHolding,
  PortfolioView,
} from "@/lib/portfolio/model";
import { usePersistence } from "@/providers/PersistenceProvider";

type PortfolioContextValue = {
  view: PortfolioView;
  holdings: PortfolioHolding[];
  isEmpty: boolean;
  hasTicker: (ticker: string) => boolean;
  addHolding: (input: AddHoldingInput) => boolean;
  removeHolding: (ticker: string) => boolean;
  recordResearchOpened: (companyOrTicker: string) => void;
  loadDemo: () => void;
  clearPortfolio: () => void;
};

const PortfolioContext = createContext<PortfolioContextValue | null>(null);

export function PortfolioProvider({ children }: { children: ReactNode }) {
  const { status, session } = useAuth();
  const { portfolioView, persistPortfolio, isLoaded } = usePersistence();
  const [view, setView] = useState<PortfolioView>(() => getEmptyPortfolio());
  const skipPersist = useRef(false);

  useEffect(() => {
    if (!isLoaded) return;
    skipPersist.current = true;
    if (status === "authenticated" && portfolioView) {
      setView(portfolioView);
    } else if (status !== "authenticated") {
      setView(getEmptyPortfolio());
    }
    window.setTimeout(() => {
      skipPersist.current = false;
    }, 0);
    // Hydrate on auth subject change — not on every persisted update.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, status, session?.subject]);

  useEffect(() => {
    if (skipPersist.current) return;
    if (status !== "authenticated") return;
    persistPortfolio(view);
  }, [view, status, persistPortfolio]);

  const hasTicker = useCallback(
    (ticker: string) => hasHolding(view.holdings, ticker),
    [view.holdings],
  );

  const addHolding = useCallback((input: AddHoldingInput): boolean => {
    let didAdd = false;
    setView((current) => {
      const next = addHoldingToView(current, input);
      if (!next) return current;
      didAdd = true;
      return next;
    });
    return didAdd;
  }, []);

  const removeHolding = useCallback((ticker: string): boolean => {
    let didRemove = false;
    setView((current) => {
      const next = removeHoldingFromView(current, ticker);
      if (!next) return current;
      didRemove = true;
      return next;
    });
    return didRemove;
  }, []);

  const recordResearchOpened = useCallback((companyOrTicker: string) => {
    setView((current) => ({
      ...current,
      activities: [
        createActivity(`Opened Research · ${companyOrTicker}`),
        ...current.activities,
      ].slice(0, 50),
    }));
  }, []);

  const loadDemo = useCallback(() => {
    setView(getDemoPortfolio());
  }, []);

  const clearPortfolio = useCallback(() => {
    setView(getEmptyPortfolio());
  }, []);

  const value = useMemo<PortfolioContextValue>(
    () => ({
      view,
      holdings: view.holdings,
      isEmpty: view.holdings.length === 0,
      hasTicker,
      addHolding,
      removeHolding,
      recordResearchOpened,
      loadDemo,
      clearPortfolio,
    }),
    [
      view,
      hasTicker,
      addHolding,
      removeHolding,
      recordResearchOpened,
      loadDemo,
      clearPortfolio,
    ],
  );

  return (
    <PortfolioContext.Provider value={value}>
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolio(): PortfolioContextValue {
  const ctx = useContext(PortfolioContext);
  if (!ctx) {
    throw new Error("usePortfolio must be used within PortfolioProvider");
  }
  return ctx;
}
