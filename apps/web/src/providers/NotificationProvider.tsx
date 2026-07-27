"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ToastViewport } from "@/components/notifications/ToastViewport";

export type NotificationTone = "success" | "warning" | "error" | "info";

export type Notification = {
  id: string;
  message: string;
  title?: string;
  tone: NotificationTone;
  createdAt: string;
  durationMs: number;
};

type NotifyInput = {
  message: string;
  title?: string;
  tone?: NotificationTone;
  durationMs?: number;
};

type NotificationContextValue = {
  notifications: Notification[];
  notify: (input: NotifyInput) => string;
  dismiss: (id: string) => void;
  success: (message: string, title?: string) => string;
  warning: (message: string, title?: string) => string;
  error: (message: string, title?: string) => string;
  info: (message: string, title?: string) => string;
};

const NotificationContext = createContext<NotificationContextValue | null>(null);

const DEFAULT_DURATION_MS = 5000;

function createId(): string {
  return `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const dismiss = useCallback((id: string) => {
    setNotifications((current) => current.filter((item) => item.id !== id));
  }, []);

  const notify = useCallback(
    ({
      message,
      title,
      tone = "info",
      durationMs = DEFAULT_DURATION_MS,
    }: NotifyInput) => {
      const id = createId();
      const notification: Notification = {
        id,
        message,
        title,
        tone,
        durationMs,
        createdAt: new Date().toISOString(),
      };
      setNotifications((current) => [...current, notification]);

      if (durationMs > 0 && typeof window !== "undefined") {
        window.setTimeout(() => dismiss(id), durationMs);
      }

      return id;
    },
    [dismiss],
  );

  const value = useMemo<NotificationContextValue>(
    () => ({
      notifications,
      notify,
      dismiss,
      success: (message, title) => notify({ message, title, tone: "success" }),
      warning: (message, title) => notify({ message, title, tone: "warning" }),
      error: (message, title) => notify({ message, title, tone: "error" }),
      info: (message, title) => notify({ message, title, tone: "info" }),
    }),
    [notifications, notify, dismiss],
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <ToastViewport
        notifications={notifications}
        onDismiss={dismiss}
      />
    </NotificationContext.Provider>
  );
}

export function useNotifications(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error("useNotifications must be used within NotificationProvider");
  }
  return ctx;
}
