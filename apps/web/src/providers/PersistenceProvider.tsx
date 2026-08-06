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
import { logger } from "@/lib/observability/logger";
import { buildPortfolioView } from "@/lib/portfolio/data";
import type { PortfolioView } from "@/lib/portfolio/model";
import {
  fetchDefaultPortfolio,
  fetchHoldings,
  migrateLocalPortfolio,
  syncHoldings,
} from "@/lib/portfolio/repository";
import type { CopilotConversation } from "@/lib/copilot/types";
import { saveResearchSession } from "@/lib/research/sessionStore";
import type { ThemeMode } from "@/providers/ThemeProvider";
import { useTheme } from "@/providers/ThemeProvider";
import {
  createEmptyUserData,
  createSavedAnalysisId,
  portfolioViewFromUserPortfolio,
  readUserData,
  sortSavedAnalyses,
  toSavedConversation,
  userPortfolioFromView,
  writeUserData,
} from "@/lib/persistence";
import type {
  SavedAnalysis,
  SavedConversation,
  SyncStatus,
  UserDataBundle,
  UserPreference,
} from "@/lib/persistence/types";
import { DEFAULT_PREFERENCES } from "@/lib/persistence/types";

/** RC1 Milestone 3 — Portfolio server-sync status (additive; local-only
 * consumers of `usePersistence()` can ignore these fields entirely). */
export type PortfolioSyncStatus = "idle" | "syncing" | "synced" | "error";

type PersistenceContextValue = {
  syncStatus: SyncStatus;
  lastSyncedAt: string | null;
  lastError: string | null;
  isLoaded: boolean;
  bundle: UserDataBundle | null;
  savedAnalyses: SavedAnalysis[];
  copilotConversations: SavedConversation[];
  preferences: UserPreference;
  portfolioView: PortfolioView | null;
  persistPortfolio: (view: PortfolioView) => void;
  saveAnalysis: (input: Omit<SavedAnalysis, "id" | "savedAt">) => SavedAnalysis | null;
  deleteSavedAnalysis: (id: string) => void;
  reopenSavedAnalysis: (id: string) => boolean;
  persistCopilotConversations: (conversations: CopilotConversation[]) => void;
  updatePreferences: (patch: Partial<UserPreference>) => void;
  syncNow: () => Promise<void>;
  /** Server-side portfolio id once migrated/loaded — null while local-only. */
  serverPortfolioId: string | null;
  /** Benchmark symbol observed on the server portfolio at load/migration time
   * — a one-shot reconciliation hint for `usePortfolioIntelPrefsStore`,
   * which owns ongoing benchmark/watchlist state (different domain). */
  serverBenchmarkSymbol: string | null;
  portfolioSyncStatus: PortfolioSyncStatus;
  portfolioSyncError: string | null;
};

const PersistenceContext = createContext<PersistenceContextValue | null>(null);

const SAVE_DEBOUNCE_MS = 400;

export function PersistenceProvider({ children }: { children: ReactNode }) {
  const { status, session } = useAuth();
  const { setMode } = useTheme();
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("idle");
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [bundle, setBundle] = useState<UserDataBundle | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const preferencesApplied = useRef(false);

  // RC1 Milestone 3 — server-side Portfolio persistence.
  const [serverPortfolioId, setServerPortfolioId] = useState<string | null>(null);
  const [serverBenchmarkSymbol, setServerBenchmarkSymbol] = useState<string | null>(
    null,
  );
  const [portfolioSyncStatus, setPortfolioSyncStatus] =
    useState<PortfolioSyncStatus>("idle");
  const [portfolioSyncError, setPortfolioSyncError] = useState<string | null>(null);
  const knownServerSymbols = useRef<string[]>([]);
  const migrationAttemptedFor = useRef<string | null>(null);
  const skipPortfolioServerSync = useRef(false);

  const subject = session?.subject ?? null;
  const accessToken = session?.accessToken ?? null;

  const flushSave = useCallback(
    (next: UserDataBundle) => {
      if (!subject) return;
      setSyncStatus("saving");
      try {
        const stamped = { ...next, updatedAt: new Date().toISOString() };
        writeUserData(stamped);
        setBundle(stamped);
        setLastSyncedAt(stamped.updatedAt);
        setLastError(null);
        setSyncStatus("saved");
        logger.debug("User data saved", { subject });
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to save user data";
        setLastError(message);
        setSyncStatus("error");
        logger.error(message, { subject });
      }
    },
    [subject],
  );

  const scheduleSave = useCallback(
    (updater: (current: UserDataBundle) => UserDataBundle) => {
      if (!bundle) return;
      const next = updater(bundle);
      setBundle(next);
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => flushSave(next), SAVE_DEBOUNCE_MS);
    },
    [bundle, flushSave],
  );

  useEffect(() => {
    if (status === "loading" || status === "refreshing") return;

    if (!subject || status !== "authenticated") {
      setBundle(null);
      setIsLoaded(true);
      setSyncStatus("idle");
      preferencesApplied.current = false;
      setServerPortfolioId(null);
      setServerBenchmarkSymbol(null);
      setPortfolioSyncStatus("idle");
      setPortfolioSyncError(null);
      knownServerSymbols.current = [];
      return;
    }

    setSyncStatus("loading");
    setIsLoaded(false);
    const stored = readUserData(subject);
    const next = stored ?? createEmptyUserData(subject);
    setBundle(next);
    setIsLoaded(true);
    setLastSyncedAt(next.updatedAt);
    setSyncStatus("saved");
    setLastError(null);
    logger.info("User data loaded", { subject });
  }, [status, subject]);

  // RC1 Milestone 3 — Migration strategy: on first authenticated load, IF a
  // server portfolio already exists, it becomes the source of truth for
  // holdings; ELSE the local snapshot (holdings/watchlist/benchmark —
  // possibly empty) is migrated to the server. The local copy in
  // `localStorage` is never deleted by this effect, win or lose.
  useEffect(() => {
    if (!isLoaded || status !== "authenticated" || !subject || !bundle) return;
    if (migrationAttemptedFor.current === subject) return;
    migrationAttemptedFor.current = subject;

    let cancelled = false;
    setPortfolioSyncStatus("syncing");
    setPortfolioSyncError(null);

    void (async () => {
      try {
        const existing = await fetchDefaultPortfolio(accessToken);
        if (cancelled) return;

        if (existing) {
          const holdings = await fetchHoldings(accessToken, existing.portfolio_id);
          if (cancelled) return;
          knownServerSymbols.current = holdings.map((h) => h.ticker);
          setServerPortfolioId(existing.portfolio_id);
          setServerBenchmarkSymbol(existing.benchmark_symbol);
          skipPortfolioServerSync.current = true;
          setBundle((current) =>
            current
              ? {
                  ...current,
                  portfolio: userPortfolioFromView(
                    buildPortfolioView(holdings, current.portfolio.activities),
                    current.portfolio,
                  ),
                }
              : current,
          );
          window.setTimeout(() => {
            skipPortfolioServerSync.current = false;
          }, 0);
          logger.info("Loaded server portfolio", {
            subject,
            portfolioId: existing.portfolio_id,
          });
        } else {
          const localHoldings = bundle.portfolio.holdings;
          const result = await migrateLocalPortfolio(accessToken, {
            name: bundle.portfolio.name || "My Portfolio",
            holdings: localHoldings,
          });
          if (cancelled) return;
          knownServerSymbols.current = localHoldings.map((h) => h.ticker);
          setServerPortfolioId(result.portfolio.portfolio_id);
          setServerBenchmarkSymbol(result.portfolio.benchmark_symbol);
          logger.info("Portfolio migration to server complete", {
            subject,
            migrated: result.migrated,
            portfolioId: result.portfolio.portfolio_id,
          });
        }
        setPortfolioSyncStatus("synced");
      } catch (error) {
        if (cancelled) return;
        const message =
          error instanceof Error ? error.message : "Portfolio server sync failed";
        setPortfolioSyncError(message);
        setPortfolioSyncStatus("error");
        // Honest degrade: keep serving the local copy — never lose data.
        logger.error(message, { subject });
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, status, subject, accessToken]);

  useEffect(() => {
    if (!bundle || preferencesApplied.current) return;
    if (bundle.preferences.theme) {
      setMode(bundle.preferences.theme);
    }
    preferencesApplied.current = true;
  }, [bundle, setMode]);

  useEffect(
    () => () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    },
    [],
  );

  const persistPortfolio = useCallback(
    (view: PortfolioView) => {
      if (!bundle || status !== "authenticated") return;
      scheduleSave((current) => ({
        ...current,
        portfolio: userPortfolioFromView(view, current.portfolio),
      }));
      // Server sync is best-effort and never blocks the local (always-on)
      // save above — a failed sync keeps the local copy intact and simply
      // retries on the next mutation.
      if (serverPortfolioId && !skipPortfolioServerSync.current) {
        const previousSymbols = knownServerSymbols.current;
        const nextSymbols = view.holdings.map((h) => h.ticker);
        syncHoldings(accessToken, serverPortfolioId, view.holdings, previousSymbols)
          .then(() => {
            knownServerSymbols.current = nextSymbols;
            setPortfolioSyncStatus("synced");
            setPortfolioSyncError(null);
          })
          .catch((error: unknown) => {
            const message =
              error instanceof Error ? error.message : "Portfolio server sync failed";
            setPortfolioSyncStatus("error");
            setPortfolioSyncError(message);
            logger.error(message, { subject });
          });
      }
    },
    [bundle, status, scheduleSave, serverPortfolioId, accessToken, subject],
  );

  const saveAnalysis = useCallback(
    (input: Omit<SavedAnalysis, "id" | "savedAt">): SavedAnalysis | null => {
      if (!bundle || status !== "authenticated") return null;
      const entry: SavedAnalysis = {
        ...input,
        id: createSavedAnalysisId(),
        savedAt: new Date().toISOString(),
      };
      scheduleSave((current) => ({
        ...current,
        savedAnalyses: sortSavedAnalyses([
          entry,
          ...current.savedAnalyses.filter(
            (item) => item.ticker.toUpperCase() !== entry.ticker.toUpperCase(),
          ),
        ]),
      }));
      return entry;
    },
    [bundle, status, scheduleSave],
  );

  const deleteSavedAnalysis = useCallback(
    (id: string) => {
      if (!bundle) return;
      scheduleSave((current) => ({
        ...current,
        savedAnalyses: current.savedAnalyses.filter((item) => item.id !== id),
      }));
    },
    [bundle, scheduleSave],
  );

  const reopenSavedAnalysis = useCallback(
    (id: string): boolean => {
      const saved = bundle?.savedAnalyses.find((item) => item.id === id);
      if (!saved?.request || !saved.response) return false;
      saveResearchSession({
        ticker: saved.ticker,
        exchange: saved.exchange || null,
        company: saved.company || null,
        analysedAt: saved.analysedAt,
        request: saved.request,
        response: saved.response,
      });
      return true;
    },
    [bundle?.savedAnalyses],
  );

  const persistCopilotConversations = useCallback(
    (conversations: CopilotConversation[]) => {
      if (!bundle || status !== "authenticated") return;
      const metadata = conversations.map(toSavedConversation);
      scheduleSave((current) => ({
        ...current,
        copilotConversations: metadata,
      }));
    },
    [bundle, status, scheduleSave],
  );

  const updatePreferences = useCallback(
    (patch: Partial<UserPreference>) => {
      if (!bundle) return;
      scheduleSave((current) => ({
        ...current,
        preferences: { ...current.preferences, ...patch },
      }));
      if (patch.theme) {
        setMode(patch.theme as ThemeMode);
      }
    },
    [bundle, scheduleSave, setMode],
  );

  const syncNow = useCallback(async () => {
    if (!bundle || !subject) return;
    setSyncStatus("saving");
    await new Promise((resolve) => setTimeout(resolve, 100));
    flushSave(bundle);
  }, [bundle, subject, flushSave]);

  const portfolioView = useMemo(
    () => (bundle ? portfolioViewFromUserPortfolio(bundle.portfolio) : null),
    [bundle],
  );

  const value = useMemo<PersistenceContextValue>(
    () => ({
      syncStatus,
      lastSyncedAt,
      lastError,
      isLoaded,
      bundle,
      savedAnalyses: bundle?.savedAnalyses ?? [],
      copilotConversations: bundle?.copilotConversations ?? [],
      preferences: bundle?.preferences ?? DEFAULT_PREFERENCES,
      portfolioView,
      persistPortfolio,
      saveAnalysis,
      deleteSavedAnalysis,
      reopenSavedAnalysis,
      persistCopilotConversations,
      updatePreferences,
      syncNow,
      serverPortfolioId,
      serverBenchmarkSymbol,
      portfolioSyncStatus,
      portfolioSyncError,
    }),
    [
      syncStatus,
      lastSyncedAt,
      lastError,
      isLoaded,
      bundle,
      portfolioView,
      persistPortfolio,
      saveAnalysis,
      deleteSavedAnalysis,
      reopenSavedAnalysis,
      persistCopilotConversations,
      updatePreferences,
      syncNow,
      serverPortfolioId,
      serverBenchmarkSymbol,
      portfolioSyncStatus,
      portfolioSyncError,
    ],
  );

  return (
    <PersistenceContext.Provider value={value}>
      {children}
    </PersistenceContext.Provider>
  );
}

export function usePersistence(): PersistenceContextValue {
  const ctx = useContext(PersistenceContext);
  if (!ctx) {
    throw new Error("usePersistence must be used within PersistenceProvider");
  }
  return ctx;
}
