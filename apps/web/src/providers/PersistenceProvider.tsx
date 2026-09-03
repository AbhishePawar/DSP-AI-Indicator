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
import type { PortfolioView } from "@/lib/portfolio/model";
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
import { isSupabaseBrowserConfigured } from "@/lib/supabase/publicConfig";
import {
  fetchCloudPersistence,
  saveCloudPersistence,
} from "@/lib/supabase/cloudSync";
import { usePortfolioIntelPrefsStore } from "@/lib/portfolio-intelligence/prefsStore";
import type {
  SavedAnalysis,
  SavedConversation,
  SyncStatus,
  UserDataBundle,
  UserPreference,
} from "@/lib/persistence/types";
import { DEFAULT_PREFERENCES } from "@/lib/persistence/types";

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

  const subject = session?.subject ?? null;

  const flushSave = useCallback(
    (next: UserDataBundle) => {
      if (!subject || !session) return;
      setSyncStatus("saving");
      try {
        const stamped = { ...next, updatedAt: new Date().toISOString() };
        writeUserData(stamped);
        setBundle(stamped);
        setLastSyncedAt(stamped.updatedAt);
        setLastError(null);
        setSyncStatus("saved");
        logger.debug("User data saved", { subject });
        if (isSupabaseBrowserConfigured()) {
          const watchlist = usePortfolioIntelPrefsStore.getState().watchlist;
          void saveCloudPersistence(session, stamped, watchlist).then(
            (result) => {
              if (!result.ok && result.error) {
                logger.warn("Cloud persistence unavailable", {
                  subject,
                  error: result.error,
                });
              }
            },
          );
        }
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to save user data";
        setLastError(message);
        setSyncStatus("error");
        logger.error(message, { subject });
      }
    },
    [subject, session],
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
    if (status === "restoring" || status === "loading" || status === "refreshing") return;

    if (!subject || status !== "authenticated") {
      setBundle(null);
      setIsLoaded(true);
      setSyncStatus("idle");
      preferencesApplied.current = false;
      return;
    }

    setSyncStatus("loading");
    setIsLoaded(false);
    const stored = readUserData(subject);
    const local = stored ?? createEmptyUserData(subject);
    setBundle(local);
    setIsLoaded(true);
    setLastSyncedAt(local.updatedAt);
    setSyncStatus("saved");
    setLastError(null);
    logger.info("User data loaded", { subject });

    if (!session || !isSupabaseBrowserConfigured()) return;
    void fetchCloudPersistence(session)
      .then((result) => {
        if (!result.ok || !result.configured || !result.snapshot) return;
        const cloud = result.snapshot;
        const cloudNewer =
          !stored ||
          new Date(cloud.updatedAt).getTime() >
            new Date(local.updatedAt).getTime();
        if (cloudNewer) {
          const merged: UserDataBundle = {
            ...local,
            updatedAt: cloud.updatedAt,
            preferences: cloud.preferences,
            savedAnalyses:
              cloud.savedResearch.length > 0
                ? sortSavedAnalyses(cloud.savedResearch)
                : local.savedAnalyses,
          };
          writeUserData(merged);
          setBundle(merged);
          setLastSyncedAt(merged.updatedAt);
        }
        const localWatch = usePortfolioIntelPrefsStore.getState().watchlist;
        if (localWatch.length === 0 && cloud.watchlist.length > 0) {
          for (const item of cloud.watchlist) {
            usePortfolioIntelPrefsStore
              .getState()
              .addWatchlistSymbol(item.symbol, item.companyName ?? undefined);
          }
        }
      })
      .catch(() => {
        logger.warn("Cloud persistence load skipped", { subject });
      });
  }, [status, subject, session]);

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
    },
    [bundle, status, scheduleSave],
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
