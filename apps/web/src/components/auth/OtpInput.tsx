"use client";

import {
  ClipboardEvent,
  KeyboardEvent,
  useEffect,
  useMemo,
  useRef,
} from "react";
import { cn } from "@/lib/utils";

export type OtpInputProps = {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  onComplete?: (value: string) => void;
  disabled?: boolean;
  autoFocus?: boolean;
  id?: string;
  label: string;
  error?: string;
};

/**
 * Accessible, keyboard-navigable N-digit OTP input rendered as a labelled
 * group of single-character boxes. Supports paste of the full code, arrow /
 * backspace navigation, and calls `onComplete` once all digits are filled.
 */
export function OtpInput({
  length = 6,
  value,
  onChange,
  onComplete,
  disabled,
  autoFocus,
  id,
  label,
  error,
}: OtpInputProps) {
  const groupId = id ?? "otp-input";
  const refs = useRef<Array<HTMLInputElement | null>>([]);
  const digits = useMemo(() => {
    const chars = value.replace(/\D/g, "").slice(0, length).split("");
    return Array.from({ length }, (_, i) => chars[i] ?? "");
  }, [value, length]);

  useEffect(() => {
    if (autoFocus) refs.current[0]?.focus();
  }, [autoFocus]);

  function setDigit(index: number, digit: string) {
    const next = [...digits];
    next[index] = digit;
    const joined = next.join("");
    onChange(joined);
    if (joined.length === length && !joined.includes("")) {
      onComplete?.(joined);
    }
  }

  function handleChange(index: number, raw: string) {
    const clean = raw.replace(/\D/g, "");
    if (!clean) {
      setDigit(index, "");
      return;
    }
    if (clean.length > 1) {
      // Fast-typed or autofilled multi-char input.
      const next = digits.slice();
      for (let i = 0; i < clean.length && index + i < length; i++) {
        next[index + i] = clean[i]!;
      }
      const joined = next.join("");
      onChange(joined);
      const lastFilled = Math.min(index + clean.length, length) - 1;
      refs.current[Math.min(lastFilled + 1, length - 1)]?.focus();
      if (joined.length === length && !joined.includes("")) onComplete?.(joined);
      return;
    }
    setDigit(index, clean);
    if (index < length - 1) refs.current[index + 1]?.focus();
  }

  function handleKeyDown(index: number, event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Backspace") {
      if (digits[index]) {
        setDigit(index, "");
      } else if (index > 0) {
        refs.current[index - 1]?.focus();
        setDigit(index - 1, "");
      }
      event.preventDefault();
    } else if (event.key === "ArrowLeft" && index > 0) {
      refs.current[index - 1]?.focus();
    } else if (event.key === "ArrowRight" && index < length - 1) {
      refs.current[index + 1]?.focus();
    }
  }

  function handlePaste(event: ClipboardEvent<HTMLInputElement>) {
    const text = event.clipboardData.getData("text").replace(/\D/g, "");
    if (!text) return;
    event.preventDefault();
    const joined = text.slice(0, length).padEnd(length, "").split("");
    const merged = Array.from({ length }, (_, i) => joined[i] || digits[i] || "");
    const value = merged.join("");
    onChange(value);
    const nextFocus = Math.min(text.length, length - 1);
    refs.current[nextFocus]?.focus();
    if (value.length === length && !value.includes("")) onComplete?.(value);
  }

  return (
    <div role="group" aria-labelledby={`${groupId}-label`}>
      <span id={`${groupId}-label`} className="mb-1.5 block text-sm font-medium text-[var(--fg)]">
        {label}
      </span>
      <div className="flex gap-2">
        {digits.map((digit, index) => (
          <input
            key={index}
            ref={(el) => {
              refs.current[index] = el;
            }}
            id={index === 0 ? groupId : undefined}
            type="text"
            inputMode="numeric"
            autoComplete={index === 0 ? "one-time-code" : "off"}
            pattern="[0-9]*"
            maxLength={length}
            value={digit}
            disabled={disabled}
            aria-label={`Digit ${index + 1} of ${length}`}
            aria-invalid={error ? true : undefined}
            className={cn(
              "h-12 w-10 rounded-[var(--radius-md,0.5rem)] border border-[var(--border)]",
              "bg-[var(--surface)] text-center text-lg font-medium text-[var(--fg)]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
              "focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]",
              "disabled:cursor-not-allowed disabled:opacity-50",
              error ? "border-[var(--danger-border)]" : null,
            )}
            onChange={(e) => handleChange(index, e.target.value)}
            onKeyDown={(e) => handleKeyDown(index, e)}
            onPaste={handlePaste}
          />
        ))}
      </div>
    </div>
  );
}
