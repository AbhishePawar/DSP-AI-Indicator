"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastTone = "info" | "success" | "warning" | "error";

export type ToastInput = {
  title?: string;
  description?: string;
  tone?: ToastTone;
  durationMs?: number;
};

export type ToastRecord = ToastInput & {
  id: string;
};

type ToastContextValue = {
  toasts: ToastRecord[];
  toast: (input: ToastInput) => string;
  dismiss: (id: string) => void;
  clear: () => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const toneClass: Record<ToastTone, string> = {
  info: "border-[var(--border)] bg-[var(--surface)] text-[var(--fg)]",
  success:
    "border-[color-mix(in_srgb,var(--accent)_35%,var(--border))] bg-[var(--accent-soft)] text-[var(--fg)]",
  warning:
    "border-[var(--warning-border)] bg-[var(--warning-bg)] text-[var(--warning-fg)]",
  error:
    "border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger-fg)]",
};

let toastSeq = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (input: ToastInput) => {
      const id = `toast-${++toastSeq}`;
      const durationMs = input.durationMs ?? 4000;
      setToasts((prev) => [...prev, { ...input, id }]);
      if (durationMs > 0) {
        window.setTimeout(() => dismiss(id), durationMs);
      }
      return id;
    },
    [dismiss],
  );

  const clear = useCallback(() => setToasts([]), []);

  const value = useMemo(
    () => ({ toasts, toast, dismiss, clear }),
    [toasts, toast, dismiss, clear],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastViewport />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}

export function ToastViewport({ className }: { className?: string }) {
  const ctx = useContext(ToastContext);
  if (!ctx) return null;

  return (
    <div
      aria-live="polite"
      aria-relevant="additions"
      className={cn(
        "pointer-events-none fixed bottom-4 right-4 z-[70] flex w-[min(100vw-2rem,22rem)] flex-col gap-2",
        className,
      )}
    >
      {ctx.toasts.map((item) => (
        <div
          key={item.id}
          role="status"
          className={cn(
            "pointer-events-auto rounded-[var(--radius-md)] border px-3 py-2.5 shadow-[var(--shadow-md)]",
            toneClass[item.tone ?? "info"],
          )}
        >
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              {item.title ? (
                <p className="text-sm font-medium leading-tight">{item.title}</p>
              ) : null}
              {item.description ? (
                <p
                  className={cn(
                    "text-sm opacity-90",
                    item.title ? "mt-1" : null,
                  )}
                >
                  {item.description}
                </p>
              ) : null}
            </div>
            <button
              type="button"
              aria-label="Dismiss notification"
              onClick={() => ctx.dismiss(item.id)}
              className="inline-flex size-7 shrink-0 items-center justify-center rounded-[var(--radius-md)] opacity-70 transition hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <X className="size-3.5" aria-hidden />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
