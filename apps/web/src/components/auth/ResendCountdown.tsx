"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ds";

export type ResendCountdownProps = {
  seconds?: number;
  onResend: () => void | Promise<void>;
  disabled?: boolean;
  label?: string;
};

/** "Resend code" button that shows a live countdown before re-enabling. */
export function ResendCountdown({
  seconds = 30,
  onResend,
  disabled,
  label = "Resend OTP",
}: ResendCountdownProps) {
  const [remaining, setRemaining] = useState(seconds);
  // Counts up on every (re)start of the countdown so the effect below sets
  // up exactly one interval per cycle instead of recreating it every tick.
  const [cycle, setCycle] = useState(0);

  useEffect(() => {
    if (remaining <= 0) return;
    const id = window.setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          window.clearInterval(id);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => window.clearInterval(id);
    // Intentionally excludes `remaining`: it's only read once, at mount /
    // resend, to decide whether to start the interval at all.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cycle]);

  async function handleResend() {
    await onResend();
    setRemaining(seconds);
    setCycle((c) => c + 1);
  }

  return (
    <div className="flex items-center justify-between text-sm">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        disabled={disabled || remaining > 0}
        onClick={handleResend}
      >
        {label}
      </Button>
      {remaining > 0 ? (
        <span aria-live="polite" className="text-[var(--muted)]">
          Resend available in {remaining}s
        </span>
      ) : null}
    </div>
  );
}
