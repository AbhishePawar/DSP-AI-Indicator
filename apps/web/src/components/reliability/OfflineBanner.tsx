"use client";

import { useEffect, useState, type ReactNode } from "react";

export function OfflineBanner() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const sync = () => setOffline(!navigator.onLine);
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="border-b border-[var(--danger-border)] bg-[var(--danger-bg)] px-4 py-2 text-center text-sm text-[var(--danger-fg)]"
    >
      You are offline. Cached UI may still render; API analyze/health calls will fail until
      connectivity returns.
    </div>
  );
}

const SESSION_KEY = "dsp.session.recovery.v1";

export function SessionRecoveryProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(SESSION_KEY);
      if (!raw) {
        window.sessionStorage.setItem(
          SESSION_KEY,
          JSON.stringify({ restoredAt: null, boot: Date.now() }),
        );
      } else {
        const parsed = JSON.parse(raw) as { boot?: number };
        window.sessionStorage.setItem(
          SESSION_KEY,
          JSON.stringify({
            restoredAt: Date.now(),
            boot: parsed.boot ?? Date.now(),
          }),
        );
      }
    } catch {
      // ignore quota / private mode
    }
  }, []);

  return <>{children}</>;
}

export function useSessionRecoveryMeta(): { restoredAt: number | null; boot: number | null } {
  const [meta, setMeta] = useState<{ restoredAt: number | null; boot: number | null }>({
    restoredAt: null,
    boot: null,
  });
  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(SESSION_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as { restoredAt?: number; boot?: number };
        setMeta({
          restoredAt: parsed.restoredAt ?? null,
          boot: parsed.boot ?? null,
        });
      }
    } catch {
      /* ignore */
    }
  }, []);
  return meta;
}
