"use client";

import type { Notification } from "@/providers/NotificationProvider";

const TONE_STYLES: Record<Notification["tone"], string> = {
  success:
    "border-[var(--accent)]/40 bg-[var(--accent-soft)]/60 text-[var(--fg)]",
  warning:
    "border-amber-500/40 bg-amber-500/10 text-[var(--fg)]",
  error:
    "border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger-fg)]",
  info: "border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg)]",
};

export function ToastViewport({
  notifications,
  onDismiss,
}: {
  notifications: Notification[];
  onDismiss: (id: string) => void;
}) {
  if (!notifications.length) return null;

  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[90] flex w-full max-w-sm flex-col gap-2"
      aria-live="polite"
      aria-label="Notifications"
    >
      {notifications.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`pointer-events-auto rounded-lg border px-4 py-3 shadow-lg ${TONE_STYLES[toast.tone]}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              {toast.title ? (
                <p className="text-sm font-medium">{toast.title}</p>
              ) : null}
              <p className={`text-sm ${toast.title ? "mt-0.5 opacity-90" : ""}`}>
                {toast.message}
              </p>
            </div>
            <button
              type="button"
              className="shrink-0 rounded px-1 text-xs opacity-70 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label="Dismiss notification"
              onClick={() => onDismiss(toast.id)}
            >
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
